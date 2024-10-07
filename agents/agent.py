from tools.api_request import request_gemini as request_llm
from tools.schema_select import schema_select
import json

class Agent:
    def __init__(self, name):
        self.name = name

    def process_input(self, input_data):
        raise NotImplementedError("Each agent must implement the process_input method.")

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
          start = text.find('{')
          end = text.find('}', start)
          if start != -1 and end != -1:
            try:
              return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
              return None
          return None
        