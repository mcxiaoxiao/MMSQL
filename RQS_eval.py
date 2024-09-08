"""
RQS_eval.py

Reads a specified JSON file and iterates through each object's 'turns' array to find a turn where 'isuser' is true and its following turn.

Usage:
    python RQS_eval.py outputs/Llama-3-70B.json outputs/gpt4_scored_Llama-3-70B.json

Arguments:
    --file_path: Path to the JSON file.
    --output_path: Path where the modified JSON file will be saved.
"""

from tools.api_request import request_gpt as request_llm
from tools.db_detail import db_getdesc
from tools.sql_execute import sqlite_execute as execute
import argparse
import json
from tqdm import tqdm

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
    

def ask_ai(db_name, question, answer_pred, answer_gold, gold_type):
    description = db_getdesc(db_name)
    column_example = get_example(db_name)
    template = """
{database_description}

{user_question}

{system_response}

{reference_answer}

Evaluate the quality of the system's response based on the following criteria. Assign 2 points directly if a criterion does not apply.
Relevance:
0 points: The response is completely irrelevant.
1 point: The response is partially relevant but misses key details.
2 points: The response is fully relevant and addresses the question adequately.
Clarity:
0 points: The response is incomprehensible.
1 point: The response is mostly clear with minor ambiguities.
2 points: The response is very clear and easy to understand.
Completeness:
0 points: The response does not address the question at all.
1 point: The response covers most aspects of the question but lacks some details.
2 points: The response thoroughly addresses all aspects of the question.
Accuracy:
0 points: The response contains factually incorrect information.
1 point: The response is partially accurate with some errors.
2 points: The response is completely accurate.
Utility:
0 points: The response does not meet the user's needs or explain the context of the question.
1 point: The response somewhat meets the user's needs and provides partial explanations.
2 points: The response excellently meets the user's needs and clearly explains the context or ambiguity of the question.
Task:
Classify the Response: Determine if the system response is 'improper'(Non-SQL based user questions), 'unanswerable'(unachievable under existing conditions), or 'ambiguous'(Lack of clarity).
Evaluate Each Criterion: Provide a detailed rationale for the score assigned to each criterion.
Calculate the Total Score: Sum the scores for all criteria.(10 points for a direct greeting alone)

Output Format:
{{
  "AnswerType": "",(text only)
  "Rationale": "",(text only, Explain the scoring of each criterion)
  "Score": ""(An integer from 0 to 10)
}}
    """
    filled_template = template.format(
        database_description="Database Description:"+ "\nDatabase schema:\n" + description + "\nExamples for each table:"+ column_example,
        user_question="User Question:" + question + "(Ground truth type:" + gold_type + ")",
        system_response="System Response:" + answer_pred,
        reference_answer="Reference Answer:" + answer_gold
    )
    
    # print(filled_template)

    messages = [{"role": "user", "content": filled_template}]
    max_attempts = 10
    attempt = 0
    while attempt < max_attempts:
        llm_response = request_llm(messages)
        print("LLM Response:", llm_response)
        select_pos = llm_response.find('{')
        colon_pos = llm_response.rfind('}')
        if select_pos != -1 and colon_pos != -1:
            llm_response = llm_response[select_pos:colon_pos+1].replace('\n',' ')
            print("formatted json "+llm_response)
        try:
            response_data = json.loads(llm_response)
            type_ai = response_data.get("AnswerType", "")
            rqs_ai = response_data.get("Score", 0)
            rationale_ai = response_data.get("Rationale", "")
            rationale_ai = str(rationale_ai)

            if int(rqs_ai) >= 0 and int(rqs_ai) <= 10:
                return type_ai, rqs_ai, rationale_ai
            else:
                raise ValueError("Response type or score out of expected range.")
        except (json.JSONDecodeError, KeyError, ValueError, TypeError, Exception) as e:
            print("\033[91mRQS_eval.py::: Retry Reason: {}\033[0m".format(str(e))) 
            attempt += 1
    return "error", 0, "error"

def process_turns(file_path, output_path):

    # Open and read the JSON file
    with open(file_path, 'r') as file:
        data = json.load(file)
    
    # Iterate over each object in the file
    for entry in tqdm(data):
        # Check if the 'turns' key exists
        print("__________________")
        if 'turns' in entry:
            turns = entry['turns']
            db_name = entry['db_name']
            length = len(turns)
            # Iterate over each turn in 'turns'
            for i in range(length):
                # Check if the current turn is a user turn
                if turns[i].get('isuser', False):
                    print(i//2)
                    # Output the current user's turn
                    print(turns[i].get('type', ''), "--", turns[i].get('text', ''))
                    # Check and process the next turn (if it exists)
                    if i + 1 < length:
                        next_turn = turns[i + 1]
                        predict_text = next_turn.get('predict', '')
                        print("Next Turn predict_text:", predict_text)
                        # Find the positions of SELECT and the semicolon
                        select_pos = predict_text.upper().find('SELECT')
                        colon_pos = predict_text.find(';', select_pos)
                        if select_pos != -1 and colon_pos != -1:
                            predict_sql = predict_text[select_pos:colon_pos].replace('\n',' ')
                        elif select_pos != -1:
                            predict_sql = predict_text[select_pos:].replace('\n',' ')
                        else:
                            predict_sql = ""
                        # Store the result in a new field 'predict_sql'
                        next_turn['predict_sql'] = predict_sql
                        # Calculate the ratio of the extracted SQL to the entire predict field
                        if len(predict_text) == 0:
                            ratio = 0
                        else:
                            ratio = len(predict_sql) / len(predict_text)
                            
                        if predict_sql != "" and ratio >= 0.5:
                                next_turn['predict_type'] = 'answerable'
                                if turns[i].get('type', '') == 'answerable':
                                    next_turn['RQS'] = "N/A"
                                else:
                                    next_turn['RQS'] = 0
                        else:
                            next_turn['predict_type'] = 'not answerable'
                            # Ask LLM, Get categorized and RQS scored based on database, questions, answers, gold answer
                            if turns[i].get('text', '').lower() == "thanks!":
                                print("Direct greeting. SKIP")
                                type_ai = "improper"
                                rqs_ai = 10
                                rationale_ai = "Direct greeting"
                            else:
                                type_ai, rqs_ai, rationale_ai = ask_ai(db_name,turns[i].get('text', ''),predict_text,next_turn.get('text', ''),turns[i].get('type', '')) 
                            next_turn['predict_type'] = type_ai
                            next_turn['RQS'] = rqs_ai
                            next_turn['RQS_Rationale'] = rationale_ai
                        
                        print("Predict Type:", next_turn['predict_type'])
                    else:
                        print("Next Turn does not exist.")
    
    # Save the modified data to a new JSON file
    with open(output_path, 'w') as outfile:
        json.dump(data, outfile, indent=4)


def main():
    parser = argparse.ArgumentParser(description='Process JSON files.')
    parser.add_argument('input_file', type=str, help='Path to the input JSON file')
    parser.add_argument('output_file', type=str, help='Path to the output JSON file')
    args = parser.parse_args()
    process_turns(args.input_file, args.output_file)

if __name__ == "__main__":
    main()
