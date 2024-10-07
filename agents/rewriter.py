from .agent import Agent
import json

class Rewriter(Agent):
    def process_input(self, input_data):
        return self.select(input_data)

    
    
    def select(self, input_data):
        sys_prompt = """
        
        """
        usr_prompt = f"""[Instruction] 你需要根据evidence和previous QA及current question提炼出当前的完整问题如果与数据库有关则输出The output should be in JSON format.以及当前问题是否与先前问题相关
[Requirements] 你需要把全部问题整合成一个确定的问题，你需要先判断这个是否可能可以通过查询数据库实现如果可能则improper为no如果可以则整理成一个问题如果不可以则不用整合直接回答则improper为yes。json字段分为improper:""(YES/NO)rewritten:""(rewritten question)
[Previous QA]
Do you know the name of the man with ID 1?
ok, how about id 2?
[Current question]
i wanna know his email
[Rewritten question]
I want to see the email of the man with ID 2.
[Answer]
{str({"improper":"NO","rewritten":"I want to know the email of the man with ID 2."})}
Task Solved. 
==========
Here is a new example, please start answering:
[Evidence]
{input_data["evidence"]}
[Previous QA]
{input_data["previous_QA"]}
[Current question]
{input_data["question"]}
[Answer]
        """
        
        llm_ans = self.request_llm(sys_prompt,usr_prompt)

        print("llm_ans")
        print(llm_ans)
        
        json_object = self.extract_json_from_string(llm_ans)

        rewritten_output_json = ""

        print("json_object")
        print(json_object)
        
        if json_object:
            # print(json_object)
            rewritten_output_json = json_object
        else:
            print("No valid JSON object found.")
            
        return f"{str(rewritten_output_json)}"