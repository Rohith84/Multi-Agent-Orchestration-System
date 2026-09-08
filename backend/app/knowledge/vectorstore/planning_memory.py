"""
ChromaDB Planning Memory vector store adapter.

Indexes completed execution plans and performs similarity searches for architectural reuse.
"""

from __future__ import annotations

import uuid
from typing import Any
try:
    import chromadb
except ImportError:
    chromadb = None

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
        self._client: Any | None = None
        self._collection: Any | None = None
        self.embedding_generator = OllamaEmbeddingGenerator()

    def _get_client(self) -> Any:
        if chromadb is None:
            logger.warning("ChromaDB is not installed in environment.")
            return None
        if self._client is None:
            logger.info("Initializing ChromaDB PersistentClient for Planning Memory at path=%s", self.path)
            self._client = chromadb.PersistentClient(path=self.path)
        return self._client

    def _purge_target_collection_sqlite(self, target_name: str) -> None:
        """Targeted SQLite purge of ONLY the corrupted collection metadata and segments."""
        import os
        import sqlite3
        db_file = os.path.join(self.path, "chroma.sqlite3")
        if not os.path.exists(db_file):
            return
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM collections WHERE name = ?", (target_name,))
            rows = cursor.fetchall()
            if rows:
                col_ids = [r[0] for r in rows]
                for cid in col_ids:
                    cursor.execute("DELETE FROM collection_metadata WHERE collection_id = ?", (cid,))
                    cursor.execute("DELETE FROM segment_metadata WHERE segment_id IN (SELECT id FROM segments WHERE collection = ?)", (cid,))
                    cursor.execute("DELETE FROM segments WHERE collection = ?", (cid,))
                    cursor.execute("DELETE FROM collections WHERE id = ?", (cid,))
                conn.commit()
                logger.info("Targeted SQLite cleanup removed corrupted planning memory collection '%s' (%d IDs)", target_name, len(col_ids))
            conn.close()
        except Exception as e:
            logger.warning("Targeted SQLite cleanup for planning memory collection '%s' encountered: %s", target_name, e)

    def _get_collection(self) -> Any:
        if self._collection is None:
            client = self._get_client()
            if client is None:
                return None
            from app.knowledge.embeddings.generator import EmbeddingGenerator
            generator = EmbeddingGenerator()
            target_dim = generator.get_dimension()
            
            try:
                self._collection = client.get_collection(name=self.collection_name)
                if self._collection.count() > 0:
                    peek_data = self._collection.peek(limit=1)
                    embeddings = peek_data.get("embeddings")
                    if embeddings is not None and len(embeddings) > 0:
                        existing_dim = len(embeddings[0])
                        if existing_dim != target_dim:
                            logger.warning(
                                "Dimension mismatch in Chroma DB '%s': active model expects %d, "
                                "but existing collection has %d. Re-creating collection...",
                                self.collection_name,
                                target_dim,
                                existing_dim
                            )
                            client.delete_collection(name=self.collection_name)
                            self._collection = client.create_collection(
                                name=self.collection_name,
                                metadata={"hnsw:space": "cosine"}
                            )
            except Exception as e:
                err_str = str(e).lower()
                if isinstance(e, KeyError) or "_type" in err_str:
                    logger.warning("Targeted recovery for planning memory collection '%s' (%s)", self.collection_name, e)
                    self._purge_target_collection_sqlite(self.collection_name)
                    self._client = None
                    fresh_client = self._get_client()
                    try:
                        self._collection = fresh_client.create_collection(
                            name=self.collection_name,
                            metadata={"hnsw:space": "cosine"}
                        )
                    except Exception:
                        self._collection = None
                elif "does not exist" in err_str or "not found" in err_str or "notfound" in type(e).__name__.lower():
                    # Collection does not exist
                    logger.info("ChromaDB collection '%s' does not exist. Creating...", self.collection_name)
                    try:
                        self._collection = client.create_collection(
                            name=self.collection_name,
                            metadata={"hnsw:space": "cosine"}
                        )
                    except Exception as create_err:
                        logger.exception("Failed to create Planning Memory collection: %s", self.collection_name)
                        self._collection = client.get_or_create_collection(
                            name=self.collection_name,
                            metadata={"hnsw:space": "cosine"}
                        )
                else:
                    logger.exception("Failed to get/verify Planning Memory collection: %s", self.collection_name)
                    try:
                        self._collection = client.get_or_create_collection(
                            name=self.collection_name,
                            metadata={"hnsw:space": "cosine"}
                        )
                    except Exception:
                        self._collection = None
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
