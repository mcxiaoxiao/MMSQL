from .agent import Agent

class Detector(Agent):
    def process_input(self, input_data):
        return self.detect(input_data)

    def detect(self, input_data):
        additional_info = self.request_llm("回答后需要加两个感叹号",input_data)
        return f"Detector detects: {input_data}, additional info: {additional_info}"