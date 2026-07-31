"""
Embedding generator for producing text vectors via Ollama.
"""

import time
import httpx
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingGenerationError(Exception):
    """Exception raised when embedding generation fails."""
    pass


class OllamaEmbeddingGenerator:
    """
    Interfaces with the local Ollama instance to generate vector embeddings.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.ollama_base_url
        self.model = self.settings.embedding_model
        self.timeout = 30.0

    async def generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding vector for the given text.
        Retries once if embedding fails.

        Args:
            text: Text block to embed.

        Returns:
            List of float values representing the embedding.
        """
        # Endpoint options
        endpoints = [
            ("/api/embeddings", {"model": self.model, "prompt": text}, "embedding"),
            ("/api/embed", {"model": self.model, "input": text}, "embeddings")
        ]

        start_time = time.time()
        
        # Try up to 2 attempts (retry once)
        for attempt in range(2):
            for path, payload, response_key in endpoints:
                url = f"{self.base_url.rstrip('/')}{path}"
                try:
                    logger.debug("Generating embedding (attempt %d/2) using %s endpoint", attempt + 1, path)
                    
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.post(url, json=payload)
                        
                        if response.status_code == 404:
                            # Endpoint not found, try the next one
                            continue
                            
                        response.raise_for_status()
                        data = response.json()
                        
                        # Handle /api/embeddings vs /api/embed response format
                        if response_key == "embedding":
                            embedding = data.get("embedding")
                        else:
                            embeddings = data.get("embeddings")
                            embedding = embeddings[0] if embeddings else None

                        if embedding:
                            duration = time.time() - start_time
                            logger.info("Generated embedding in %.2f seconds (attempt %d/2, dimensions: %d)", duration, attempt + 1, len(embedding))
                            return embedding
                            
                except Exception as e:
                    logger.warning("Embedding attempt %d failed on endpoint %s: %s", attempt + 1, path, e)
            
            # Wait briefly before retrying
            if attempt == 0:
                time.sleep(1.0)

        # If both attempts failed, raise error
        logger.error("Failed to generate embedding after retries using model %s", self.model)
        raise EmbeddingGenerationError(f"Failed to generate embedding for model {self.model} via Ollama")
