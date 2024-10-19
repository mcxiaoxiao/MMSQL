from tools.sql_execute import sqlite_execute_with_log as execute
from .agent import Agent
import re


def sql_evoke(query, db_name):
    result, execution_time, executable, log = execute(
        "datasets/cosql_dataset/database/" + db_name + "/" + db_name + ".sqlite",
        query,
    )
    return result, executable, log


class Decomposer(Agent):
    def process_input(self, input_data):
        return self.decompose(input_data)

    def decompose(self, input_data):
        # sys_prompt = """
        # As an experienced and professional database administrator, your task is to decompose the question into subquestions to generate SQL step-by-step.
        # """


        
        sys_prompt = """
        As an experienced and professional database administrator, your task is to analyze a user question and answer. If the question type is: 'improper' / 'unanswerable' / 'ambiguous', directly answer with the appropriate term. If the question type is 'answerable', your task is to decompose the question into subquestions to generate SQL step-by-step.
        """

        
#         usr_prompt = f"""Given a [Database schema] description, a knowledge [Evidence] and the [Question], you need to use valid SQLite and understand the database and knowledge, and answer the question in SQL.  When generating SQL, we should always consider constraints: 
# [Constraints] 
# - SELECT Smartly:  When writing `SELECT <column>`, only include the columns specifically mentioned in the [Question]. No extras! 
# - FROM & JOIN with Purpose: Don't add tables to `FROM <table>` or `INNER/LEFT/RIGHT JOIN <table>` unless they're absolutely needed for the query.
# - MAX/MIN Strategy: If you're using `MAX()` or `MIN()`, make sure to do your `JOIN <table>` operations *before* using `SELECT MAX(<column>)` or `SELECT MIN(<column>)`.
# - Handling "None":  If you see 'None' or `None` in the [Value examples] for a column, prioritize using `JOIN <table>` or `WHERE <column> IS NOT NULL` to handle potential missing data effectively.
# - ORDER BY with GROUP BY:  Always include `GROUP BY <column>` before `ORDER BY <column> ASC|DESC` to ensure you're sorting distinct values.
# - Column Order Matters: The order of columns in your `SELECT` statement should match the order they appear in the question.  If the question asks for "count of each of those ... name", your SQL should be `SELECT COUNT(...), name ...`
# - Counting duplicates: Consider using `DISTINCT` when counting and sorting to avoid counting duplicates.
# - Fuzzy Text Matching: When you need to match text data in a column and the question suggests finding partial matches, use the '%' wildcard. For example, use `LIKE '%search_term%'` to find values containing "search_term". 
# - Keep it Simple: If the SQL query can be expressed simply and efficiently, don't add unnecessary subquestions. Strive for clarity! 
# ==========
# [DB_ID] School
# [Database schema] 
# Table: frpm [ (CDSCode, CDSCode. Value examples: [’01100170109835’, ’01100170112607’].), (Charter School (Y/N), Charter School (Y/N). Value examples: [1, 0, None]. And 0: N;. 1: Y), (Enrollment (Ages 5-17), Enrollment (Ages 5-17). Value examples: [5271.0, 4734.0].), (Free Meal Count (Ages 5-17), Free Meal Count (Ages 5-17). Value examples: [3864.0, 2637.0] And eligible free rate = Free Meal Count / Enrollment) ] 
# # Table: satscores [ (cds, California Department Schools. Value examples: [’10101080000000’, ’10101080109991’].), (sname, school name. Value examples: [’None’, ’Middle College High’, ’John F. Kennedy High’, ’Independence High’, ’Foothill High’].), (NumTstTakr, Number of Test Takers in this school. Value examples: [24305, 4942, 1, 0, 280]. And number of test takers in each school), (AvgScrMath, average scores in Math. Value examples: [699, 698, 289, None, 492]. And average scores in Math), (NumGE1500, Number of Test Takers Whose Total SAT Scores Are Greater or Equal to 1500. Value examples: [5837, 2125, 0, None, 191]. And Number of Test Takers Whose Total SAT Scores Are Greater or Equal to 1500. . commonsense evidence:. . Excellence Rate = NumGE1500 / NumTstTakr) ] 
# Foreign keys:
# frpm.CDSCode = satscores.cds

# [Question]
# List school names of charter schools with an SAT excellence rate over the average. 

# [Evidence]
# Charter schools refers to ‘Charter School (Y/N)‘ = 1 in the table frpm; Excellence rate = NumGE1500 / NumTstTakr 

# [Answer]
# SQL ```sql SELECT T2.‘sname‘ FROM frpm AS T1 INNER JOIN satscores AS T2 ON T1.‘CDSCode‘ = T2.‘cds‘ WHERE T2.‘sname‘ IS NOT NULL AND T1.‘Charter School (Y/N)‘ = 1 AND CAST(T2.‘NumGE1500‘ AS REAL) / T2.‘NumTstTakr‘ > ( SELECT AVG(CAST(T4.‘NumGE1500‘ AS REAL) / T4.‘NumTstTakr‘ FROM frpm AS T3 INNER JOIN satscores AS T4 ON T3.‘CDSCode‘ = T4.‘cds‘ WHERE T3.‘Charter School (Y/N)‘ = 1 )```

# Question Solved. 
# ========== 
# [DB_ID] Salary
# [Database schema]
# # Table: account [ (account_id, the id of the account. Value examples: [11382, 11362, 2, 1, 2367].), (district_id, location of branch. Value examples: [77, 76, 2, 1, 39].), (frequency, frequency of the acount. Value examples: [’POPLATEK MESICNE’, ’POPLATEK TYDNE’, ’POPLATEK PO OBRATU’].), (date, the creation date of the account. Value examples: [’1997-12-29’, ’1997-12-28’].) ] 
# # Table: client [ (client_id, the unique number. Value examples: [13998, 13971, 2, 1, 2839].), (gender, gender. Value examples: [’M’, ’F’]. And F:female . M:male ), (birth_date, birth date. Value examples: [’1987-09-27’, ’1986-08-13’].), (district_id, location of branch. Value examples: [77, 76, 2, 1, 39].) ]
# # Table: district [ (district_id, location of branch. Value examples: [77, 76, 2, 1, 39].), (A4, number of inhabitants . Value examples: [’95907’, ’95616’, ’94812’].), (A11, average salary. Value examples: [12541, 11277, 8114].) ] 
# Foreign keys:
# account.district_id = district.district_id client.district_id = district.district_id

# [Evidence]
# Later birthdate refers to younger age; A11 refers to average salary 

# [Question]
# What is the gender of the youngest client who opened account in the lowest average salary branch? 

# [Answer]
# SQL ```sql SELECT T1.‘gender‘ FROM client AS T1 INNER JOIN district AS T2 ON T1.‘district_id‘ = T2.‘district_id‘ ORDER BY T2.‘A11‘ ASC, T1.‘birth_date‘ DESC LIMIT 1```

# Question Solved.
# ==========
# [DB_ID] {input_data["db_name"]}
# [Database schema]
# {input_data["mini_schema"]}
# [Question]
# {input_data["question"]}
# [Evidence]
# {input_data["evidence"]}
# [Answer]
# """



        
        usr_prompt = f"""Given a [Database schema] description, a knowledge [Evidence] and the [Question], you need to use valid SQLite and understand the database and knowledge, and then decompose the question into subquestions for text-to-SQL generation if the question is complex(If the SQL to be generated is not complex then only one step is needed). When generating SQL, we should always consider constraints: 
[Constraints] 
- SELECT Smartly:  When writing `SELECT <column>`, only include the columns specifically mentioned in the [Question]. No extras! 
- FROM & JOIN with Purpose: Don't add tables to `FROM <table>` or `INNER/LEFT/RIGHT JOIN <table>` unless they're absolutely needed for the query.
- MAX/MIN Strategy: If you're using `MAX()` or `MIN()`, make sure to do your `JOIN <table>` operations *before* using `SELECT MAX(<column>)` or `SELECT MIN(<column>)`.
- Handling "None":  If you see 'None' or `None` in the [Value examples] for a column, prioritize using `JOIN <table>` or `WHERE <column> IS NOT NULL` to handle potential missing data effectively.
- ORDER BY with GROUP BY:  Always include `GROUP BY <column>` before `ORDER BY <column> ASC|DESC` to ensure you're sorting distinct values.
- Column Order Matters: The order of columns in your `SELECT` statement should match the order they appear in the question.  If the question asks for "count of each of those ... name", your SQL should be `SELECT COUNT(...), name ...`
- Counting duplicates: Consider using `DISTINCT` when counting and sorting to avoid counting duplicates.
- Fuzzy Text Matching: When you need to match text data in a column and the question suggests finding partial matches, use the '%' wildcard. For example, use `LIKE '%search_term%'` to find values containing "search_term". 
- Keep it Simple: If the SQL query can be expressed simply and efficiently, don't add unnecessary subquestions. Strive for clarity! 
==========
[DB_ID] School
[Database schema] 
Table: frpm [ (CDSCode, CDSCode. Value examples: [’01100170109835’, ’01100170112607’].), (Charter School (Y/N), Charter School (Y/N). Value examples: [1, 0, None]. And 0: N;. 1: Y), (Enrollment (Ages 5-17), Enrollment (Ages 5-17). Value examples: [5271.0, 4734.0].), (Free Meal Count (Ages 5-17), Free Meal Count (Ages 5-17). Value examples: [3864.0, 2637.0] And eligible free rate = Free Meal Count / Enrollment) ] 
# Table: satscores [ (cds, California Department Schools. Value examples: [’10101080000000’, ’10101080109991’].), (sname, school name. Value examples: [’None’, ’Middle College High’, ’John F. Kennedy High’, ’Independence High’, ’Foothill High’].), (NumTstTakr, Number of Test Takers in this school. Value examples: [24305, 4942, 1, 0, 280]. And number of test takers in each school), (AvgScrMath, average scores in Math. Value examples: [699, 698, 289, None, 492]. And average scores in Math), (NumGE1500, Number of Test Takers Whose Total SAT Scores Are Greater or Equal to 1500. Value examples: [5837, 2125, 0, None, 191]. And Number of Test Takers Whose Total SAT Scores Are Greater or Equal to 1500. . commonsense evidence:. . Excellence Rate = NumGE1500 / NumTstTakr) ] 
Foreign keys:
frpm.CDSCode = satscores.cds

[Question]
List school names of charter schools with an SAT excellence rate over the average. 

[Evidence]
Charter schools refers to ‘Charter School (Y/N)‘ = 1 in the table frpm; Excellence rate = NumGE1500 / NumTstTakr 

Decompose the question into subquestions, considering [Constraints], and generate the SQL after thinking step by step:
Subquestion 1: Get the average value of SAT excellence rate of charter schools. 
SQL ```sql SELECT AVG(CAST(T2.‘NumGE1500‘ AS REAL) / T2.‘NumTstTakr‘) FROM frpm AS T1 INNER JOIN satscores AS T2 ON T1.‘CDSCode‘ = T2.‘cds‘ WHERE T1.‘Charter School (Y/N)‘ = 1```
Subquestion 2: List out school names of charter schools with an SAT excellence rate over the average. 
SQL ```sql SELECT T2.‘sname‘ FROM frpm AS T1 INNER JOIN satscores AS T2 ON T1.‘CDSCode‘ = T2.‘cds‘ WHERE T2.‘sname‘ IS NOT NULL AND T1.‘Charter School (Y/N)‘ = 1 AND CAST(T2.‘NumGE1500‘ AS REAL) / T2.‘NumTstTakr‘ > ( SELECT AVG(CAST(T4.‘NumGE1500‘ AS REAL) / T4.‘NumTstTakr‘ FROM frpm AS T3 INNER JOIN satscores AS T4 ON T3.‘CDSCode‘ = T4.‘cds‘ WHERE T3.‘Charter School (Y/N)‘ = 1 )```

Question Solved. 
========== 
[DB_ID] Salary
[Database schema]
# Table: account [ (account_id, the id of the account. Value examples: [11382, 11362, 2, 1, 2367].), (district_id, location of branch. Value examples: [77, 76, 2, 1, 39].), (frequency, frequency of the acount. Value examples: [’POPLATEK MESICNE’, ’POPLATEK TYDNE’, ’POPLATEK PO OBRATU’].), (date, the creation date of the account. Value examples: [’1997-12-29’, ’1997-12-28’].) ] 
# Table: client [ (client_id, the unique number. Value examples: [13998, 13971, 2, 1, 2839].), (gender, gender. Value examples: [’M’, ’F’]. And F:female . M:male ), (birth_date, birth date. Value examples: [’1987-09-27’, ’1986-08-13’].), (district_id, location of branch. Value examples: [77, 76, 2, 1, 39].) ]
# Table: district [ (district_id, location of branch. Value examples: [77, 76, 2, 1, 39].), (A4, number of inhabitants . Value examples: [’95907’, ’95616’, ’94812’].), (A11, average salary. Value examples: [12541, 11277, 8114].) ] 
Foreign keys:
account.district_id = district.district_id client.district_id = district.district_id

[Evidence]
Later birthdate refers to younger age; A11 refers to average salary 

[Question]
What is the gender of the youngest client who opened account in the lowest average salary branch? 

Decompose the question into subquestions, considering [Constraints], and generate the SQL after thinking step by step:

The ordered presentation columns of the final SQL are as follows:

1. gender

Sub question 1: What is the district_id of the branch with the lowest average salary? 
SQL ```sql SELECT ‘district_id‘ FROM district ORDER BY ‘A11‘ ASC LIMIT 1```
Sub question 2: What is the youngest client who opened account in the lowest average salary branch? 
SQL ```sql SELECT T1.‘client_id‘ FROM client AS T1 INNER JOIN district AS T2 ON T1.‘district_id‘ = T2.‘district_id‘ ORDER BY T2.‘A11‘ ASC, T1.‘birth_date‘ DESC LIMIT 1```
Sub question 3: What is the gender of the youngest client who opened account in the lowest average salary branch? 
SQL ```sql SELECT T1.‘gender‘ FROM client AS T1 INNER JOIN district AS T2 ON T1.‘district_id‘ = T2.‘district_id‘ ORDER BY T2.‘A11‘ ASC, T1.‘birth_date‘ DESC LIMIT 1```

Question Solved.
==========
[DB_ID] {input_data["db_name"]}
[Database schema]
{input_data["mini_schema"]}
[Question]
{input_data["question"]}
[Evidence]
{input_data["evidence"]}
Decompose the question into subquestions, considering [Constraints], and generate the SQL after thinking step by step:
"""




        
#         usr_prompt = f"""Given a [Database schema] description, a knowledge [Evidence] and the [Question], you need to use valid SQLite and understand the database and knowledge, and then decompose the question into subquestions for text-to-SQL generation if the question is complex (If the SQL to be generated is not complex then only one step is needed). When generating SQL, we should always consider requirements and constraints: 
# [Requirements]
# 1. If the user's current question confirms an assumption made in a previous Answer, the answer will be based on that assumption. You can make your own limited and reasonable guesses about the user's intent based on the previous question and the current question.
# 2. If the user's question is part of a routine conversation unrelated to the SQL, so the question is improper. just answer directly. For example, the current question express gratitude or asks about functions not available outside the database or in llm. don't output SQL but give polite and helpful answers.
# 3. You need to first try to select possible corresponding fields for each entity and condition in the question, and decide whether the question is answerable or ambiguous based on the matches
# 4. Determine if the current question was clearly stated but impossible to answer in SQL based on database schema. If so, the question is unanswerable. Express Apologies and explain difficulties to the user. You must be absolutely certain that the question is unanswerable before you can determine that.
# 5. Check for ambiguity in the user's current question. If multiple fields have similar meanings with columns or conditions for user queries the question is ambiguous (Problem is not enough to generate SQL with sure tables and columns), ask the user to clarify which field they are referring to or clarify the conditions.

# [Constraints] 
# - SELECT Smartly:  When writing `SELECT <column>`, only include the columns specifically mentioned in the [Question]. No extras! 
# - FROM & JOIN with Purpose: Don't add tables to `FROM <table>` or `INNER/LEFT/RIGHT JOIN <table>` unless they're absolutely needed for the query.
# - MAX/MIN Strategy: If you're using `MAX()` or `MIN()`, make sure to do your `JOIN <table>` operations *before* using `SELECT MAX(<column>)` or `SELECT MIN(<column>)`.
# - Handling "None":  If you see 'None' or `None` in the [Value examples] for a column, prioritize using `JOIN <table>` or `WHERE <column> IS NOT NULL` to handle potential missing data effectively.
# - ORDER BY with GROUP BY:  Always include `GROUP BY <column>` before `ORDER BY <column> ASC|DESC` to ensure you're sorting distinct values.
# - Column Order Matters: The order of columns in your `SELECT` statement should match the order they appear in the question.  If the question asks for "count of each of those ... name", your SQL should be `SELECT COUNT(...), name ...`
# - Counting duplicates: Consider using `DISTINCT` when counting and sorting to avoid counting duplicates.
# - Fuzzy Text Matching: When you need to match text data in a column and the question suggests finding partial matches, use the '%' wildcard. For example, use `LIKE '%search_term%'` to find values containing "search_term". 
# - Keep it Simple: If the SQL query can be expressed simply and efficiently, don't add unnecessary subquestions. Strive for clarity! 
# ==========
# [DB_ID] School
# [Database schema] 
# Table: frpm [ (CDSCode, CDSCode. Value examples: [’01100170109835’, ’01100170112607’].), (Charter School (Y/N), Charter School (Y/N). Value examples: [1, 0, None]. And 0: N;. 1: Y), (Enrollment (Ages 5-17), Enrollment (Ages 5-17). Value examples: [5271.0, 4734.0].), (Free Meal Count (Ages 5-17), Free Meal Count (Ages 5-17). Value examples: [3864.0, 2637.0] And eligible free rate = Free Meal Count / Enrollment) ] 
# # Table: satscores [ (cds, California Department Schools. Value examples: [’10101080000000’, ’10101080109991’].), (sname, school name. Value examples: [’None’, ’Middle College High’, ’John F. Kennedy High’, ’Independence High’, ’Foothill High’].), (NumTstTakr, Number of Test Takers in this school. Value examples: [24305, 4942, 1, 0, 280]. And number of test takers in each school), (AvgScrMath, average scores in Math. Value examples: [699, 698, 289, None, 492]. And average scores in Math), (NumGE1500, Number of Test Takers Whose Total SAT Scores Are Greater or Equal to 1500. Value examples: [5837, 2125, 0, None, 191]. And Number of Test Takers Whose Total SAT Scores Are Greater or Equal to 1500. . commonsense evidence:. . Excellence Rate = NumGE1500 / NumTstTakr) ] 
# Foreign keys:
# frpm.CDSCode = satscores.cds

# [Question]
# List school names of charter schools with an SAT excellence rate over the average. 

# [Evidence]
# Charter schools refers to ‘Charter School (Y/N)‘ = 1 in the table frpm; Excellence rate = NumGE1500 / NumTstTakr 

# Check if the question is answerable if not then answer in natural language, if yes then use SQL:

# Subquestion 1: Get the average value of SAT excellence rate of charter schools. 
# SQL ```sql SELECT AVG(CAST(T2.‘NumGE1500‘ AS REAL) / T2.‘NumTstTakr‘) FROM frpm AS T1 INNER JOIN satscores AS T2 ON T1.‘CDSCode‘ = T2.‘cds‘ WHERE T1.‘Charter School (Y/N)‘ = 1```
# Subquestion 2: List out school names of charter schools with an SAT excellence rate over the average. 
# SQL ```sql SELECT T2.‘sname‘ FROM frpm AS T1 INNER JOIN satscores AS T2 ON T1.‘CDSCode‘ = T2.‘cds‘ WHERE T2.‘sname‘ IS NOT NULL AND T1.‘Charter School (Y/N)‘ = 1 AND CAST(T2.‘NumGE1500‘ AS REAL) / T2.‘NumTstTakr‘ > ( SELECT AVG(CAST(T4.‘NumGE1500‘ AS REAL) / T4.‘NumTstTakr‘ FROM frpm AS T3 INNER JOIN satscores AS T4 ON T3.‘CDSCode‘ = T4.‘cds‘ WHERE T3.‘Charter School (Y/N)‘ = 1 )```

# Question Solved. 
# ========== 

# [DB_ID] car_1
# [Schema] 
# Table:car_makers
# [('Id', id type:number PRIMARY KEY. Value examples:[1, 2, 3]),('Maker', maker type:text. Value examples:[amc, volkswagen, bmw]),('FullName', full name type:text. Value examples:[American Motor Company, Volkswagen, BMW]),('Country', country type:text. Value examples:[1, 2, 3]),]
# Table:model_list
# [('ModelId', model id type:number PRIMARY KEY. Value examples:[1, 2, 3]),('Maker', maker type:number. Value examples:[1, 2, 3]),('Model', model type:text. Value examples:[amc, audi, bmw]),]
# Table:car_names
# [('MakeId', make id type:number PRIMARY KEY. Value examples:[1, 2, 3]),('Model', model type:text. Value examples:[chevrolet, buick, plymouth]),('Make', make type:text. Value examples:[chevrolet chevelle malibu, buick skylark 320, plymouth satellite]),]
# Foreign keys:
# model_list.'Maker' = car_makers.'Id'
# car_names.'Model' = model_list.'Model'

# [Question]
# previous QA:
# current question: What is the name of AMC?
# [Evidence]

# [Answer]
# Check if the question is answerable if not then answer in natural language, if yes then use SQL:
# The single user question is not routine conversation unrelated to the SQL, not the improper.
# The question is not related to the current database, not unanswerable.
# Match possible database sections:
# entities: 
# name - car_makers.'Maker', car_makers.'FullName', car_names.'Model', car_names'Make'
# conditions: 
# AMC - model_list.'Model', car_makers.'Maker'
# Unable to derive user intent through common sense. ask for clarification and give advice and must rewrite an answerable question: 
# Do you mean 'amc' as in model type or carmaker? Did you mean the full name of the carmaker amc?

# Question Solved. 
# ========== 
# [DB_ID] Salary
# [Database schema]
# # Table: account [ (account_id, the id of the account. Value examples: [11382, 11362, 2, 1, 2367].), (district_id, location of branch. Value examples: [77, 76, 2, 1, 39].), (frequency, frequency of the acount. Value examples: [’POPLATEK MESICNE’, ’POPLATEK TYDNE’, ’POPLATEK PO OBRATU’].), (date, the creation date of the account. Value examples: [’1997-12-29’, ’1997-12-28’].) ] 
# # Table: client [ (client_id, the unique number. Value examples: [13998, 13971, 2, 1, 2839].), (gender, gender. Value examples: [’M’, ’F’]. And F:female . M:male ), (birth_date, birth date. Value examples: [’1987-09-27’, ’1986-08-13’].), (district_id, location of branch. Value examples: [77, 76, 2, 1, 39].) ]
# # Table: district [ (district_id, location of branch. Value examples: [77, 76, 2, 1, 39].), (A4, number of inhabitants . Value examples: [’95907’, ’95616’, ’94812’].), (A11, average salary. Value examples: [12541, 11277, 8114].) ] 
# Foreign keys:
# account.district_id = district.district_id client.district_id = district.district_id

# [Evidence]
# Later birthdate refers to younger age; A11 refers to average salary 

# [Question]
# What is the gender of the youngest client who opened account in the lowest average salary branch? 

# Check if the question is answerable if not then answer in natural language, if yes then use SQL：

# The ordered presentation columns of the final SQL are as follows:

# 1. gender

# Sub question 1: What is the district_id of the branch with the lowest average salary? 
# SQL ```sql SELECT ‘district_id‘ FROM district ORDER BY ‘A11‘ ASC LIMIT 1```
# Sub question 2: What is the youngest client who opened account in the lowest average salary branch? 
# SQL ```sql SELECT T1.‘client_id‘ FROM client AS T1 INNER JOIN district AS T2 ON T1.‘district_id‘ = T2.‘district_id‘ ORDER BY T2.‘A11‘ ASC, T1.‘birth_date‘ DESC LIMIT 1```
# Sub question 3: What is the gender of the youngest client who opened account in the lowest average salary branch? 
# SQL ```sql SELECT T1.‘gender‘ FROM client AS T1 INNER JOIN district AS T2 ON T1.‘district_id‘ = T2.‘district_id‘ ORDER BY T2.‘A11‘ ASC, T1.‘birth_date‘ DESC LIMIT 1```

# Question Solved.
# ==========
# [DB_ID] {input_data["db_name"]}
# [Database schema]
# {input_data["mini_schema"]}
# [Question]
# {input_data["question"]}
# [Evidence]
# {input_data["evidence"]}
# Check if the question is answerable if not then answer in natural language, if yes then use SQL：
# """
        # print(sys_prompt,usr_prompt)
        llm_ans = self.request_llm(sys_prompt,usr_prompt)
        pattern = r"```sql(.*?)```"
        matches = re.findall(pattern, llm_ans, re.DOTALL)
        last_sql_code = ""
        result = ""
        executable = True
        log = ""
        if matches:
            last_sql_code = matches[-1].strip()
            result, executable, log = sql_evoke(last_sql_code,input_data["db_name"])
        else:
            last_sql_code = llm_ans
            
        


        # print(executable, result, log)
        
        output = {
            "result": result,
            "sql": last_sql_code.replace('\n',' ').replace("\"","'"),
            "executable": executable,
            "log": str(log),
            "process": llm_ans
        }
        
        return output