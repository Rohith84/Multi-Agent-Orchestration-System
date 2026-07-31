"""
Knowledge service — business logic orchestrating document loaders, chunkers,
embedding generators, repositories, and ChromaDB vector store.
"""

import asyncio
import time
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.knowledge.chunker import DocumentChunker
from app.knowledge.embeddings.generator import OllamaEmbeddingGenerator
from app.knowledge.loader import DocumentLoader, UnsupportedFileTypeError
from app.knowledge.vectorstore.chroma import ChromaStore
from app.models.knowledge import KnowledgeDocument
from app.repositories.knowledge_repository import KnowledgeRepository

logger = get_logger(__name__)


class KnowledgeService:
    """
    Coordinates ingestion, semantic mapping, and indexing of knowledge documents.
    Tracks reindexing progress globally in memory.
    """

    # Global in-memory progress tracker for re-indexing
    _reindex_status = {
        "status": "idle",
        "processed": 0,
        "total": 0,
        "error": None,
    }

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = KnowledgeRepository(db)
        self.loader = DocumentLoader()
        self.chunker = DocumentChunker(chunk_size=500, chunk_overlap=100)
        self.generator = OllamaEmbeddingGenerator()
        self.vector_store = ChromaStore()

    @classmethod
    def get_reindex_progress(cls) -> dict[str, Any]:
        """Get the current in-memory status of reindexing."""
        return cls._reindex_status

    async def upload_document(self, filename: str, content_bytes: bytes) -> KnowledgeDocument:
        """
        Ingest a new document: Load, parse, chunk, embed, and store in PG + ChromaDB.
        """
        start_time = time.time()
        logger.info("Starting upload ingestion for: %s", filename)

        # 1. Parse content
        try:
            text_content = await self.loader.load(filename, content_bytes)
        except UnsupportedFileTypeError:
            logger.error("Failed ingestion: unsupported file type for %s", filename)
            raise
        except Exception as e:
            logger.exception("Failed ingestion during document load parsing for %s", filename)
            raise ValueError(f"Parsing error: {e}") from e

        if not text_content.strip():
            raise ValueError("Document contains no readable text content.")

        # 2. Save document metadata in PostgreSQL
        ext = filename.split(".")[-1] if "." in filename else "txt"
        doc = await self.repository.create_document(
            filename=filename,
            file_type=ext.upper(),
        )
        await self.db.commit()

        # 3. Chunk text content
        chunks = self.chunker.chunk(text_content)
        if not chunks:
            # Delete doc metadata if no text extracted/chunked
            await self.repository.delete_document(doc.id)
            await self.db.commit()
            raise ValueError("No text chunks generated from the document.")

        # 4. Save chunks in PostgreSQL & generate embeddings for ChromaDB
        db_chunks = []
        chroma_chunks = []
        embedding_total_time = 0.0

        for idx, chunk_content in enumerate(chunks):
            # Save chunk in PG
            db_chunk = await self.repository.create_chunk(
                document_id=doc.id,
                chunk_index=idx,
                content=chunk_content,
            )
            db_chunks.append(db_chunk)

            # Generate embedding with retry logic inside the generator
            try:
                emb_start = time.time()
                embedding = await self.generator.generate_embedding(chunk_content)
                embedding_total_time += time.time() - emb_start
            except Exception as e:
                logger.error("Failed to generate embedding for chunk %d of document %s: %s", idx, filename, e)
                # Rollback PG document and raise exception
                await self.repository.delete_document(doc.id)
                await self.db.commit()
                raise

            chroma_chunks.append({
                "chunk_index": idx,
                "content": chunk_content,
                "embedding": embedding,
            })

        await self.db.commit()

        # 5. Store embeddings in ChromaDB
        try:
            self.vector_store.add_chunks(
                document_id=doc.id,
                filename=filename,
                chunks=chroma_chunks,
            )
        except Exception as e:
            logger.error("Failed to index chunks in ChromaDB for %s: %s", filename, e)
            # Clean up PG entries if ChromaDB fails
            await self.repository.delete_document(doc.id)
            await self.db.commit()
            raise

        upload_duration = time.time() - start_time
        logger.info(
            "Successfully ingested document: %s. Upload + Chunks + DB time: %.2fs. Total Embedding time: %.2fs.",
            filename,
            upload_duration,
            embedding_total_time,
        )

        return doc

    async def list_documents(self) -> list[KnowledgeDocument]:
        """List all indexed documents from PostgreSQL."""
        return await self.repository.get_documents()

    async def delete_document(self, doc_id: uuid.UUID) -> None:
        """Delete document metadata, database chunks, and vector store embeddings."""
        logger.info("Initiating deletion of document: %s", doc_id)
        # 1. Delete in ChromaDB
        try:
            self.vector_store.delete_document(doc_id)
        except Exception as e:
            logger.error("Error deleting from ChromaDB for doc %s: %s", doc_id, e)
            # Proceed to delete in PG anyway to clean up DB state

        # 2. Delete in PostgreSQL (cascades to chunks)
        await self.repository.delete_document(doc_id)
        await self.db.commit()
        logger.info("Successfully deleted document %s from system", doc_id)

    async def reindex_all_documents(self) -> None:
        """
        Recreates all vector embeddings in ChromaDB from PostgreSQL chunks in a background operation.
        Updates global progress mapping.
        """
        cls = self.__class__
        if cls._reindex_status["status"] == "running":
            logger.warning("Reindexing already in progress. Skipping.")
            return

        cls._reindex_status.update({
            "status": "running",
            "processed": 0,
            "total": 0,
            "error": None,
        })

        try:
            # 1. Fetch all chunks
            chunks = await self.repository.get_all_chunks()
            if not chunks:
                cls._reindex_status.update({
                    "status": "completed",
                    "processed": 0,
                    "total": 0,
                })
                logger.info("Reindexing complete: no chunks exist in DB.")
                return

            cls._reindex_status["total"] = len(chunks)
            logger.info("Starting reindexing of %d chunks", len(chunks))

            # 2. Clear collection
            self.vector_store.clear_collection()

            # Group chunks by document so we can batch inserts
            doc_groups = {}
            for chunk in chunks:
                doc_groups.setdefault(chunk.document_id, {
                    "filename": chunk.document.filename,
                    "chunks": []
                })
                doc_groups[chunk.document_id]["chunks"].append(chunk)

            # Re-generate embeddings and insert document by document
            for doc_id, doc_data in doc_groups.items():
                filename = doc_data["filename"]
                chroma_chunks = []

                for chunk in doc_data["chunks"]:
                    try:
                        embedding = await self.generator.generate_embedding(chunk.content)
                        chroma_chunks.append({
                            "chunk_index": chunk.chunk_index,
                            "content": chunk.content,
                            "embedding": embedding,
                        })
                    except Exception as e:
                        logger.error(
                            "Reindexing failed for document %s, chunk %d: %s",
                            filename,
                            chunk.chunk_index,
                            e
                        )
                        raise ValueError(f"Re-indexing failed during embedding generation: {e}") from e
                    
                    # Update progress
                    cls._reindex_status["processed"] += 1

                # Save batches to Chroma
                self.vector_store.add_chunks(
                    document_id=doc_id,
                    filename=filename,
                    chunks=chroma_chunks,
                )

            cls._reindex_status["status"] = "completed"
            logger.info("Reindexing completed successfully.")

        except Exception as e:
            cls._reindex_status.update({
                "status": "failed",
                "error": str(e),
            })
            logger.error("Reindexing workflow failed: %s", e)
