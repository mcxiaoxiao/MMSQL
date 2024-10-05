from .agent import Agent

class Decomposer(Agent):
    def process_input(self, input_data):
        return self.decompose(input_data)

    def decompose(self, input_data):
        additional_info = self.request_llm("回答后需要加两个感叹号",input_data)
        return f"Decomposer decomposes: {input_data}, additional info: {additional_info}"