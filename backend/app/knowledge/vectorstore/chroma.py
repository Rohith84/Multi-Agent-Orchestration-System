"""
ChromaDB vector store adapter.
"""

import uuid
from typing import Any, TypedDict
try:
    import chromadb
except ImportError:
    chromadb = None

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class VectorDBUnavailableError(Exception):
    """Exception raised when the vector database is unreachable or fails."""
    pass


class QueryResultChunk(TypedDict):
    content: str
    document_id: str
    filename: str
    chunk_index: int
    score: float


class ChromaStore:
    """
    Adapter for ChromaDB document/embedding storage and querying.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.path = self.settings.vector_db_path
        self.collection_name = "knowledge_base"
        self._client = None
        self._collection = None

    def _get_client(self) -> Any:
        """Lazy initialization of Chroma persistent client."""
        if chromadb is None:
            raise VectorDBUnavailableError("ChromaDB is not installed in environment.")
        if self._client is None:
            try:
                logger.info("Initializing ChromaDB PersistentClient at path=%s", self.path)
                self._client = chromadb.PersistentClient(path=self.path)
            except Exception as e:
                logger.exception("Failed to initialize ChromaDB client at %s", self.path)
                raise VectorDBUnavailableError(f"ChromaDB persistent client is unavailable: {e}") from e
        return self._client

    def _get_collection(self) -> Any:
        """Lazy retrieval of the vector collection with dimension compatibility check."""
        if self._collection is None:
            client = self._get_client()
            from app.knowledge.embeddings.generator import EmbeddingGenerator
            generator = EmbeddingGenerator()
            target_dim = generator.get_dimension()
            
            try:
                # Try to get the collection first
                self._collection = client.get_collection(name=self.collection_name)
                
                # Check for dimension mismatch if collection contains elements
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
                if "does not exist" in err_str or "not found" in err_str or "notfound" in type(e).__name__.lower():
                    # Collection does not exist yet
                    logger.info("ChromaDB collection '%s' does not exist. Creating...", self.collection_name)
                    try:
                        self._collection = client.create_collection(
                            name=self.collection_name,
                            metadata={"hnsw:space": "cosine"}
                        )
                    except Exception as create_err:
                        logger.exception("Failed to create ChromaDB collection: %s", self.collection_name)
                        raise VectorDBUnavailableError(f"Failed to create ChromaDB collection: {create_err}") from create_err
                else:
                    logger.exception("Failed to get or create ChromaDB collection: %s", self.collection_name)
                    raise VectorDBUnavailableError(f"Failed to access ChromaDB collection: {e}") from e
        return self._collection

    def add_chunks(
        self,
        document_id: uuid.UUID,
        filename: str,
        chunks: list[dict[str, Any]]
    ) -> None:
        """
        Store chunks and their embeddings into ChromaDB.

        Args:
            document_id: Database ID of the document.
            filename: Original file name.
            chunks: List of dicts, each containing:
                    - 'chunk_index': int
                    - 'content': str
                    - 'embedding': list[float]
        """
        if not chunks:
            return

        collection = self._get_collection()
        
        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for c in chunks:
            idx = c["chunk_index"]
            chunk_id = f"{document_id}_chunk_{idx}"
            
            ids.append(chunk_id)
            embeddings.append(c["embedding"])
            documents.append(c["content"])
            metadatas.append({
                "document_id": str(document_id),
                "filename": filename,
                "chunk_index": idx
            })

        try:
            logger.info("Adding %d chunks to ChromaDB collection for document: %s", len(ids), filename)
            collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents
            )
        except Exception as e:
            logger.exception("Failed to add vectors to ChromaDB collection")
            raise VectorDBUnavailableError(f"Failed to store chunks in ChromaDB: {e}") from e

    def delete_document(self, document_id: uuid.UUID) -> None:
        """
        Delete all chunks belonging to a document from ChromaDB.

        Args:
            document_id: Database ID of the document.
        """
        collection = self._get_collection()
        try:
            logger.info("Deleting chunks from ChromaDB for document ID: %s", document_id)
            collection.delete(where={"document_id": str(document_id)})
        except Exception as e:
            logger.exception("Failed to delete vectors from ChromaDB collection")
            raise VectorDBUnavailableError(f"Failed to delete chunks from ChromaDB: {e}") from e

    def search_similarity(
        self,
        query_embedding: list[float],
        top_k: int = 5
    ) -> list[QueryResultChunk]:
        """
        Perform a semantic similarity search in ChromaDB.

        Args:
            query_embedding: Vector representation of the search query.
            top_k: Number of top results to return.

        Returns:
            List of QueryResultChunk dictionaries with similarity score and metadata.
        """
        collection = self._get_collection()
        try:
            logger.info("Executing ChromaDB similarity search (top_k=%d)", top_k)
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )

            formatted_results = []
            if not results or not results["documents"] or len(results["documents"][0]) == 0:
                return formatted_results

            docs = results["documents"][0]
            metas = results["metadatas"][0]
            distances = results["distances"][0]

            for i in range(len(docs)):
                # Chroma distance is cosine distance (1 - cosine_similarity)
                # Let's map it to similarity score: similarity = 1.0 - distance
                distance = distances[i]
                similarity_score = max(0.0, min(1.0, 1.0 - distance))

                meta = metas[i]
                formatted_results.append({
                    "content": docs[i],
                    "document_id": meta.get("document_id", ""),
                    "filename": meta.get("filename", "Unknown"),
                    "chunk_index": int(meta.get("chunk_index", 0)),
                    "score": round(similarity_score, 4)
                })

            return formatted_results
        except Exception as e:
            logger.exception("Failed to query similarity from ChromaDB")
            raise VectorDBUnavailableError(f"Failed to query ChromaDB: {e}") from e

    def clear_collection(self) -> None:
        """Clear all entries in the collection."""
        collection = self._get_collection()
        try:
            logger.warning("Clearing all data from collection: %s", self.collection_name)
            # Fetch all items to delete them
            all_ids = collection.get()["ids"]
            if all_ids:
                collection.delete(ids=all_ids)
        except Exception as e:
            logger.exception("Failed to clear ChromaDB collection")
            raise VectorDBUnavailableError(f"Failed to clear ChromaDB collection: {e}") from e
