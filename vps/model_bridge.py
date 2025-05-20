import requests
import json
import os


# This is a private endpoint, don't even try
MODEL_URL = "https://ppjmbaf3sh6p5tx2iaz53gmr.agents.do-ai.run/api/v1/chat/completions"
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
MODEL_TIMEOUT = 20


def send_payload(payload):
    try:
        print(f"[send_payload] Sending payload to model: {payload}")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AUTH_TOKEN}"
        }
        resp = requests.post(MODEL_URL, headers=headers, json=payload, timeout=MODEL_TIMEOUT)
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
        return resp.json()['choices'][0]['message']['content'].strip()
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
