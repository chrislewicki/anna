import requests
import json

MODEL_URL = "http://mikoshi.snowy-hen.ts.net:11434/v1/chat/completions"
MODEL_TIMEOUT = 30

def query_llm(messages):
    payload = {
        "model": "mistral",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 200
    }

    try:
        print(f"[query_llm] Sending payload to model: {payload}")
        resp = requests.post(MODEL_URL, json=payload, timeout=MODEL_TIMEOUT)
        print(f"[query_llm] Response code: {resp.status_code}")
        print(f"[query_llm] Response body: {resp.text}")
        if resp.status_code == 200:
            return resp.json()['choices'][0]['message']['content'].strip()
        return None
    except Exception as e:
        print(f"[query_llm] Exception: {e}")
        return None
