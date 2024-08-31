from openai import OpenAI
import requests
import time
import google.generativeai as genai
# Set API key
OPENAI_API_KEY = 'sk-proj-1JRQ9SkU0gSRKsBoCyD1T3BlbkFJSQ44FoEjAHN05t7FrryD'
OPENAI_MODEL_NAME = "gpt-4-1106-preview"
client = OpenAI(api_key=OPENAI_API_KEY)

GEMINI_API_KEY = 'AIzaSyCxpeaNafORNa4mddSV-da0tD1XLGeTHkw'
GEMINI_MODEL_NAME = "gemini-1.5-pro"
ge_model = genai.GenerativeModel(GEMINI_MODEL_NAME)

def request_gpt(messages):
    print("request "+ OPENAI_MODEL_NAME)
    for attempt in range(5):  # Retry up to 5 times
        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL_NAME,
                messages=messages,
                temperature=0
            )
            response_message = response.choices[0].message.content
            return response_message
        except Exception as e:
            print(e)
            if attempt < 4:  # Don't wait after the last attempt
                time.sleep(10)  # Wait for 10 seconds before retrying
            else:
                return f"An error occurred with GPT request after 5 attempts: {e}"

def request_gemini(messages):
    genai.configure(api_key=GEMINI_API_KEY)
    print("request "+ GEMINI_MODEL_NAME)
    chat = ge_model.start_chat(
    history=[
        {"role": "user", "parts": "Hello"},
        {"role": "model", "parts": "Great to meet you. What would you like to know?"},
    ]
    )
    response = chat.send_message("I have 2 dogs in my house.")
    print(response.text)
