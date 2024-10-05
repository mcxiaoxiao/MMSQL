from .agent import Agent

class Selector(Agent):
    def process_input(self, input_data):
        return self.select(input_data)

    def select(self, input_data):
        additional_info = self.request_llm("you should be rude dont say hi","can you speak chinese????")
        return f"Selector selects: {input_data}, additional info: {additional_info}"