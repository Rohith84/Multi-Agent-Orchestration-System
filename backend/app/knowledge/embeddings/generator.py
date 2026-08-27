"""
Embedding generator for producing text vectors via FastEmbed (in-process CPU) or Ollama.
"""

import time
import httpx
from typing import ClassVar
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingGenerationError(Exception):
    """Exception raised when embedding generation fails."""
    pass


class BaseEmbeddingGenerator:
    """Abstract base class for embedding generators."""
    async def generate_embedding(self, text: str) -> list[float]:
        raise NotImplementedError

    def get_dimension(self) -> int:
        raise NotImplementedError


class FastEmbeddingGenerator(BaseEmbeddingGenerator):
    """
    In-process CPU embedding generator using Qdrant FastEmbed.
    """
    _model_instance = None  # Class-level cache to avoid re-initializing ONNX runtime on every request

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        self.model_name = model_name
        self._initialize_model()

    def _initialize_model(self) -> None:
        if FastEmbeddingGenerator._model_instance is None:
            try:
                from fastembed import TextEmbedding
                logger.info("Initializing FastEmbed CPU model: %s", self.model_name)
                start = time.time()
                FastEmbeddingGenerator._model_instance = TextEmbedding(model_name=self.model_name)
                logger.info("FastEmbed model initialized in %.3f seconds", time.time() - start)
            except Exception as e:
                logger.error("Failed to initialize FastEmbed: %s", e)
                raise EmbeddingGenerationError(f"FastEmbed initialization failed: {e}") from e

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding in-process on CPU."""
        if not text.strip():
            return [0.0] * self.get_dimension()
        try:
            model = FastEmbeddingGenerator._model_instance
            embeddings = list(model.embed([text]))
            if embeddings and len(embeddings) > 0:
                return [float(x) for x in embeddings[0]]
            raise EmbeddingGenerationError("No embeddings returned by FastEmbed model")
        except Exception as e:
            logger.error("FastEmbed generation failed: %s", e)
            raise EmbeddingGenerationError(f"FastEmbed failed: {e}") from e

    def get_dimension(self) -> int:
        if "bge-small" in self.model_name:
            return 384
        if "bge-base" in self.model_name:
            return 768
        if "nomic-embed-text" in self.model_name:
            return 768
        return 384


class OllamaRestEmbeddingGenerator(BaseEmbeddingGenerator):
    """
    REST client that connects to a local Ollama instance for embeddings.
    """
    def __init__(self, model_name: str, base_url: str) -> None:
        self.model = model_name
        self.base_url = base_url
        self.timeout = 30.0

    async def generate_embedding(self, text: str) -> list[float]:
        endpoints = [
            ("/api/embeddings", {"model": self.model, "prompt": text}, "embedding"),
            ("/api/embed", {"model": self.model, "input": text}, "embeddings")
        ]
        start_time = time.time()
        for attempt in range(2):
            for path, payload, response_key in endpoints:
                url = f"{self.base_url.rstrip('/')}{path}"
                try:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.post(url, json=payload)
                        if response.status_code == 404:
                            continue
                        response.raise_for_status()
                        data = response.json()
                        if response_key == "embedding":
                            embedding = data.get("embedding")
                        else:
                            embeddings = data.get("embeddings")
                            embedding = embeddings[0] if embeddings else None
                        if embedding:
                            return [float(x) for x in embedding]
                except Exception as e:
                    logger.warning("Ollama embedding attempt %d failed on endpoint %s: %s", attempt + 1, path, e)
            if attempt == 0:
                time.sleep(1.0)
        raise EmbeddingGenerationError(f"Failed to generate embedding for model {self.model} via Ollama")

    def get_dimension(self) -> int:
        return 768


class EmbeddingGenerator(BaseEmbeddingGenerator):
    """
    Unified Embedding Generator.
    Delegates to FastEmbeddingGenerator or OllamaRestEmbeddingGenerator
    based on app configuration.
    """
    def __init__(self) -> None:
        settings = get_settings()
        provider = getattr(settings, "embedding_provider", "fastembed").lower()
        
        if provider == "ollama":
            self.delegate = OllamaRestEmbeddingGenerator(
                model_name=settings.embedding_model,
                base_url=settings.ollama_base_url
            )
            logger.info("Using Ollama Embedding Generator (model=%s)", settings.embedding_model)
        else:
            self.delegate = FastEmbeddingGenerator()
            logger.info("Using FastEmbed (In-Process CPU) Embedding Generator")

    async def generate_embedding(self, text: str) -> list[float]:
        return await self.delegate.generate_embedding(text)

    def get_dimension(self) -> int:
        return self.delegate.get_dimension()


# Keep legacy wrapper class for backwards compatibility
class OllamaEmbeddingGenerator(EmbeddingGenerator):
    """
    Legacy wrapper class. Now delegates to the unified EmbeddingGenerator.
    """
    pass
