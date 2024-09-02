"""
llm_generation.py

This script generates responses using the Large Language Model (LLM) based on the test dataset "MMSQL_test.json".

Usage:
    python llm_generation.py outputs/llm_responses.json

Arguments:
    --output: Path to the output JSON file where the LLM responses will be saved.
"""

# Import the functions from /tools
import math
import os
from tools.api_request import request_gemini as request_llm
from tools.db_detail import db_getdesc
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
    
def get_system(db_name): 
    # Get db schema prompt
    description = db_getdesc(db_name)
    column_example = get_example(db_name)
    question = "Database schema:\n" + description + "\nExamples for each table:"+ column_example + "\nBased on the provided information, if the user's question cannot be accurately answered with an SQL query, indicate whether the question is ambiguous(Problem is not enough to generate SQL with sure tables and columns) or unanswerable(Unable to answer questions based on database information) and explain why. If the question is answerable, output only SQL query without additional content."
    return question

def process_json_part(data, output_file):
    for index1,item in enumerate(tqdm(data)):
        # Initialnize messages
        # print("__________"+str(index1)+"___________")
        system_instruct = get_system(item['db_name'])
        messages = [{"role": "system", "content": system_instruct}]
        for index, turn in enumerate(item['turns']):
            if turn['isuser']:
                # update messages
                user_question = turn['text']
                # print(str(index)+" type "+turn['type']+" Q: "+user_question)
                messages.append({"role": "user", "content": user_question})
                if index+1<len(item['turns']):
                    # llm input
                    # print(messages)
                    llm_response = request_llm(messages)
                    # llm record
                    # print("\nLLM Response:")
                    # print(llm_response)
                    item['turns'][index+1]['predict'] = llm_response
                    # update messages
                    g_ans = ""
                    if item['turns'][index+1]['text']:
                        g_ans = item['turns'][index+1]['text']
                    else:
                        g_ans = item['turns'][index+1]['query']
                    messages.append({"role": "assistant", "content": g_ans})
                    
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

def process_json_multithreaded(input_file, output_file, num_threads=20):
    with  open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
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
    parser = argparse.ArgumentParser(description="MMSQL-EVAL LLM GENERATION SCRIPT")
    parser.add_argument("output_file", help="Output JSON file path. Such as 'output/gemini-1,5-pro'")
    args = parser.parse_args()
    process_json_multithreaded('datasets/data_with_ids.json', args.output_file)