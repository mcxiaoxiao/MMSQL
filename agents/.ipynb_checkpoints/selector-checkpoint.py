from .agent import Agent
import json

class Selector(Agent):
    def process_input(self, input_data):
        return self.select(input_data)

    
    
    def select(self, input_data):
        sys_prompt = """
        As an experienced and professional database administrator, your task is to analyze a user question and a database schema to provide relevant information. The database schema consists of table descriptions table examples, each containing multiple column descriptions. Your goal is to identify any possible tables and columns based on the user question and evidence provided.
        """
        usr_prompt = f"""[Instruction] 1. Discard any table schema unrelated to the user question and evidence. 2. Sort the columns in each relevant table in descending order of relevance and keep the top 6 columns. 3. Ensure that at least 3 tables are included in the final output JSON. 4. The output should be in JSON format.
[Requirements] 1. If a table has less than or equal to 3 columns, mark it as "keep_all". 2. If a table is completely irrelevant to the user question and evidence, mark it as "drop_all". 3. Prioritize the columns in each relevant table based on their relevance.
Here is a typical example:
[DB_ID] car_1
[Schema] 
continents(ContId:cont id type:number PRIMARY KEY|Continent:continent type:text|)
countries(CountryId:country id type:number PRIMARY KEY|CountryName:country name type:text|Continent:continent type:number|)
car_makers(Id:id type:number PRIMARY KEY|Maker:maker type:text|FullName:full name type:text|Country:country type:text|)
model_list(ModelId:model id type:number PRIMARY KEY|Maker:maker type:number|Model:model type:text|)
car_names(MakeId:make id type:number PRIMARY KEY|Model:model type:text|Make:make type:text|)
cars_data(Id:id type:number PRIMARY KEY|MPG:mpg type:text|Cylinders:cylinders type:number|Edispl:edispl type:number|Horsepower:horsepower type:text|Weight:weight type:number|Accelerate:accelerate type:number|Year:year type:number|)
continents:
(1,america)
(2,europe)
(3,asia)
countries:
(1,usa,1)
(2,germany,2)
(3,france,2)
car_makers:
(1,amc,American Motor Company,1)
(2,volkswagen,Volkswagen,2)
(3,bmw,BMW,2)
model_list:
(1,1,amc)
(2,2,audi)
(3,3,bmw)
car_names:
(1,chevrolet,chevrolet chevelle malibu)
(2,buick,buick skylark 320)
(3,plymouth,plymouth satellite)
cars_data:
(1,18,8,307.0,130,3504,12.0,1970)
(2,15,8,350.0,165,3693,11.5,1970)
(3,18,8,318.0,150,3436,11.0,1970)
[Question]
Which companies have three or more models? list the count and the maker's full name.
[Evidence]
["'Continent' refers to the continent's Id in table countries, refers to the name of continent in table continents"]
[Answer]
The entities extracted from the Question are:
count
maker's full name
companies
three or more models
Therefore we can select the related database schema based on these entities with Evidence
{str({"continents": "drop_all", "countries": "drop_all", "car_makers": ["Id", "FullName"], "model_list": "keep_all",  "cars_data": "drop_all"})}
Question Solved. 
========== 
Here is a new example, please start answering:
[DB_ID] {input_data["db_name"]}
[Schema] 
{input_data["db_desc"]}
{input_data["db_exam"]}
[Question]
{input_data["question"]}
[Answer]
        """
        
        llm_ans = self.request_llm(sys_prompt,usr_prompt)
        
        json_object = self.extract_json_from_string(llm_ans)
        
        if json_object:
            # print(json_object)
            minischema = self.schema_select(input_data["db_name"],json_object)
            if minischema == "":
                minischema = "None"
        else:
          print("No valid JSON object found.")
            
        return f"{str(minischema)}"