from tools.api_request import request_gemini as request_llm
# from tools.api_request import request_gpt as request_llm
# from tools.api_request import request_nvidia as request_llm
from tools.schema_select import schema_select
import json

class Agent:
    def __init__(self, name):
        self.name = name

    def process_input(self, input_data):
        llm_response = self.request_llm(input_data['sys_prompt'],input_data['usr_prompt'])
        return llm_response

    # Agent Tools
    
    def request_llm(self, system_instruct, user_question):
        messages = [{"role": "system", "content": system_instruct},{"role": "user", "content": user_question}]
        # print(messages)
        response = request_llm(messages)
        # print(f"LLM response to {self.name}: "+ response)
        return response

    
    def schema_select(self, dbname, table_config):
        return schema_select(dbname, table_config)

    
    def extract_json_from_string(self, text):
        # print( text)
        # print("count")
        open_count = text.count('{')
        close_count = text.count('}')

        if open_count > close_count:
            text += '}' * (open_count - close_count)
            # print(text)
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            try:
              print(text[start:end + 1])
                 
              return json.loads(json.dumps(eval(text[start:end + 1])))
            except json.JSONDecodeError  as e:
              print(f"JSON ERROR {e}")
              return None
        return None
        