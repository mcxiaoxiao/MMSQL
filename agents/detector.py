from .agent import Agent
import json


class Detector(Agent):
    def process_input(self, input_data):
        return self.detect(input_data)

    def detect(self, input_data):
        data = {"answerable": "no", "type": "ambiguous", "answer": "Do you mean 'amc' as in model type or carmaker? Did you mean the full name of the carmaker amc?", "rewrite": ["What is the full name of the carmaker 'amc'", "What is the full name of the carmaker which made the model type named 'amc'"]}
        json_string_1 = json.dumps(data)
        data = {"answerable": "Yes"}
        json_string_2 = json.dumps(data)
        
        sys_prompt = """As an experienced and professional database administrator, your task is to analyze a user question. If the question type is: 'improper' / 'unanswerable' / 'ambiguous', directly answer with the appropriate term. If the question type is 'answerable', directly respond with "Yes". You need to identify the problem type step by step and output. The output should contain JSON format."""
        if input_data["mini_schema"] == "None":
            usr_prompt = f"""告诉用户问题不可被回答并根据数据库schema给出修改问题的建议（你可以这样问...）
[DB_ID] {input_data["db_desc"]}
[Schema] 
{input_data["mini_schema"]}
[Question]
{input_data["question"]}
[Evidence]
{input_data["evidence"]}
"""
        else:
            usr_prompt = f"""
[Requirements]
1. If the user's current question confirms an assumption made in a previous Answer, the answer will be based on that assumption. You can make your own limited and reasonable guesses about the user's intent based on the previous question and the current question.
2. If the user's question is part of a routine conversation unrelated to the SQL, so the question is improper. just answer directly. For example, the current question express gratitude or asks about functions not available outside the database or in llm. don't output "Yes" but give polite and helpful answers.
3. Determine if the current question can be answered accurately based on the provided database schema. If it is unable to answer questions based on database information the question is unanswerable, express expressing Apologies and explain difficulties to the user. 
4. You need to first try to select possible corresponding fields for each entity and condition in the question, and decide whether the question is answerable or ambiguous based on the matches
5. Check for ambiguity in the user's current question. If multiple fields have similar meanings with columns or conditions for user queries the question is ambiguous (Problem is not enough to generate SQL with sure tables and columns), ask the user to clarify which field they are referring to or clarify the conditions.
6. If the question is ambiguous or unanswerable, you must guess the user's intent and make only minor adjustments to make the refined question examples answerable and put it in the "rewrite". Choose one from improper/unanswerable/ambiguous and put it in the "type"
7. Output "answerable" is "Yes" if the question can be answered with certainty for each column and condition. No need to fill in "answer" in this case. 

[DB_ID] car_1
[Schema] 
Table:car_makers
[('Id', id type:number PRIMARY KEY. Value examples:[1, 2, 3]),('Maker', maker type:text. Value examples:[amc, volkswagen, bmw]),('FullName', full name type:text. Value examples:[American Motor Company, Volkswagen, BMW]),('Country', country type:text. Value examples:[1, 2, 3]),]
Table:model_list
[('ModelId', model id type:number PRIMARY KEY. Value examples:[1, 2, 3]),('Maker', maker type:number. Value examples:[1, 2, 3]),('Model', model type:text. Value examples:[amc, audi, bmw]),]
Table:car_names
[('MakeId', make id type:number PRIMARY KEY. Value examples:[1, 2, 3]),('Model', model type:text. Value examples:[chevrolet, buick, plymouth]),('Make', make type:text. Value examples:[chevrolet chevelle malibu, buick skylark 320, plymouth satellite]),]
Foreign keys:
model_list.'Maker' = car_makers.'Id'
car_names.'Model' = model_list.'Model'

[Question]
previous QA:
current question: What is the name of AMC?
[Evidence]

[Answer]
The single user question is not routine conversation unrelated to the SQL, not the improper.
The problem is related to the current database, not unanswerable.
Match possible database sections:
entities: 
name - car_makers.'Maker', car_makers.'FullName', car_names.'Model', car_names'Make'
conditions: 
AMC - model_list.'Model', car_makers.'Maker'
Unable to derive user intent through common sense. ask for clarification and give advice and must rewrite an answerable question: 
{json_string_1}
Question Solved. 
========== 
[DB_ID] car_1
[Schema] 
Table:countries
[('CountryName', country name type:text. Value examples:[usa, germany, france]),('Continent', continent type:number. Value examples:[1, 2, 3]),]
Table:car_makers
[('Maker', maker type:text. Value examples:[amc, volkswagen, bmw]),('FullName', full name type:text. Value examples:[American Motor Company, Volkswagen, BMW]),('Country', country type:text. Value examples:[1, 2, 3]),]
Table:model_list
[('ModelId', model id type:number PRIMARY KEY. Value examples:[1, 2, 3]),('Maker', maker type:number. Value examples:[1, 2, 3]),('Model', model type:text. Value examples:[amc, audi, bmw]),]
Table:car_names
[('MakeId', make id type:number PRIMARY KEY. Value examples:[1, 2, 3]),('Model', model type:text. Value examples:[chevrolet, buick, plymouth]),('Make', make type:text. Value examples:[chevrolet chevelle malibu, buick skylark 320, plymouth satellite]),]
Foreign keys:
car_names.'Model' = model_list.'Model'

[Question]
previous_QA :
Q:What are the name of amc?
A:Did you mean the full name of the car maker amc?

Q:Yes
A:select fullname from car_makers where maker = "amc"

Q:What type of car making by german?
A:Sorry we don't have information about type of car. Can you clarify your question?

Q:What kind of car is produced in Germany?
A:Did you mean the car models produced in Germany?

Q:Yes
[Evidence]

[Answer]
Current user issues confirm previous assumptions: "car models produced in Germany", not the improper.
The Question is related to the database, not unanswerable.
Match possible database sections:
entities: 
car models - model_list.'model' 
conditions: 
Germany - car_makers.'Country', Countries.'CountryName'
The question can be answered with certainty for each column and condition.
{json_string_2}
Question Solved. 
========== 
[DB_ID] {input_data["db_name"]}
[Schema] 
{input_data["mini_schema"]}
[Question]
{input_data["question"]}
[Evidence]
{input_data["evidence"]}
[Answer]

            """
        # print(sys_prompt,usr_prompt)
        llm_response = self.request_llm(sys_prompt, usr_prompt)
        print(llm_response)
        

        json_object = self.extract_json_from_string(llm_response)
        if json_object == None:
            json_object = {"answerable": "no", "answer": llm_response, "rewrite": ""}
        llm_lower = json_object.get('answerable', 'yes').lower().strip().replace("\n", "")
        if llm_lower.startswith("yes"):
            return "YES"
        else:
            return json_object
