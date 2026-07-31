"""
Retriever search component.
Runs semantic similarity search over ChromaDB and tracks time/metrics.
"""

import time
from typing import Any
from app.core.logging import get_logger
from app.knowledge.embeddings.generator import OllamaEmbeddingGenerator
from app.knowledge.vectorstore.chroma import ChromaStore, QueryResultChunk

logger = get_logger(__name__)


class KnowledgeRetriever:
    """
    Coordinates semantic search by converting queries to embeddings
    and querying the vector store.
    """

    def __init__(self) -> None:
        self.embedding_generator = OllamaEmbeddingGenerator()
        self.vector_store = ChromaStore()

    async def retrieve(self, query: str, top_k: int = 5) -> list[QueryResultChunk]:
        """
        Retrieves top K relevant chunks for a given query text.

        Args:
            query: The user query string.
            top_k: Number of relevant chunks to retrieve.

        Returns:
            List of QueryResultChunk dictionary results.
        """
        logger.info("Starting semantic retrieval for query: '%s'", query)
        
        try:
            # 1. Generate query embedding & track time
            emb_start = time.time()
            query_embedding = await self.embedding_generator.generate_embedding(query)
            emb_time = time.time() - emb_start
            logger.info("Retrieval: Embedding generation completed in %.4f seconds", emb_time)

            # 2. Similarity search & track time
            ret_start = time.time()
            results = self.vector_store.search_similarity(query_embedding, top_k=top_k)
            ret_time = time.time() - ret_start
            logger.info("Retrieval: Semantic search completed in %.4f seconds", ret_time)

            # 3. Log results and similarity scores
            logger.info(
                "Retrieval Summary: retrieved %d chunks in total. Details:",
                len(results)
            )
            for i, chunk in enumerate(results):
                logger.info(
                    "[%d] Document: %s (ID: %s), Chunk Index: %d, Similarity Score: %.4f",
                    i + 1,
                    chunk["filename"],
                    chunk["document_id"],
                    chunk["chunk_index"],
                    chunk["score"]
                )

            return results

        except Exception as e:
            logger.error("Error occurred during retrieval process: %s", e)
            # Re-raise so agents/services can catch and handle/log as needed
            raise
