from .agent import Agent

class Refiner(Agent):
    def process_input(self, input_data):
        return self.refine(input_data)

    def refine(self, input_data):
        additional_info = self.request_llm("回答后需要加两个感叹号",input_data)
        return f"Refiner refines: {input_data}, additional info: {additional_info}"