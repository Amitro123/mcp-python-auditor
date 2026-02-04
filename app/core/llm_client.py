"""LLM Client for AI-powered audit analysis.

Supports Groq (cloud) and Ollama (local) backends.
"""

import os
from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: The prompt to send to the LLM

        Returns:
            Generated response text
        """


class GroqClient(LLMClient):
    """Groq API client for fast LLM inference."""

    def __init__(self, api_key: str | None = None, model: str = "llama-3.3-70b-versatile"):
        """Initialize Groq client.

        Args:
            api_key: Groq API key. If None, reads from GROQ_API_KEY env var
            model: Model to use for generation
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model
        self._client = None

    def _get_client(self):
        """Lazy-load Groq client."""
        if self._client is None:
            import groq

            if not self.api_key:
                raise ValueError("Groq API key not provided")
            self._client = groq.Groq(api_key=self.api_key)
        return self._client

    def generate(self, prompt: str) -> str:
        """Generate a response using Groq API.

        Args:
            prompt: The prompt to send

        Returns:
            Generated response text
        """
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content


class OllamaClient(LLMClient):
    """Ollama local LLM client."""

    def __init__(self, model: str = "llama3.2", base_url: str = "http://localhost:11434"):
        """Initialize Ollama client.

        Args:
            model: Model to use for generation
            base_url: Ollama server URL
        """
        self.model = model
        self.base_url = base_url

    def generate(self, prompt: str) -> str:
        """Generate a response using Ollama API.

        Args:
            prompt: The prompt to send

        Returns:
            Generated response text
        """
        import requests

        response = requests.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["response"]


def get_llm_client(provider: str = "groq", **kwargs) -> LLMClient:
    """Factory function to create LLM client.

    Args:
        provider: Either "groq" or "ollama"
        **kwargs: Additional arguments for the client

    Returns:
        LLM client instance
    """
    if provider.lower() in ("groq", "1"):
        return GroqClient(**kwargs)
    if provider.lower() in ("ollama", "2"):
        return OllamaClient(**kwargs)
    raise ValueError(f"Unknown provider: {provider}")


def call_llm(prompt: str, provider: str = "1") -> str:
    """Legacy wrapper for backward compatibility.

    Args:
        prompt: The prompt to send
        provider: "1" for Groq, "2" for Ollama

    Returns:
        Generated response text
    """
    # Interactive API key prompt for Groq
    if provider == "1":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            api_key = input("Groq API key: ").strip()
        client = GroqClient(api_key=api_key)
    else:
        client = OllamaClient()

    return client.generate(prompt)
