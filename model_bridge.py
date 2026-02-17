import requests
import json
import logging
from config import LLM_TEMPERATURE, LLM_MAX_TOKENS
from llm_providers import get_provider

logger = logging.getLogger(__name__)


def send_payload(payload):
    """
    Send a payload to the configured LLM provider.

    Args:
        payload: Dictionary containing messages and other parameters

    Returns:
        Response object if successful, None otherwise
    """
    logger.debug(f"Sending payload to model with {len(payload.get('messages', []))} messages")

    # Get configured provider and send request
    provider = get_provider()
    return provider.send_request(payload)


def query_llm(messages):
    """
    Query the LLM with a list of messages.

    Args:
        messages: List of message dictionaries with 'role' and 'content' keys

    Returns:
        String response from LLM, or None if request failed or response malformed
    """
    resp = send_payload({
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
