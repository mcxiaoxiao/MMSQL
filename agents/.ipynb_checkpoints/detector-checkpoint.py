from .agent import Agent

class Detector(Agent):
    def process_input(self, input_data):
        return self.detect(input_data)

    def detect(self, input_data):
        sys_prompt = """
        As an experienced and professional database administrator, your task is to analyze a user question 的类型 如果是improper/unanswerable/ambiguous则直接回答如果是answerable则直接回答Yes.
        """
        if input_data["mini_schema"] == "None":
            usr_prompt = f"""告诉用户问题不可被回答并根据数据库schema给出修改问题的建议（你可以这样问...）
[DB_ID] {input_data["db_desc"]}
[Schema] 
{input_data["mini_schema"]}

[Question]

{input_data["question"]}
"""
        else:
            usr_prompt = f"""
根据数据库schema和问题判断问题是否能被准确的回答，如果不能则告知用户为什么不能，需要用户澄清些什么，如果可以回答的话则输出Yes即可
[DB_ID] {input_data["db_name"]}
[Schema] 
{input_data["mini_schema"]}
[Question]
{input_data["question"]}
            """
            
        llm_response = self.request_llm(sys_prompt,usr_prompt)
        if llm_response.lower() == "yes":
            llm_response = "YES"
        return f"{llm_response}"