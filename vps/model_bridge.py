import requests
import json

MODEL_URL = "http://mikoshi.snowy-hen.ts.net:11434/v1/chat/completions"
MODEL_TIMEOUT = 30

def send_payload(payload):
    try:
        print(f"[send_payload] Sending payload to model: {payload}")
        resp = requests.post(MODEL_URL, json=payload, timeout=MODEL_TIMEOUT)
        print(f"[send_payload] Response code: {resp.status_code}")
        print(f"[send_payload] Response body: {resp.text}")
        if resp.status_code == 200:
            return resp
        return None
    except Exception as e:
        print(f"[send_payload] Exception: {e}")
        return None

def query_llm(messages):
    resp = send_payload( {
        "model": "mistral",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 8124
    })
    if resp is not None:
        return resp.json()['choices'][0]['message']['content'].strip(), resp.json()['choices'][0]['message']['context']
    return None

def query_llm_with_context(messages, context):
    resp = send_payload({
        "model": "mistral",
        "messages": messages,
        "context": context,
        "temperature": 0.7,
        "max_tokens": 8124
    })
    if resp is not None:
        return resp.json()['choices'][0]['message']['content'].strip(), resp.json()['choices'][0]['message']['context']
    return None, None