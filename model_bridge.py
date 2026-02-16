import requests
import json
import os
import logging
from config import LLM_TIMEOUT_SECONDS, LLM_TEMPERATURE, LLM_MAX_TOKENS

logger = logging.getLogger(__name__)

# This is a private endpoint, don't even try
MODEL_URL = "https://ppjmbaf3sh6p5tx2iaz53gmr.agents.do-ai.run/api/v1/chat/completions"
AUTH_TOKEN = os.getenv("AUTH_TOKEN")


def send_payload(payload):
    """
    Send a payload to the LLM API.

    Args:
        payload: Dictionary containing model, messages, and other parameters

    Returns:
        Response object if successful, None otherwise
    """
    try:
        logger.debug(f"Sending payload to model with {len(payload.get('messages', []))} messages")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AUTH_TOKEN}"
        }
        resp = requests.post(MODEL_URL, headers=headers, json=payload, timeout=LLM_TIMEOUT_SECONDS)
        logger.debug(f"Response code: {resp.status_code}")

        if resp.status_code == 200:
            logger.info("Successfully received response from LLM")
            return resp
        else:
            logger.warning(f"LLM returned non-200 status: {resp.status_code}")
            logger.debug(f"Response body: {resp.text}")
            return None
    except requests.exceptions.Timeout:
        logger.error(f"LLM request timed out after {LLM_TIMEOUT_SECONDS}s")
        return None
    except Exception as e:
        logger.error(f"LLM request failed: {e}", exc_info=True)
        return None


def query_llm(messages):
    """
    Query the LLM with a list of messages.

    Args:
        messages: List of message dictionaries with 'role' and 'content' keys

    Returns:
        String response from LLM, or None if request failed or response malformed
    """
    resp = send_payload({
        "model": "mistral",
        "messages": messages,
        "temperature": LLM_TEMPERATURE,
        "max_tokens": LLM_MAX_TOKENS
    })

    if resp is None:
        return None

    try:
        data = resp.json()

        # Validate response structure
        if 'choices' not in data:
            logger.error(f"Missing 'choices' in LLM response: {data}")
            return None

        if not data['choices'] or len(data['choices']) == 0:
            logger.error("Empty 'choices' array in LLM response")
            return None

        choice = data['choices'][0]
        if 'message' not in choice or 'content' not in choice['message']:
            logger.error(f"Malformed choice structure: {choice}")
            return None

        content = choice['message']['content'].strip()

        if not content:
            logger.warning("LLM returned empty content")
            return None

        return content

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing LLM response: {e}", exc_info=True)
        return None


def query_llm_with_context(messages, context):
    """
    Query the LLM with messages and conversation context.

    Args:
        messages: List of message dictionaries with 'role' and 'content' keys
        context: Previous conversation context to maintain state

    Returns:
        Tuple of (content string, context dict), or (None, None) if request failed
    """
    resp = send_payload({
        "model": "mistral",
        "messages": messages,
        "context": context,
        "temperature": LLM_TEMPERATURE,
        "max_tokens": LLM_MAX_TOKENS
    })

    if resp is None:
        return None, None

    try:
        data = resp.json()

        # Validate response structure
        if 'choices' not in data:
            logger.error(f"Missing 'choices' in LLM response: {data}")
            return None, None

        if not data['choices'] or len(data['choices']) == 0:
            logger.error("Empty 'choices' array in LLM response")
            return None, None

        choice = data['choices'][0]
        if 'message' not in choice:
            logger.error(f"Malformed choice structure: {choice}")
            return None, None

        message = choice['message']
        if 'content' not in message:
            logger.error(f"Missing 'content' in message: {message}")
            return None, None

        content = message['content'].strip()
        new_context = message.get('context', None)

        if not content:
            logger.warning("LLM returned empty content")
            return None, None

        return content, new_context

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response: {e}")
        return None, None
    except Exception as e:
        logger.error(f"Unexpected error parsing LLM response: {e}", exc_info=True)
        return None, None
