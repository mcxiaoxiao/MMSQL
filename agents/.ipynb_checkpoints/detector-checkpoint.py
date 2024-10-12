from .agent import Agent

class Detector(Agent):
    def process_input(self, input_data):
        return self.detect(input_data)

    def detect(self, input_data):
        sys_prompt = """
        As an experienced and professional database administrator, your task is to analyze a user question. If the question is improper, unanswerable, or ambiguous, directly answer with the appropriate term. If the question is answerable, directly respond with "Yes".
        """
        if input_data["mini_schema"] == "None":
            usr_prompt = f"""告诉用户问题不可被回答并根据数据库schema给出修改问题的建议（你可以这样问...）
[DB_ID] {input_data["db_desc"]}
[Schema] 
{input_data["mini_schema"]}
[Question]
{input_data["question"]}
[Evidence]
{input_data["evidence"]}
"""
        else:
            usr_prompt = f"""
[Requirements]
1. If the user's question is part of a routine conversation unrelated to the SQL, just answer directly. For example, the current question express gratitude or ask about functions not available outside the database or in llm. don't output "Yes" but give polite and helpful answers.
2. Determine if the current question can be answered accurately based on the provided database schema. If not, explain why to the user.
3. Check for ambiguity in the user's current question. If multiple fields have similar meanings with columns or conditions for user queries, ask the user to clarify which field they are referring to. You can make some reasonable guesses.
4. Output "Yes" if the question can be answered with certainty for each column output.

[DB_ID] {input_data["db_name"]}
[Schema] 
{input_data["mini_schema"]}
[Question]
{input_data["question"]}
[Evidence]
{input_data["evidence"]}
            """
        # print(sys_prompt,usr_prompt)
        llm_response = self.request_llm(sys_prompt,usr_prompt)
        llm_lower = llm_response.lower()
        llm_lower = llm_lower.strip()
        llm_lower = llm_lower.replace("\n", "")
        # print("llm_lower" + llm_lower)
        if llm_lower == "yes" or llm_lower == "yes.":
            return f"YES"
        else:
            return f"{llm_response}"