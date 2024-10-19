# Import the functions from /tools
import math
import os

# You need to choose one of the api's or hf's "request_llm" function here. 
# from tools.hf_open_source_llm_request import request_llm
# from tools.api_request import request_gpt as request_llm
# from tools.api_request import request_gemini as request_llm 

from tools.db_detail import db_getdesc
from tools.db_detail import db_getnames
from tools.sql_execute import sqlite_execute as execute
import threading
import concurrent
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import json
import argparse

def sql_evoke(query,db_name):
    result, execution_time ,executable = execute("datasets/cosql_dataset/database/"+db_name+"/"+db_name+".sqlite",query)
    return result 

def get_example(db_name):
    sql_query = "SELECT name FROM sqlite_master WHERE type='table';"
    result = sql_evoke(sql_query,db_name)
    column_example=""
    for table_name in result:
        column_example = column_example + table_name[0] + ":\n"
        sql_get_eg = "SELECT * FROM "+ table_name[0] +" LIMIT 3;"
        table_eg = sql_evoke(sql_get_eg,db_name)
        for table_data in table_eg:
            column_example = column_example + '('
            for column_data in table_data: 
                column_example = column_example + str(column_data) +','
            column_example = column_example[:-1] + ')\n'
    return column_example

# print(db_getdesc("car_1"),get_example("car_1"))
from agents.rewriter import Rewriter
from agents.selector import Selector
from agents.detector import Detector
from agents.decomposer import Decomposer
from agents.refiner import Refiner

# creat and name the agents
rewriter = Rewriter("Rewriter")
selector = Selector("Selector")
detector = Detector("Detector")
decomposer = Decomposer("Decomposer")
refiner = Refiner("Refiner")

# input_data = "hey!"
# output_rewriter = rewriter.process_input(input_data)
# output_selector = selector.process_input(input_data)
# output_detector = detector.process_input(input_data)
# output_decomposer = decomposer.process_input(input_data)
# output_refiner = refiner.process_input(input_data)




def solve_answerable(db_name, output_selector, question):
    output_decomposer = ""
    output_refiner = ""
    
    print("________Decompose question and solve________")
    input_data = {
    "evidence": "",
    "db_name": db_name,
    "mini_schema": output_selector,
    "question": question,
    }

    output_decomposer = decomposer.process_input(input_data)
    print(output_decomposer)
    
    if output_decomposer["executable"]:
        return output_decomposer["sql"], output_decomposer, output_refiner
        # sql_output = " Result:" + str(output_decomposer["result"])
    else:
        
        print("________Refines erroneous SQL queries________")
        input_data = {
        "evidence": "",
        "db_name": db_name,
        "mini_schema": output_selector,
        "question": question,
        "old_sql": output_decomposer.get("sql"),
        "log": output_decomposer.get("log")
        }
        
        
        output_refiner = refiner.process_input(input_data)
        # print(output_refiner)
        print(output_refiner)
        return output_refiner["sql"], output_decomposer, output_refiner
        
        # if output_decomposer["executable"]:
        #     sql_output = " Result:" + str(output_refiner["result"])

        
def process_json_part(data, output_file):
    for index1,item in enumerate(tqdm(data)):
        retries = 0
        while retries < 2:
            try:
                # print(item)
                # Initialnize messages
                id_now = item.get('id')
                print("id " + str(id_now) + " Turn "+str(index1)+" ==================================================================")
                db_name = item['db_name']
                previous_QA = ""
                print(id_now)
                
                for index, turn in enumerate(item['turns']):
                    
                    if turn['isuser']:
                        final_output = ""
                        output_rewriter = ""
                        output_selector = ""
                        output_detector = ""
                        output_decomposer = ""
                        output_refiner = ""
                        final_output = ""
                        rewritten_questions = []
                        rewritten_outputs = []
                        sql_output = ""
                        user_question = turn['text']
                        question_type = turn['type']
        
                        print("previous_QA " + ":" + previous_QA)
                        print("question " + str(index//2) + ":\033[93m " + user_question + "\033[0m")
                        
                        if index+1<len(item['turns']):
        
                            # print("________Question rewriter________")
                            # input_data = {
                            #     "db_desc": db_getnames(db_name),
                            #     "evidence": "",
                            #     "question": user_question,
                            #     "previous_QA": previous_QA
                            # }
                            
                            # output_rewriter = rewriter.process_input(input_data)
                            
                            # if output_rewriter["improper"] == "YES":
                            #     final_output = output_rewriter["text"]

                            if user_question == "":
                                continue
                            
                            else:
                                # rewritten_question = output_rewriter["text"]
                                rewritten_question = "previous QA:" + previous_QA + "\ncurrent question:" + user_question
                                
                                print("________Select columns and values________")
                                input_data = {
                                    "evidence": "",
                                    "db_name": db_name,
                                    "db_desc": db_getdesc(db_name),
                                    "db_exam": get_example(db_name),
                                    "question": rewritten_question 
                                }
                                
                                # output_selector = selector.process_input(input_data)
                                output_selector = db_getdesc(db_name) + "Value examples:" + get_example(db_name)
                                print(output_selector)
                            
                                
                                print("________Question type detect________")
                                input_data = {
                                    "evidence": "",
                                    "db_name": db_name,
                                    "db_desc": db_getdesc(db_name),
                                    "mini_schema": output_selector,
                                    "question": rewritten_question
                                }
                                
                                output_detector = detector.process_input(input_data)
                                if output_detector == "YES":

                                
                                # if "YES" == "YES":
                                    final_output, output_decomposer, output_refiner = solve_answerable(db_name, output_selector, rewritten_question)
                                    
                                else:
                                        
                                    final_output = output_detector.get("answer",output_detector)

                                    if output_detector.get("type",'').lower() != 'improper':
                                        rewritten_questions = output_detector.get("rewrite",[])
                                        rewritten_questions.append(user_question)
                                        print("rewritten_questions: :\033[94m" + str(rewritten_questions) + "\033[0m")
                                        
                                        for rewritten_question in rewritten_questions:
                                            possible_output, output_decomposer, output_refiner = solve_answerable(db_name, output_selector, "previous QA:" + previous_QA + "\ncurrent question:" + rewritten_question)
                                            if possible_output != "":
                                                rewritten_outputs.append(possible_output)
                                                            
                            # llm record
                            print("\nFINAL Response:")
                            print(final_output)
                            
                            item['turns'][index+1]['predict'] = final_output
                            item['turns'][index+1]['rewritten_questions'] = rewritten_questions
                            item['turns'][index+1]['rewritten_outputs'] = rewritten_outputs

                            
                            
                            item['turns'][index+1]['Rewriter'] = output_rewriter
                            item['turns'][index+1]['Selector'] = output_selector
                            item['turns'][index+1]['Detector'] = output_detector
                            item['turns'][index+1]['Decomposer'] = output_decomposer
                            item['turns'][index+1]['Refiner'] = output_refiner
                            
                            # update messages
                            g_ans = ""
                            if item['turns'][index+1]['text']:
                                g_ans = item['turns'][index+1]['text']
                            else:
                                g_ans = item['turns'][index+1]['query']
                            if question_type == "answerable":
                                sql_result = sql_evoke(g_ans,db_name)
                                sql_output = " Result:" + str(sql_result)
                            # previous_QA += "\nQ:" + user_question + "\nA:" + g_ans + sql_output + '\n'
                            previous_QA += "\nQ:" + user_question + "\nA:" + g_ans + '\n'
                            print("gold answer: " + g_ans)
                            print("————————————————————————————————————————————————————————————")
                            
                if not os.path.exists(output_file):
                    with open(output_file, 'w') as f:
                        items = [item]
                        json.dump(items, f, indent=4)
                        f.write('\n')
                else:
                    with open(output_file, 'r') as f:
                        try:
                            items = json.load(f)
                        except json.JSONDecodeError:
                            print("\033[91mError:The file content is not in valid JSON format\033[0m")
                            # items = []
        
                    if not isinstance(items, list):
                        print("\033[91mError:The file content is not in valid JSON format\033[0m")
                        # items = []

                    items.append(item)

                    with open(output_file, 'w') as f:
                        json.dump(items, f, indent=4)
                        f.write('\n')
                break
            except Exception as e:
                retries += 1
                print(f"\033[91m==============Error processing id {id_now} data index {index} (attempt {retries}): {e}==============\033[0m")


def process_json_multithreaded(input_file, output_file, num_threads=2):
    with  open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        data = data[:]
    # split
    data_parts = []
    chunk_size = math.ceil(len(data) / num_threads)  # Round up to ensure all data is included
    for i in range(num_threads):
        start = i * chunk_size
        end = min((i + 1) * chunk_size, len(data))  # Ensure we don't go beyond the end of the data
        data_parts.append(data[start:end])

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        for part in data_parts:
            future = executor.submit(process_json_part, part, output_file)
            futures.append(future)
        concurrent.futures.wait(futures)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MMSQL-EVAL MULTI-AGENT LLM GENERATION SCRIPT")
    parser.add_argument("output_file", help="Output JSON file path. Such as 'output/gemini-1.5-pro'")
    args = parser.parse_args()
    process_json_multithreaded('datasets/MMSQL_test.json', args.output_file)