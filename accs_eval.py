"""
accs_eval.py

This script calculates several metrics from the output JSON files, including ACCS, IACCS, EM, QM, and ERROR.

Usage:
    python accs_eval.py --input outputs/llm_responses.json --output outputs/metrics.json

Arguments:
    --input: Path to the input JSON file containing the LLM responses.
    --output: Path to the output JSON file where the metrics will be saved.
"""


import json
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import os, sys
import signal
import re
import json
import sqlite3
import traceback
import argparse

from process_sql import tokenize, get_schema, get_tables_with_alias, Schema, get_sql


# Flag to disable value evaluation
DISABLE_VALUE = True
# Flag to disable distinct in select evaluation
DISABLE_DISTINCT = True


CLAUSE_KEYWORDS = ('select', 'from', 'where', 'group', 'order', 'limit', 'intersect', 'union', 'except')
JOIN_KEYWORDS = ('join', 'on', 'as')

WHERE_OPS = ('not', 'between', '=', '>', '<', '>=', '<=', '!=', 'in', 'like', 'is', 'exists')
UNIT_OPS = ('none', '-', '+', "*", '/')
AGG_OPS = ('none', 'max', 'min', 'count', 'sum', 'avg')
TABLE_TYPE = {
    'sql': "sql",
    'table_unit': "table_unit",
}

COND_OPS = ('and', 'or')
SQL_OPS = ('intersect', 'union', 'except')
ORDER_OPS = ('desc', 'asc')


HARDNESS = {
    "component1": ('where', 'group', 'order', 'limit', 'join', 'or', 'like'),
    "component2": ('except', 'union', 'intersect')
}


def condition_has_or(conds):
    return 'or' in conds[1::2]


def condition_has_like(conds):
    return WHERE_OPS.index('like') in [cond_unit[1] for cond_unit in conds[::2]]


def condition_has_sql(conds):
    for cond_unit in conds[::2]:
        val1, val2 = cond_unit[3], cond_unit[4]
        if val1 is not None and type(val1) is dict:
            return True
        if val2 is not None and type(val2) is dict:
            return True
    return False


def val_has_op(val_unit):
    return val_unit[0] != UNIT_OPS.index('none')


def has_agg(unit):
    return unit[0] != AGG_OPS.index('none')


def accuracy(count, total):
    if count == total:
        return 1
    return 0


def recall(count, total):
    if count == total:
        return 1
    return 0


def F1(acc, rec):
    if (acc + rec) == 0:
        return 0
    return (2. * acc * rec) / (acc + rec)


def get_scores(count, pred_total, label_total):
    if pred_total != label_total:
        return 0,0,0
    elif count == pred_total:
        return 1,1,1
    return 0,0,0


def eval_sel(pred, label):
    pred_sel = pred['select'][1]
    label_sel = label['select'][1]
    label_wo_agg = [unit[1] for unit in label_sel]
    pred_total = len(pred_sel)
    label_total = len(label_sel)
    cnt = 0
    cnt_wo_agg = 0

    for unit in pred_sel:
        if unit in label_sel:
            cnt += 1
            label_sel.remove(unit)
        if unit[1] in label_wo_agg:
            cnt_wo_agg += 1
            label_wo_agg.remove(unit[1])

    return label_total, pred_total, cnt, cnt_wo_agg


def eval_where(pred, label):
    pred_conds = [unit for unit in pred['where'][::2]]
    label_conds = [unit for unit in label['where'][::2]]
    label_wo_agg = [unit[2] for unit in label_conds]
    pred_total = len(pred_conds)
    label_total = len(label_conds)
    cnt = 0
    cnt_wo_agg = 0

    for unit in pred_conds:
        if unit in label_conds:
            cnt += 1
            label_conds.remove(unit)
        if unit[2] in label_wo_agg:
            cnt_wo_agg += 1
            label_wo_agg.remove(unit[2])

    return label_total, pred_total, cnt, cnt_wo_agg


def eval_group(pred, label):
    pred_cols = [unit[1] for unit in pred['groupBy']]
    label_cols = [unit[1] for unit in label['groupBy']]
    pred_total = len(pred_cols)
    label_total = len(label_cols)
    cnt = 0
    pred_cols = [pred.split(".")[1] if "." in pred else pred for pred in pred_cols]
    label_cols = [label.split(".")[1] if "." in label else label for label in label_cols]
    for col in pred_cols:
        if col in label_cols:
            cnt += 1
            label_cols.remove(col)
    return label_total, pred_total, cnt


def eval_having(pred, label):
    pred_total = label_total = cnt = 0
    if len(pred['groupBy']) > 0:
        pred_total = 1
    if len(label['groupBy']) > 0:
        label_total = 1

    pred_cols = [unit[1] for unit in pred['groupBy']]
    label_cols = [unit[1] for unit in label['groupBy']]
    if pred_total == label_total == 1 \
            and pred_cols == label_cols \
            and pred['having'] == label['having']:
        cnt = 1

    return label_total, pred_total, cnt


def eval_order(pred, label):
    pred_total = label_total = cnt = 0
    if len(pred['orderBy']) > 0:
        pred_total = 1
    if len(label['orderBy']) > 0:
        label_total = 1
    if len(label['orderBy']) > 0 and pred['orderBy'] == label['orderBy'] and \
            ((pred['limit'] is None and label['limit'] is None) or (pred['limit'] is not None and label['limit'] is not None)):
        cnt = 1
    return label_total, pred_total, cnt


def eval_and_or(pred, label):
    pred_ao = pred['where'][1::2]
    label_ao = label['where'][1::2]
    pred_ao = set(pred_ao)
    label_ao = set(label_ao)

    if pred_ao == label_ao:
        return 1,1,1
    return len(pred_ao),len(label_ao),0


def get_nestedSQL(sql):
    nested = []
    for cond_unit in sql['from']['conds'][::2] + sql['where'][::2] + sql['having'][::2]:
        if type(cond_unit[3]) is dict:
            nested.append(cond_unit[3])
        if type(cond_unit[4]) is dict:
            nested.append(cond_unit[4])
    if sql['intersect'] is not None:
        nested.append(sql['intersect'])
    if sql['except'] is not None:
        nested.append(sql['except'])
    if sql['union'] is not None:
        nested.append(sql['union'])
    return nested


def eval_nested(pred, label):
    label_total = 0
    pred_total = 0
    cnt = 0
    if pred is not None:
        pred_total += 1
    if label is not None:
        label_total += 1
    if pred is not None and label is not None:
        cnt += Evaluator().eval_exact_match(pred, label)
    return label_total, pred_total, cnt


def eval_IUEN(pred, label):
    lt1, pt1, cnt1 = eval_nested(pred['intersect'], label['intersect'])
    lt2, pt2, cnt2 = eval_nested(pred['except'], label['except'])
    lt3, pt3, cnt3 = eval_nested(pred['union'], label['union'])
    label_total = lt1 + lt2 + lt3
    pred_total = pt1 + pt2 + pt3
    cnt = cnt1 + cnt2 + cnt3
    return label_total, pred_total, cnt


def get_keywords(sql):
    res = set()
    if len(sql['where']) > 0:
        res.add('where')
    if len(sql['groupBy']) > 0:
        res.add('group')
    if len(sql['having']) > 0:
        res.add('having')
    if len(sql['orderBy']) > 0:
        res.add(sql['orderBy'][0])
        res.add('order')
    if sql['limit'] is not None:
        res.add('limit')
    if sql['except'] is not None:
        res.add('except')
    if sql['union'] is not None:
        res.add('union')
    if sql['intersect'] is not None:
        res.add('intersect')

    # or keyword
    ao = sql['from']['conds'][1::2] + sql['where'][1::2] + sql['having'][1::2]
    if len([token for token in ao if token == 'or']) > 0:
        res.add('or')

    cond_units = sql['from']['conds'][::2] + sql['where'][::2] + sql['having'][::2]
    # not keyword
    if len([cond_unit for cond_unit in cond_units if cond_unit[0]]) > 0:
        res.add('not')

    # in keyword
    if len([cond_unit for cond_unit in cond_units if cond_unit[1] == WHERE_OPS.index('in')]) > 0:
        res.add('in')

    # like keyword
    if len([cond_unit for cond_unit in cond_units if cond_unit[1] == WHERE_OPS.index('like')]) > 0:
        res.add('like')

    return res


def eval_keywords(pred, label):
    pred_keywords = get_keywords(pred)
    label_keywords = get_keywords(label)
    pred_total = len(pred_keywords)
    label_total = len(label_keywords)
    cnt = 0

    for k in pred_keywords:
        if k in label_keywords:
            cnt += 1
    return label_total, pred_total, cnt


def count_agg(units):
    return len([unit for unit in units if has_agg(unit)])


def count_component1(sql):
    count = 0
    if len(sql['where']) > 0:
        count += 1
    if len(sql['groupBy']) > 0:
        count += 1
    if len(sql['orderBy']) > 0:
        count += 1
    if sql['limit'] is not None:
        count += 1
    if len(sql['from']['table_units']) > 0:  # JOIN
        count += len(sql['from']['table_units']) - 1

    ao = sql['from']['conds'][1::2] + sql['where'][1::2] + sql['having'][1::2]
    count += len([token for token in ao if token == 'or'])
    cond_units = sql['from']['conds'][::2] + sql['where'][::2] + sql['having'][::2]
    count += len([cond_unit for cond_unit in cond_units if cond_unit[1] == WHERE_OPS.index('like')])

    return count


def count_component2(sql):
    nested = get_nestedSQL(sql)
    return len(nested)


def count_others(sql):
    count = 0
    # number of aggregation
    agg_count = count_agg(sql['select'][1])
    agg_count += count_agg(sql['where'][::2])
    agg_count += count_agg(sql['groupBy'])
    if len(sql['orderBy']) > 0:
        agg_count += count_agg([unit[1] for unit in sql['orderBy'][1] if unit[1]] +
                            [unit[2] for unit in sql['orderBy'][1] if unit[2]])
    agg_count += count_agg(sql['having'])
    if agg_count > 1:
        count += 1

    # number of select columns
    if len(sql['select'][1]) > 1:
        count += 1

    # number of where conditions
    if len(sql['where']) > 1:
        count += 1

    # number of group by clauses
    if len(sql['groupBy']) > 1:
        count += 1

    return count
# Define the exception you want to raise when the timeout occurs
class TimeoutException(Exception):
    pass

# Define the signal handler function
def signal_handler(signum, frame):
    raise TimeoutException

error_count = 0
def execute_query(db, query):
    """
    在独立的线程内执行数据库查询。
    创建自己的数据库连接和游标来执行查询。
    """
    global error_count
    conn = None
    cursor = None
    try:
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        cursor.execute(query)
        result = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"SQLite serror: {e}")
        error_count += 1
        result = None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return result



def eval_exec_match(db_path,db, p_str, g_str):
    p_str = p_str.lower()
    g_str = g_str.lower()
    p_str = p_str.replace("`","'")
    p_str = p_str.replace("▁"," ")
    g_str = g_str.replace(">="," >= ")
    p_str = p_str.replace(">="," >= ")
    split_index = p_str.find('=')
    if split_index != -1:
        p_str = p_str[:split_index] + ' = ' + p_str[split_index + 1:]
    split_index = g_str.find('=')
    if split_index != -1:
        g_str = g_str[:split_index] + ' = ' + g_str[split_index + 1:]
    p_str = ' '.join(p_str.split())
    g_str = ' '.join(g_str.split())
    p_str = p_str.replace("\"","'")
    g_str = g_str.replace("\"","'")
    db = os.path.join(db_path, db, db + ".sqlite")
    schema = Schema(get_schema(db))
    # print("Gold:"+g_str)
    # print("Pred:"+p_str)
    gold = get_sql(schema, g_str)
    pred = get_sql(schema, p_str)


    with ThreadPoolExecutor(max_workers=1) as executor:
        # 执行第一个查询
        future = executor.submit(execute_query, db, p_str)
        try:
            p_res = future.result(timeout=10)  # 设置超时时间为10秒
        except TimeoutError:
            print("操作超时")
            return False
        except Exception as e:
            print(f"执行出错: {e}")
            return False
            
        # 执行第二个查询
        future = executor.submit(execute_query, db, g_str)
        try:
            q_res = future.result(timeout=10)  # 设置超时时间为10秒
        except TimeoutError:
            print("操作超时")
            return False
        except Exception as e:
            print(f"执行出错: {e}")
            return False

    def res_map(res, val_units):
        rmap = {}
        for idx, val_unit in enumerate(val_units):
            key = tuple(val_unit[1]) if not val_unit[2] else (val_unit[0], tuple(val_unit[1]), tuple(val_unit[2]))
            rmap[key] = [r[idx] for r in res]
        return rmap

    p_val_units = [unit[1] for unit in pred['select'][1]]
    q_val_units = [unit[1] for unit in gold['select'][1]]

    return res_map(p_res, p_val_units) == res_map(q_res, q_val_units)

class Evaluator:
    """A simple evaluator"""
    def __init__(self):
        self.partial_scores = None

    def eval_hardness(self, sql):
        count_comp1_ = count_component1(sql)
        count_comp2_ = count_component2(sql)
        count_others_ = count_others(sql)

        if count_comp1_ <= 1 and count_others_ == 0 and count_comp2_ == 0:
            return "easy"
        elif (count_others_ <= 2 and count_comp1_ <= 1 and count_comp2_ == 0) or \
                (count_comp1_ <= 2 and count_others_ < 2 and count_comp2_ == 0):
            return "medium"
        elif (count_others_ > 2 and count_comp1_ <= 2 and count_comp2_ == 0) or \
                (2 < count_comp1_ <= 3 and count_others_ <= 2 and count_comp2_ == 0) or \
                (count_comp1_ <= 1 and count_others_ == 0 and count_comp2_ <= 1):
            return "hard"
        else:
            return "extra"

    def eval_exact_match(self, pred, label):
        partial_scores = self.eval_partial_match(pred, label)
        self.partial_scores = partial_scores

        for key, score in partial_scores.items():
            if score['f1'] != 1:
                return 0

        if len(label['from']['table_units']) > 0:
            label_tables = sorted(label['from']['table_units'])
            pred_tables = sorted(pred['from']['table_units'])
            return label_tables == pred_tables
        return 1

    def eval_partial_match(self, pred, label):
        res = {}

        label_total, pred_total, cnt, cnt_wo_agg = eval_sel(pred, label)
        acc, rec, f1 = get_scores(cnt, pred_total, label_total)
        res['select'] = {'acc': acc, 'rec': rec, 'f1': f1,'label_total':label_total,'pred_total':pred_total}
        acc, rec, f1 = get_scores(cnt_wo_agg, pred_total, label_total)
        res['select(no AGG)'] = {'acc': acc, 'rec': rec, 'f1': f1,'label_total':label_total,'pred_total':pred_total}

        label_total, pred_total, cnt, cnt_wo_agg = eval_where(pred, label)
        acc, rec, f1 = get_scores(cnt, pred_total, label_total)
        res['where'] = {'acc': acc, 'rec': rec, 'f1': f1,'label_total':label_total,'pred_total':pred_total}
        acc, rec, f1 = get_scores(cnt_wo_agg, pred_total, label_total)
        res['where(no OP)'] = {'acc': acc, 'rec': rec, 'f1': f1,'label_total':label_total,'pred_total':pred_total}

        label_total, pred_total, cnt = eval_group(pred, label)
        acc, rec, f1 = get_scores(cnt, pred_total, label_total)
        res['group(no Having)'] = {'acc': acc, 'rec': rec, 'f1': f1,'label_total':label_total,'pred_total':pred_total}

        label_total, pred_total, cnt = eval_having(pred, label)
        acc, rec, f1 = get_scores(cnt, pred_total, label_total)
        res['group'] = {'acc': acc, 'rec': rec, 'f1': f1,'label_total':label_total,'pred_total':pred_total}

        label_total, pred_total, cnt = eval_order(pred, label)
        acc, rec, f1 = get_scores(cnt, pred_total, label_total)
        res['order'] = {'acc': acc, 'rec': rec, 'f1': f1,'label_total':label_total,'pred_total':pred_total}

        label_total, pred_total, cnt = eval_and_or(pred, label)
        acc, rec, f1 = get_scores(cnt, pred_total, label_total)
        res['and/or'] = {'acc': acc, 'rec': rec, 'f1': f1,'label_total':label_total,'pred_total':pred_total}

        label_total, pred_total, cnt = eval_IUEN(pred, label)
        acc, rec, f1 = get_scores(cnt, pred_total, label_total)
        res['IUEN'] = {'acc': acc, 'rec': rec, 'f1': f1,'label_total':label_total,'pred_total':pred_total}

        label_total, pred_total, cnt = eval_keywords(pred, label)
        acc, rec, f1 = get_scores(cnt, pred_total, label_total)
        res['keywords'] = {'acc': acc, 'rec': rec, 'f1': f1,'label_total':label_total,'pred_total':pred_total}

        return res
    
evaluator = Evaluator()



def map_labels_to_new_categories(label):
    mapping = {
        'INFER_SQL': 'Answerable',
        'INFORM_SQL': 'Answerable',
        'CANNOT_ANSWER': 'Unanswerable',
        'CANNOT_UNDERSTAND': 'Ambiguous',
        'NOT_RELATED': 'Unanswerable',
        'AMBIGUOUS': 'Ambiguous'
    }
    return mapping.get(label, 'Improper')

def process_labels(turn_type):
    for label in turn_type:
        new_label = map_labels_to_new_categories(label)
        if "Answeable" in new_label:
            return "Answeable"
    return map_labels_to_new_categories(turn_type[0])


def qm(db_path,p_str,g_str,db):
    p_str = p_str.lower()
    g_str = g_str.lower()
    p_str = p_str.replace("`","'")
    p_str = p_str.replace("▁"," ")
    split_index = p_str.find('=')
    if split_index != -1:
        p_str = p_str[:split_index] + ' = ' + p_str[split_index + 1:]
    split_index = g_str.find('=')
    if split_index != -1:
        g_str = g_str[:split_index] + ' = ' + g_str[split_index + 1:]
    c = ' '.join(p_str.split())
    g_str = ' '.join(g_str.split())
    p_str = p_str.replace("\"","'")
    print("Gold SQL:"+g_str)
    print("Predict SQL:"+p_str)
    g_str = g_str.replace("\"","'")
    db_name = db
    db = os.path.join(db_path, db, db + ".sqlite")
    schema = Schema(get_schema(db))
    g_sql = get_sql(schema, g_str)
    p_sql = get_sql(schema, p_str)
    exact_score = evaluator.eval_exact_match(p_sql, g_sql)
    return exact_score

parser = argparse.ArgumentParser(description='evaluation of AccS. Input JSON file and database path.')
parser.add_argument('json_file_path', type=str, help='Path to the JSON file')
parser.add_argument('database_path', type=str, help='Path to the database')

# 解析命令行参数
args = parser.parse_args()


with open(args.json_file_path, 'r', encoding='utf-8') as file:
    data = json.load(file)

qm_count = 0
allsqlqa = 0
allsqla = 0
em_count = 0
accs = 0
allqa = 0
iaccs_count = 0 
allturn = 0
# 遍历每个元素
for element in tqdm(data):
    print("_________________________")
    db_name = element.get('db_name')
    turns = element.get('turns', [])
    # 遍历每个元素的turns数组
    allturn += 1
    iaccs = True
    for i in range(len(turns) - 1):
        if i%2 == 0:
            print("\n turn:"+str((i+1)//2))
        if turns[i].get('isUser'):
            allqa+=1
            # print(turns[i]['text'])
            gold_type = turns[i].get('type',[])
            predict_type = turns[i].get('predict_type',['INFORM_SQL'])
            if len(gold_type) == 0:
                gold_type = ['INFORM_SQL']
            if len(predict_type) == 0:
                predict_type = ['INFORM_SQL']
            print("Gold Type:"+str(gold_type))
            print("Predict Type:"+str(predict_type))
            gold_type = process_labels (gold_type)
            predict_type = process_labels (predict_type)
            # print("gold   :"+gold_type)
            # print("predict:"+predict_type)
            
            if gold_type == 'Answerable':
                allsqlqa += 1
            if predict_type == 'Answerable':
                allsqla += 1
            if gold_type == predict_type and predict_type == 'Answerable':
                try:
                    print("Question:"+turns[i].get('text',''))
                    if qm(args.database_path,turns[i+1].get('query',''), turns[i+1].get('predict',''), db_name):
                        # print("QM\n")
                        qm_count += 1
                        accs += 1
                        print("\033[92mACCS+1\033[0m")
                    else:
                        iaccs = False
                        print("\033[91mIACCS failed\033[0m")
                except:
                    accs += 0
                    iaccs = False
                    print("\033[91mIACCS failed\033[0m")
                try:
                    
                    if eval_exec_match(args.database_path,db_name, turns[i+1].get('predict',''), turns[i+1].get('query','')):
                        em_count += 1
                except Exception as e:
                    # print("EM error")
                    print(e)
            if gold_type == predict_type and predict_type != 'Answerable':
                print("Question:"+turns[i].get('text',''))
                accs += 1
                print("\033[92mACCS+1\033[0m")
            if gold_type != predict_type:
                iaccs = False
                print("\033[91mIACCS failed\033[0m")
                
    if iaccs:
        print("\033[92mIACCS+1\033[0m")
        iaccs_count += 1

print("_____________________________________")

percentage2 = (accs / allqa) * 100
percentage2_iaccs = (iaccs_count / allturn) * 100
percentage3 = (em_count / allsqlqa) * 100
percentage4 = (qm_count / allsqlqa) * 100
percentage5 = (error_count / allsqla) * 100

print("Result")
print("_____________________________________")
print("| Metric | Count | Total | Percentage |")
print("|--------|-------|-------|------------|")

print(f"| ACCS   | {accs:<5} | {allqa:<5} | {percentage2:.1f}%      |")
print(f"| IACCS  | {iaccs_count:<5} | {allturn:<5} | {percentage2_iaccs:.1f}%      |")
print(f"| EM     | {em_count:<5} | {allsqlqa:<5} | {percentage3:.1f}%      |")
print(f"| QM     | {qm_count:<5} | {allsqlqa:<5} | {percentage4:.1f}%      |")
print(f"| ERROR  | {error_count:<5} | {allsqla:<5} | {percentage5:.1f}%      |")

print("-------------------------------------")
print("For more details, please refer to: https://github.com/mcxiaoxiao/MMSQL")