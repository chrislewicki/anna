import requests
import json

MODEL_URL = "http://your-laptop-ip:11434/v1/chat/completions"
MODEL_TIMEOUT = 5

def query_llm(messages):
    payload = {
        "model": "mistral",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 200
    }

    try:
        resp = requests.post(MODEL_URL, json=payload, timeout=MODEL_TIMEOUT)
        if resp.status_code == 200:
            return resp.json()['choices'][0]['message']['content'].strip()
        return None
    except Exception:
        return None
