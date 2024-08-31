from openai import OpenAI
import requests
import time
import google.generativeai as genai
# Set API key
OPENAI_API_KEY = 'sk-proj-1JRQ9SkU0gSRKsBoCyD1T3BlbkFJSQ44FoEjAHN05t7FrryD'
OPENAI_MODEL_NAME = "gpt-4-1106-preview"
client = OpenAI(api_key=OPENAI_API_KEY)

GEMINI_API_KEY = 'AIzaSyAUJEkCFcasjISnFQLqu5kyXFZWLppKIaU'
GEMINI_MODEL_NAME = "gemini-1.5-flash"
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
                print(f"An error occurred with GPT request after 5 attempts: {e}")
                return "failed"

def request_gemini(messages):   
    print("request "+ GEMINI_MODEL_NAME)
    url = "https://generativelanguage.googleapis.com/v1beta/models/"+GEMINI_MODEL_NAME+":generateContent?key="+ GEMINI_API_KEY
    messages = [
        {"role": "user", "parts":[{"text": "who are you"}]},
        {"role": "model", "parts":[{"text": "i am gzm"}]},
        {"role": "user", "parts":[{"text": "repeat!"}]}
    ]
    
    headers = {
        "Content-Type": "application/json"
    }
    
    data = {
        "contents": messages
    }
    
    max_retries = 5
    retry_count = 0
    response = None
    
    while retry_count < max_retries:
        response = requests.post(url, headers=headers, json=data,timeout = 30)
    
        if response.status_code == 200:
            break
        else:
            print("Failed to make request, retrying...")
            retry_count += 1
            time.sleep(10)  # 暂停一秒再重试，以防止过于频繁的请求
    
    if response is not None and response.status_code == 200:
        response_json = response.json()
        print("Received response from Gemini.")
        # generated_text = response_json['candidates'][0]['content']['parts'][0]['text']
        # 安全地访问嵌套的字典和列表
        generated_text = response_json.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
        return generated_text
    else:
        print("Error: Failed after {} retries".format(max_retries))
        return "failed"