"""
ChromaDB Planning Memory vector store adapter.

Indexes completed execution plans and performs similarity searches for architectural reuse.
"""

from __future__ import annotations

import uuid
from typing import Any
import chromadb

from app.core.config import get_settings
from app.core.logging import get_logger
from app.knowledge.embeddings.generator import OllamaEmbeddingGenerator

logger = get_logger(__name__)


class PlanningMemoryStore:
    """
    Vector store adapter for storing and querying historical execution plans in ChromaDB.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.path = self.settings.vector_db_path
        self.collection_name = "planning_memory"
        self._client: chromadb.PersistentClient | None = None
        self._collection: Any | None = None
        self.embedding_generator = OllamaEmbeddingGenerator()

    def _get_client(self) -> chromadb.PersistentClient:
        if self._client is None:
            logger.info("Initializing ChromaDB PersistentClient for Planning Memory at path=%s", self.path)
            self._client = chromadb.PersistentClient(path=self.path)
        return self._client

    def _get_collection(self) -> Any:
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    async def add_plan(
        self,
        memory_id: uuid.UUID,
        goal: str,
        plan: str,
        success_score: float = 100.0,
    ) -> None:
        """
        Embed and store a completed execution plan into ChromaDB.
        """
        try:
            embedding = await self.embedding_generator.generate_embedding(goal)
            collection = self._get_collection()

            collection.add(
                ids=[str(memory_id)],
                embeddings=[embedding],
                metadatas=[{
                    "memory_id": str(memory_id),
                    "goal": goal[:500],
                    "success_score": float(success_score),
                }],
                documents=[plan],
            )
            logger.info("Indexed planning memory ID=%s in ChromaDB", memory_id)
        except Exception as e:
            logger.warning("Failed to store planning memory vector in ChromaDB: %s", e)

    async def search_similar_plans(
        self,
        user_request: str,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Perform vector similarity search for prior completed plans matching a user request.
        """
        try:
            embedding = await self.embedding_generator.generate_embedding(user_request)
            collection = self._get_collection()

            results = collection.query(
                query_embeddings=[embedding],
                n_results=top_k,
            )

            matches = []
            if results and results.get("documents") and len(results["documents"][0]) > 0:
                docs = results["documents"][0]
                metas = results["metadatas"][0]
                distances = results["distances"][0]

                for i in range(len(docs)):
                    sim_score = round(max(0.0, min(1.0, 1.0 - distances[i])), 4)
                    matches.append({
                        "memory_id": metas[i].get("memory_id"),
                        "goal": metas[i].get("goal"),
                        "plan": docs[i],
                        "similarity_score": sim_score,
                    })

            logger.info("Retrieved %d matching planning memories for request", len(matches))
            return matches
        except Exception as e:
            logger.warning("Planning memory similarity search failed: %s", e)
            return []
