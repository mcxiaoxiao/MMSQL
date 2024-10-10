from tools.sql_execute import sqlite_execute_with_log as execute
from .agent import Agent
import re


def sql_evoke(query, db_name):
    result, execution_time, executable, log = execute(
        "datasets/cosql_dataset/database/" + db_name + "/" + db_name + ".sqlite",
        query,
    )
    return result, executable, log


class Refiner(Agent):
    def process_input(self, input_data):
        return self.refine(input_data)

    def refine(self, input_data):
        sys_prompt = """
        As an experienced and professional database administrator, your task is to fix erroneous SQL based on the Query and SQLite database info.
        """

        usr_prompt = f"""[Instruction] When executing SQL below, some errors occurred, please fix up SQL based on query and database info. Solve the task step by step if you need to. Using SQL format in the code block, and indicate script type in the code block. When you find an answer, verify the answer carefully. Include verifiable evidence in your response if possible. Only SQL statements are allowed in (the fixed SQL), do not add any comments.
[Constraints] 
- In ‘SELECT <column>‘, just select needed columns in the [Question] without any unnecessary column or value 
- In ‘FROM <table>‘ or ‘JOIN <table>‘, do not include unnecessary table 
- If use max or min func, ‘JOIN <table>‘ FIRST, THEN use ‘SELECT MAX(<column>)‘ or ‘SELECT MIN(<column>)‘ 
- If [Value examples] of <column> has ’None’ or None, use ‘JOIN <table>‘ or ‘WHERE <column> is NOT NULL‘ is better 
- If use ‘ORDER BY <column> ASC|DESC‘, add ‘GROUP BY <column>‘ before to select distinct values 
[Response format] 
Your response should be in this format: Analysis: **(Your analysis)** Correct SQL: ```sql (the fixed SQL) ```
[Query] {input_data["question"]}
[Evidence] {input_data["evidence"]}
[Database info] {input_data["mini_schema"]}
[old SQL] ”’ sql {input_data["old_sql"]} ”’ 
[SQLite error] {input_data["log"]}
Now please fixup old SQL and generate new SQL again.
"""
        
        llm_ans = self.request_llm(sys_prompt,usr_prompt)
        pattern = r"```sql(.*?)```"
        matches = re.findall(pattern, llm_ans, re.DOTALL)
        
        if matches:
            last_sql_code = matches[-1].strip()
 
        
        result, executable, log = sql_evoke(last_sql_code,input_data["db_name"])

        # print(executable, result, log)
        
        output = {
            "result": result,
            "sql": last_sql_code.replace('\n',' ').replace("\"","'"),
            "executable": executable,
            "log": str(log)
        }
        
        return output
        # print(usr_prompt)
        llm_ans = self.request_llm(sys_prompt,usr_prompt)
        return llm_ans