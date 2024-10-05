from tools.api_request import request_gemini as request_llm

class Agent:
    def __init__(self, name):
        self.name = name

    def process_input(self, input_data):
        raise NotImplementedError("Each agent must implement the process_input method.")

    def request_llm(self, system_instruct, user_question):
        messages = [{"role": "system", "content": system_instruct},{"role": "user", "content": user_question}]
        print(messages)
        response = request_llm(messages)
        print(f"LLM response to {self.name}: "+ response)
        return response