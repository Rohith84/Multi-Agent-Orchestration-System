"""
Ollama REST API client.

Handles communication with the local Ollama instance.
Uses httpx for async HTTP requests to the Ollama chat API.
"""

from typing import Any

import httpx

from app.core.config import get_settings
from app.core.exceptions import (
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class OllamaClient:
    """
    Unified LLM Client supporting both local Ollama and Groq Cloud API.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.ollama_base_url
        self.model_name = settings.model_name
        self.timeout = settings.ollama_timeout
        self.groq_api_key = settings.groq_api_key

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
    ) -> str:
        """
        Send a chat completion request to Groq API or local Ollama.
        """
        model = model or self.model_name

        if self.groq_api_key:
            try:
                return await self._chat_groq(messages, model)
            except Exception as e:
                logger.warning("Groq API call failed (%s). Falling back to local Ollama.", e)
                return await self._chat_ollama(messages, "qwen2.5-coder:3b")

        return await self._chat_ollama(messages, model)

    async def _chat_groq(
        self,
        messages: list[dict[str, str]],
        model: str,
    ) -> str:
        """Send request to Groq Cloud OpenAI-compatible Endpoint."""
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 8192,
        }

        logger.info(
            "Sending request to Groq API (model=%s, messages=%d)",
            model,
            len(messages),
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()

            data = response.json()
            assistant_message = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )

            logger.info(
                "Received response from Groq API (model=%s, length=%d chars)",
                model,
                len(assistant_message),
            )
            return assistant_message

    async def _chat_ollama(
        self,
        messages: list[dict[str, str]],
        model: str,
    ) -> str:
        """Send chat completion request to local Ollama."""
        url = f"{self.base_url}/api/chat"

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "keep_alive": "15m",
            "options": {
                "num_gpu": 99,
                "num_ctx": 8192,
                "num_predict": 4096,
                "temperature": 0.2,
            },
        }

        logger.info(
            "Sending chat request to Ollama (model=%s, messages=%d)",
            model,
            len(messages),
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)

                if response.status_code == 404:
                    logger.error("Model '%s' not found in Ollama", model)
                    raise OllamaModelNotFoundError(model)

                response.raise_for_status()

                data = response.json()
                assistant_message = data.get("message", {}).get("content", "")

                logger.info(
                    "Received response from Ollama (model=%s, length=%d chars)",
                    model,
                    len(assistant_message),
                )

                return assistant_message

        except OllamaModelNotFoundError:
            raise
        except httpx.ConnectError as e:
            logger.error("Failed to connect to Ollama at %s: %s", self.base_url, e)
            raise OllamaConnectionError() from e
        except httpx.TimeoutException as e:
            logger.error("Ollama request timed out after %ds", self.timeout)
            raise OllamaTimeoutError(self.timeout) from e
        except httpx.HTTPStatusError as e:
            logger.error("Ollama HTTP error: %s", e)
            raise OllamaConnectionError(
                f"Ollama returned an error: {e.response.status_code}"
            ) from e

    async def is_available(self) -> bool:
        """Check if Ollama is reachable and the configured model exists."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code != 200:
                    return False

                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]

                # Check if our model is available (with or without :latest tag)
                return any(
                    self.model_name in model_name
                    for model_name in models
                )
        except Exception:
            return False

    async def get_runtime_status(self) -> dict[str, Any]:
        """
        Query Ollama's local /api/ps endpoint to inspect loaded process model, size, VRAM, and processor type.
        """
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                response = await client.get(f"{self.base_url}/api/ps")
                if response.status_code != 200:
                    return {
                        "status": "unavailable",
                        "loaded_models": [],
                        "processor": "unknown",
                        "vram_mb": 0,
                    }

                data = response.json()
                models = data.get("models", [])
                if not models:
                    return {
                        "status": "idle",
                        "loaded_models": [],
                        "processor": "idle",
                        "vram_mb": 0,
                    }

                loaded_info = []
                total_vram_bytes = 0
                processor_types = set()

                for m in models:
                    name = m.get("name", "unknown")
                    size = m.get("size", 0)
                    vram = m.get("size_vram", 0)
                    total_vram_bytes += vram

                    if vram == 0:
                        proc = "CPU"
                    elif size > 0 and vram >= size * 0.95:
                        proc = "GPU"
                    elif vram > 0:
                        proc = "CPU/GPU"
                    else:
                        proc = "unknown"

                    processor_types.add(proc)
                    loaded_info.append({
                        "name": name,
                        "size_mb": round(size / (1024 * 1024), 2),
                        "vram_mb": round(vram / (1024 * 1024), 2),
                        "processor": proc,
                    })

                primary_processor = "/".join(sorted(processor_types)) if processor_types else "unknown"

                return {
                    "status": "running",
                    "loaded_models": loaded_info,
                    "processor": primary_processor,
                    "vram_mb": round(total_vram_bytes / (1024 * 1024), 2),
                }
        except Exception as e:
            logger.warning("Failed querying Ollama /api/ps: %s", e)
            return {
                "status": "unknown",
                "loaded_models": [],
                "processor": "unknown",
                "vram_mb": 0,
            }
