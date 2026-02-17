"""LLM provider abstraction for multi-provider support."""

from abc import ABC, abstractmethod
from typing import Optional
import requests
import logging
import config

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def send_request(self, payload: dict) -> Optional[requests.Response]:
        """
        Send request to LLM provider.

        Args:
            payload: The request payload (OpenAI-compatible format)

        Returns:
            Response object or None if request failed
        """
        pass


class DigitalOceanProvider(LLMProvider):
    """DigitalOcean GenAI Platform provider."""

    def __init__(self):
        """Initialize DigitalOcean provider."""
        self.url = config.DIGITALOCEAN_MODEL_URL
        self.auth_token = config.DIGITALOCEAN_AUTH_TOKEN
        self.model = config.DIGITALOCEAN_MODEL
        self.timeout = config.LLM_TIMEOUT_SECONDS

        if not self.auth_token:
            logger.warning("DIGITALOCEAN_AUTH_TOKEN not set, requests will likely fail")

    def send_request(self, payload: dict) -> Optional[requests.Response]:
        """Send request to DigitalOcean GenAI Platform."""
        try:
            # Ensure model is set in payload
            payload['model'] = self.model

            headers = {
                'Authorization': f'Bearer {self.auth_token}',
                'Content-Type': 'application/json',
            }

            logger.debug(f"Sending request to DigitalOcean: {self.url}")
            response = requests.post(
                self.url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )

            response.raise_for_status()
            return response

        except requests.exceptions.Timeout:
            logger.error(f"DigitalOcean request timed out after {self.timeout}s")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"DigitalOcean request failed: {e}")
            return None


class OllamaLocalProvider(LLMProvider):
    """Local ollama provider (requires host network mode in Docker)."""

    def __init__(self):
        """Initialize local ollama provider."""
        self.url = f"{config.OLLAMA_LOCAL_URL}/v1/chat/completions"
        self.model = config.OLLAMA_LOCAL_MODEL
        self.timeout = config.LLM_TIMEOUT_SECONDS

    def send_request(self, payload: dict) -> Optional[requests.Response]:
        """Send request to local ollama instance."""
        try:
            # Ensure model is set in payload
            payload['model'] = self.model

            headers = {
                'Content-Type': 'application/json',
            }

            logger.debug(f"Sending request to local ollama: {self.url}")
            response = requests.post(
                self.url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )

            response.raise_for_status()
            return response

        except requests.exceptions.ConnectionError:
            logger.error(
                f"Cannot connect to local ollama at {self.url}. "
                "Ensure ollama is running and docker-compose.yml has 'network_mode: host'"
            )
            return None
        except requests.exceptions.Timeout:
            logger.error(f"Local ollama request timed out after {self.timeout}s")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Local ollama request failed: {e}")
            return None


class OllamaTailscaleProvider(LLMProvider):
    """Ollama via Tailscale provider."""

    def __init__(self):
        """Initialize Tailscale ollama provider."""
        self.base_url = config.OLLAMA_TAILSCALE_URL
        self.url = f"{self.base_url}/v1/chat/completions"
        self.model = config.OLLAMA_TAILSCALE_MODEL
        self.timeout = config.LLM_TIMEOUT_SECONDS

        if not self.base_url:
            logger.warning(
                "OLLAMA_TAILSCALE_URL not set, requests will fail. "
                "Example: http://hostname.tail-scale.ts.net:11434"
            )

    def send_request(self, payload: dict) -> Optional[requests.Response]:
        """Send request to ollama via Tailscale."""
        try:
            # Ensure model is set in payload
            payload['model'] = self.model

            headers = {
                'Content-Type': 'application/json',
            }

            logger.debug(f"Sending request to Tailscale ollama: {self.url}")
            response = requests.post(
                self.url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )

            response.raise_for_status()
            return response

        except requests.exceptions.ConnectionError:
            logger.error(
                f"Cannot connect to Tailscale ollama at {self.url}. "
                "Check OLLAMA_TAILSCALE_URL and network connectivity"
            )
            return None
        except requests.exceptions.Timeout:
            logger.error(f"Tailscale ollama request timed out after {self.timeout}s")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Tailscale ollama request failed: {e}")
            return None


def get_provider() -> LLMProvider:
    """
    Get LLM provider based on LLM_PROVIDER environment variable.

    Returns:
        LLMProvider instance (defaults to DigitalOceanProvider)
    """
    provider_name = config.LLM_PROVIDER.lower()

    if provider_name == "ollama-local":
        logger.info("Using LLM provider: ollama-local")
        return OllamaLocalProvider()
    elif provider_name == "ollama-tailscale":
        logger.info("Using LLM provider: ollama-tailscale")
        return OllamaTailscaleProvider()
    else:
        # Default to DigitalOcean
        if provider_name != "digitalocean":
            logger.warning(
                f"Unknown LLM_PROVIDER '{provider_name}', defaulting to digitalocean"
            )
        logger.info("Using LLM provider: digitalocean")
        return DigitalOceanProvider()
