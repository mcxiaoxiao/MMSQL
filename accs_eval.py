"""
accs_eval.py

This script calculates several metrics from the output JSON files, including base metric (e.g. ACCS, IACCS, EM, QM...) and analytical results.

Usage:
    python accs_eval.py outputs/gpt_gemini-1-Copy1.5-flash-llm.json

Arguments:
    --input: Path to the input JSON file containing the LLM responses.
"""

from collections import defaultdict
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

from tools.process_sql import tokenize, get_schema, get_tables_with_alias, Schema, get_sql

import nltk

try:
    nltk.data.find('punkt_tab')  # check
except LookupError:
    print("check::: punkt_tab not found，start download...")
    nltk.download('punkt_tab')  # auto download
    print("punkt_tab has installed")
else:
    print("check::: punkt_tab exist")


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

    print("execute sql " + query)
    global error_count
    conn = None
    cursor = None
    try:
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        cursor.execute(query)
        result = cursor.fetchall()
        print()
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

def calculate_metrics(correct, gold, predict):
    precision = correct / predict if predict > 0 else 0
    recall = correct / gold if gold > 0 else 0
    return precision, recall

def calculate_f1(precision, recall):
    if precision + recall == 0:
        return 0
    return 2 * (precision * recall) / (precision + recall)

def eval_exec_match(db_path, db, p_str, g_str):
    """Evaluates the EM of SQL query.

    Args:
        db_path (str): Path to the SQLite database directory.
        db (str): Name of the SQLite database file.
        p_str (str): The predicted SQL query.
        g_str (str): The gold standard SQL query.

    Returns:
        bool: True if the predicted and gold standard queries produce the same results, False otherwise.
    """
    # Preprocess the queries
    p_str = p_str.replace("```", "").replace(";", "").replace("`", "'").replace(" ", " ").replace("\"", "'")
    g_str = g_str.replace("```", "").replace(";", "").replace("`", "'").replace(" ", " ").replace("\"", "'")

    # Handle potential '=' issues
    split_index = p_str.find('=')
    if split_index != -1:
        p_str = p_str[:split_index] + ' = ' + p_str[split_index + 1:]
    split_index = g_str.find('=')
    if split_index != -1:
        g_str = g_str[:split_index] + ' = ' + g_str[split_index + 1:]

    # Execute the queries
    db_file = os.path.join(db_path, db, db + ".sqlite")
    g_r = execute_query(db_file, g_str)
    p_r = execute_query(db_file, p_str)

    # Print the results for debugging
    print("Gold Result")
    print(g_r)
    print("Pred Result")
    print(p_r)

    # Compare the results
    if "ORDER BY" in g_str:
        # If the gold standard query has an ORDER BY clause, the results must be identical
        return g_r == p_r
    else:
        # If the gold standard query doesn't have an ORDER BY clause, the results must have the same elements (regardless of order)
        return set(g_r) == set(p_r)


# def eval_exec_match(db_path,db, p_str, g_str):
#     # p_str = p_str.lower()
#     # g_str = g_str.lower()
#     # p_str = p_str.replace("`","'")
#     # p_str = p_str.replace("▁"," ")
#     # g_str = g_str.replace(">="," >= ")
#     # p_str = p_str.replace(">="," >= ")
#     # split_index = p_str.find('=')
#     # if split_index != -1:
#     #     p_str = p_str[:split_index] + ' = ' + p_str[split_index + 1:]
#     # split_index = g_str.find('=')
#     # if split_index != -1:
#     #     g_str = g_str[:split_index] + ' = ' + g_str[split_index + 1:]
#     # p_str = ' '.join(p_str.split())
#     # g_str = ' '.join(g_str.split())
#     # p_str = p_str.replace("\"","'")
#     # g_str = g_str.replace("\"","'")
#     db = os.path.join(db_path, db, db + ".sqlite")
#     schema = Schema(get_schema(db))
#     print("E Gold:"+g_str)
#     print("E Pred:"+p_str)
#     gold = get_sql(schema, g_str)
#     pred = get_sql(schema, p_str)


#     with ThreadPoolExecutor(max_workers=1) as executor:

#         future = executor.submit(execute_query, db, p_str)
#         try:
#             p_res = future.result(timeout=10) 
#         except TimeoutError:
#             print("Timeout")
#             return False
#         except Exception as e:
#             print(f"SQL ERROR: {e}")
#             return False
            

#         future = executor.submit(execute_query, db, g_str)
#         try:
#             q_res = future.result(timeout=10) 
#         except TimeoutError:
#             print("Timeout")
#             return False
#         except Exception as e:
#             print(f"SQL ERROR: {e}")
#             return False

#     def res_map(res, val_units):
#         rmap = {}
#         for idx, val_unit in enumerate(val_units):
#             key = tuple(val_unit[1]) if not val_unit[2] else (val_unit[0], tuple(val_unit[1]), tuple(val_unit[2]))
#             rmap[key] = [r[idx] for r in res]
#         return rmap

#     p_val_units = [unit[1] for unit in pred['select'][1]]
#     q_val_units = [unit[1] for unit in gold['select'][1]]

#     return res_map(p_res, p_val_units) == res_map(q_res, q_val_units)



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


def parse_sql(predict_text):
    select_pos = predict_text.upper().find('SELECT')
    colon_pos = predict_text.find(';', select_pos)
    if select_pos != -1 and colon_pos != -1:
        predict_sql = predict_text[select_pos:colon_pos].replace('\n',' ')
    elif select_pos != -1:
        predict_sql = predict_text[select_pos:].replace('\n',' ')
    else:
        predict_sql = ""
    return predict_sql

def calculate_metrics(correct, total_gold, total_pred):
    precision = correct / total_pred if total_pred > 0 else 0
    recall = correct / total_gold if total_gold > 0 else 0
    return precision, recall


def qm(db_path,p_str,g_str,db):
    # print("Initial Gold SQL:"+g_str)
    # p_str = p_str.lower()
    # g_str = g_str.lower()
    p_str = p_str.replace("```","")
    p_str = p_str.replace(";","")
    g_str = g_str.replace("```","")
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

    g_str = g_str.replace("\"","'")
    db_name = db
    db = os.path.join(db_path, db, db + ".sqlite")
    schema = Schema(get_schema(db))
    g_sql = get_sql(schema, g_str)
    p_sql = get_sql(schema, p_str)
    print("Gold SQL:"+g_str)
    print("Predict SQL:"+p_str)
    exact_score = evaluator.eval_exact_match(p_sql, g_sql)
    return exact_score

parser = argparse.ArgumentParser(description='evaluation of AccS. Input JSON file path.')
parser.add_argument('json_file_path', type=str, help='Path to the JSON file')


args = parser.parse_args()


with open(args.json_file_path, 'r', encoding='utf-8') as file:
    data = json.load(file)

duem = 0
iduem_count = 0
qm_count = 0
im_count = 0
allsqlqa = 0
allsqla = 0
em_count = 0
accs = 0
allqa = 0
iaccs_count = 0 
allturn = 0
RQS_count = 0
RQS_sum = 0
rewritten_count_ans = 0
rewritten_correct_ans = 0
rewritten_count_amb = 0
rewritten_correct_amb = 0

gold_counts = defaultdict(int)
predict_counts = defaultdict(int)
correct_counts = defaultdict(int)

turn_qm_counts = defaultdict(int)
turn_total_counts = defaultdict(int)

AmbA = 0
AmbA_count = 0
AmbClaA = 0
AmbClaA_count = 0

rqs_sums = defaultdict(int)
rqs_counts = defaultdict(int)





for element in tqdm(data):
    print("____________________________________")
    db_name = element.get('db_name')
    print("DB Name:"+db_name)
    turns = element.get('turns', [])

    allturn += 1
    iaccs = True
    imatch = True
    iduem = True
    for i in range(len(turns) - 1):
        
        turn_number = (i) // 2 
        if turns[i].get('type','') == 'answerable':
        
            turn_total_counts[turn_number+1] += 1  

        # if  turns[i].get('RQS','N/A') != 'N/A':
        predict_type = turns[i].get('predict_type','answerable')
        gold_type = turns[i-1].get('type','')
        print("RQS Gold Type:"+str(gold_type))
        print("RQS Predict Type:"+str(predict_type))
        if gold_type != 'answerable':
            RQS_count += 1
            RQS = 0
            if predict_type == gold_type:
                RQS = turns[i].get('RQS','0')
            RQS_sum += int(RQS)
            print("RQS:"+str(RQS))
            if gold_type in ['unanswerable', 'ambiguous', 'improper']:
                rqs_sums[gold_type] += int(RQS)
                rqs_counts[gold_type] += 1


        if i%2 == 0:
            print("\n========turn:"+str((i+1)//2))
            print("Question:"+turns[i].get('text',''))
            print("Answer:" + turns[i+1].get('predict', '').encode('gbk', 'replace').decode('gbk'))
        if turns[i].get('isuser'):
            allqa+=1
            # print(turns[i]['text'])
            gold_type = turns[i].get('type','')
            predict_type = turns[i+1].get('predict_type','answerable')
            # if isinstance(turns[i+1].get('Detector',{}), dict):
            #     predict_type = turns[i+1].get('Detector',{}).get('type',predict_type)
            
            if len(gold_type) == 0:
                gold_type ='answerable'
            if len(predict_type) == 0:
                predict_type = 'answerable'
            print("Gold Type:"+str(gold_type))
            print("Predict Type:"+str(predict_type))
            
            gold_counts[gold_type] += 1
            predict_counts[predict_type] += 1
            if gold_type == predict_type:
                correct_counts[gold_type] += 1

            if gold_type == 'answerable':
                allsqlqa += 1

            if gold_type == predict_type and predict_type == 'answerable':

                allsqla += 1

                if i-2 >= 0 and turns[i-2].get('type','') == 'ambiguous':
                    AmbClaA_count += 1
                try:
                    
                    if eval_exec_match("datasets/cosql_dataset/database",db_name, turns[i+1].get('predict_sql',''), turns[i+1].get('query','')):
                        em_count += 1
                        duem += 1

                        print("\033[92mEM+1\033[0m")
                        print("\033[92mDUEM+1\033[0m")
                    else:
                        iduem = False
                        print("\033[91mIDUEM failed\033[0m")
                        print("\033[91mEM error\033[0m")
                except Exception as e:
                    print("\033[91mEM error\033[0m")
                    print(e)

                try:
                    # print("Question:"+turns[i].get('text',''))
                    if qm("datasets/cosql_dataset/database", turns[i+1].get('predict_sql',''),turns[i+1].get('query',''), db_name):
                        qm_count += 1
                        accs += 1
                        print("\033[92mACCS+1\033[0m")
                        turn_qm_counts[turn_number+1] += 1 
                        if i-2 >= 0 and turns[i-2].get('type','') == 'ambiguous':
                            AmbClaA += 1
                            print("\033[92mAmbClaA+1\033[0m")
                        print("\033[92mACCS+1\033[0m")
                    else:
                        iaccs = False
                        imatch = False
                        print("QM nok\n")
                        print("\033[91mIACCS failed\033[0m")
                except Exception as e:
                    print("\033[91mQM error\033[0m")
                    # print(turns[i+1].get('query',''))
                    # print(turns[i+1].get('predict_sql',''))
                    print(e)
                    
                    accs += 0
                    iaccs = False
                    imatch = False
                    print("\033[91mIACCS failed\033[0m")



            if gold_type == 'ambiguous' and predict_type == 'answerable':      
                AmbA_count += 1
                try:
                    print("AMBA")
                    ambiguous_ans = parse_sql(turns[i+1].get('predict',''))
                    print(ambiguous_ans)
                    if qm("datasets/cosql_dataset/database",turns[i+3].get('query',''), ambiguous_ans, db_name):
                        AmbA += 1
                        print("\033[92mAmbA+1\033[0m")
                except Exception as e:
                    print("\033[91mAmbA error\033[0m")
                    print(e)
            
                
            if gold_type == predict_type and predict_type != 'answerable':
                # print("Question:"+turns[i].get('text',''))
                duem += 1
                accs += 1
                print("\033[92mACCS+1\033[0m")
                print("\033[92mDUEM+1\033[0m")



            if gold_type != predict_type:
                iaccs = False

                print("\033[91mIACCS failed\033[0m")


            if gold_type == 'ambiguous' and predict_type == 'ambiguous':
                rewritten_count_amb += 1
                rewriten_success = False
                if len(turns[i+1].get('rewritten_outputs',[])) > 0:
                    for rewritten_output in turns[i+1].get('rewritten_outputs',[]):
                        print("Rewritten Output:"+rewritten_output)
                        try:
                            if qm("datasets/cosql_dataset/database",rewritten_output,turns[i+3].get('query',''), db_name):
                                rewriten_success = True
                                break
                        except Exception as e:
                            print(e)
                if rewriten_success:
                    rewritten_correct_amb += 1


            if gold_type == 'answerable' and predict_type == 'unanswerable':

                iduem = False
                print("\033[91mIDUEM failed\033[0m")

            if gold_type == 'answerable' and predict_type == 'ambiguous':
                # rewritten QAs to save the score
                imatch = False
                rewritten_count_ans += 1
                rewriten_success = False
                if len(turns[i+1].get('rewritten_outputs',[])) > 0:
                    for rewritten_output in turns[i+1].get('rewritten_outputs',[]):
                        print("Rewritten Output:"+rewritten_output)
                        # try:
                        #     if qm("datasets/cosql_dataset/database",rewritten_output,turns[i+1].get('query',''), db_name):
                        #         qm_count += 1
                        #         accs += 1
                        #         print("\033[92mACCS+1\033[0m")
                        #         print("\033[92mQM+1\033[0m")
                        #         break
                        #     else:
                        #         print("\033[91mQM failed\033[0m")
                        # except Exception as e:
                        #     print("\033[91mQM error\033[0m")
                        #     print(e)
                        #     print("\033[91mQM failed\033[0m")
                        try:
                            if eval_exec_match("datasets/cosql_dataset/database",db_name, rewritten_output, turns[i+1].get('query','')):
                                rewriten_success = True
                                print("\033[92mDUEM+1\033[0m")
                                print("\033[92mEM+1\033[0m")
                                break
                            else:
                                print("\033[91mEM failed\033[0m")
                        except Exception as e:
                            print("\033[91mEM error\033[0m")
                            print(e)
                            print("\033[91mEM failed\033[0m")
                if rewriten_success:
                    rewritten_correct_ans += 1
                    em_count += 1
                    duem += 1
                    print("\033[92mDUEM+1\033[0m")

                else:
                    iduem = False
                    print("\033[91mIDUEM failed\033[0m")
                    print("\033[91mEM failed\033[0m")
                    
                
                
    if iaccs:
        print("\033[92mIACCS+1\033[0m")
        iaccs_count += 1
    if imatch:
        print("\033[92mIM+1\033[0m")
        im_count += 1
    if iduem:
        print("\033[92mIDUEM+1\033[0m")
        iduem_count += 1


print("_____________________________________")
percentage1= (duem / allqa) * 100
percentage1_iduem = (iduem_count / allqa) * 100
percentage2 = (accs / allqa) * 100
percentage2_iaccs = (iaccs_count / allturn) * 100
percentage3 = (em_count / allsqla) * 100
percentage4 = (qm_count / allsqla) * 100
percentage5 = (error_count / allsqla) * 100
percentage6 = (im_count / allturn) * 100


print("A. Overall Result Analysis")
print("_____________________________________")
print("| Metric | Count | Total | Percentage |")
print("|--------|-------|-------|------------|")
print(f"| DUEM   | {duem:<5} | {allqa:<5} | {percentage1:.1f}%      |")
print(f"| IDUEM   | {iduem_count:<5} | {allqa:<5} | {percentage1_iduem:.1f}%      |")

print(f"| QM     | {qm_count:<5} | {allsqlqa:<5} | {percentage4:.1f}%      |")
print(f"| EM     | {em_count:<5} | {allsqlqa:<5} | {percentage3:.1f}%      |")

print(f"| ACCS   | {accs:<5} | {allqa:<5} | {percentage2:.1f}%      |")
print(f"| IACCS  | {iaccs_count:<5} | {allturn:<5} | {percentage2_iaccs:.1f}%      |")

print(f"| ERROR  | {error_count:<5} | {allsqlqa:<5} | {percentage5:.1f}%      |")
print(f"| IM     | {im_count:<5} | {allturn:<5} | {percentage6:.1f}%      |")
print("-------------------------------------")


categories = ['answerable', 'unanswerable', 'ambiguous', 'improper']


print("B. Category Analysis")
print("__________________________________________________")
print("| Category       | Precision | Recall | F1 Score |")
print("|----------------|-----------|--------|----------|")

f1_scores = []

for category in categories:
    precision, recall = calculate_metrics(correct_counts[category], gold_counts[category], predict_counts[category])
    f1 = calculate_f1(precision, recall)
    f1_scores.append(f1)
    print(f"| {category.capitalize():<14} | {precision*100:.1f}%    | {recall*100:.1f}%  | {f1*100:.1f}%  |")

average_f1 = sum(f1_scores) / len(f1_scores)
print("__________________________________________________")
print(f"| {'Average F1':<14} | {'':<9} | {'':<6} | {average_f1*100:.1f}%  |")
print("__________________________________________________")
# print("__________________________________________________")

print("C. Turn-wise QM Statistics")
print("_________________________________________")
print("| Turn  | QM Count | Total | Percentage |")
print("|-------|----------|-------|------------|")

for turn in sorted(turn_total_counts.keys()):
    qm_count_t = turn_qm_counts[turn]
    total_count = turn_total_counts[turn]
    percentage = (qm_count_t / total_count) * 100 if total_count > 0 else 0
    print(f"| {turn:<5} | {qm_count_t:<8} | {total_count:<5} | {percentage:.1f}%      |")


qm_count_5plus = sum(count for turn, count in turn_qm_counts.items() if turn > 4)
total_count_5plus = sum(count for turn, count in turn_total_counts.items() if turn > 4)
percentage_5plus = (qm_count_5plus / total_count_5plus) * 100 if total_count_5plus > 0 else 0
print(f"| >4    | {qm_count_5plus:<8} | {total_count_5plus:<5} | {percentage_5plus:.1f}%      |")

print("_________________________________________")

print("D. Answerable QA vs. Ambiguous QA turns QM Analysis")
print("___________________________________________________")
print("| Metric             | Count | Total | Percentage |")
print("|--------------------|-------|-------|------------|")
print(f"| Ans.Q+ans          | {qm_count:<5} | {allsqlqa:<5} | {percentage4:.1f}%      |")
print(f"| Amb.Q+ans          | {AmbA:<5} | {AmbA_count:<5} | {(AmbA/AmbA_count)*100:.1f}%      |")
print(f"| Amb.Q+clarify+ans  | {AmbClaA_count:<5} | {allturn:<5} | {(AmbClaA_count/allturn)*100:.1f}%      |")
print("___________________________________________________")


print("E. RQS Averages by Category")
print("________________________________")
print("| Category       | Average RQS |")
print("|----------------|-------------|")

total_rqs_sum = 0
total_rqs_count = 3

for category in ['unanswerable', 'ambiguous', 'improper']:
    

    if rqs_counts[category] > 0:
        # print(rqs_sums[category] , rqs_counts[category])
        avg_rqs = rqs_sums[category] / rqs_counts[category]
        print(f"| {category.capitalize():<14} | {avg_rqs:.2f}        |")
        total_rqs_sum += avg_rqs
    else:
        print(f"| {category.capitalize():<14} | N/A         |")
        total_rqs_sum += 0
print("________________________________")

if total_rqs_count > 0:
    overall_avg_rqs = total_rqs_sum / total_rqs_count
    print(f"| Overall Average | {overall_avg_rqs:.2f}        |")
else:
    print(f"| Overall Average | N/A         |")

print("________________________________")

print("F. Rewritten QA Analysis")
print("_____________________________________________")
print("| Metric       | Count | Total | Percentage |")
print("|--------------|-------|-------|------------|")
if rewritten_count_ans != 0:
    print(f"| Ans.Q+Amb    | {rewritten_correct_ans:<5} | {rewritten_count_ans:<5} | {(rewritten_correct_ans/rewritten_count_ans)*100:.1f}%      |")
if rewritten_count_amb != 0:
    print(f"| Amb.Q+Amb    | {rewritten_correct_amb:<5} | {rewritten_count_amb:<5} | {(rewritten_correct_amb/rewritten_count_amb)*100:.1f}%      |")
print("_____________________________________________")



import pyfiglet

ascii_art = pyfiglet.figlet_format("MMSQL")
print(ascii_art)

print("We appreciate your interest! For more details and if you have any questions, please refer to: https://github.com/mcxiaoxiao/MMSQL")