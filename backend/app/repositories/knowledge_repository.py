"""
Knowledge repository — data access layer for knowledge documents and chunks.
"""

import uuid
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument

logger = get_logger(__name__)


class KnowledgeRepository:
    """
    Repository for CRUD operations on KnowledgeDocument and KnowledgeChunk.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_document(self, filename: str, file_type: str) -> KnowledgeDocument:
        """
        Record a new document metadata in the database.
        """
        doc = KnowledgeDocument(
            filename=filename,
            file_type=file_type,
        )
        self.db.add(doc)
        await self.db.flush()
        logger.info("Created document metadata entry: %s (id=%s)", filename, doc.id)
        return doc

    async def create_chunk(self, document_id: uuid.UUID, chunk_index: int, content: str) -> KnowledgeChunk:
        """
        Save a single text chunk associated with a document.
        """
        chunk = KnowledgeChunk(
            document_id=document_id,
            chunk_index=chunk_index,
            content=content,
        )
        self.db.add(chunk)
        await self.db.flush()
        return chunk

    async def get_document(self, doc_id: uuid.UUID) -> KnowledgeDocument | None:
        """
        Retrieve a document by its ID.
        """
        result = await self.db.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.id == doc_id)
        )
        return result.scalar_one_or_none()

    async def get_document_with_chunks(self, doc_id: uuid.UUID) -> KnowledgeDocument | None:
        """
        Retrieve a document with all its chunks eagerly loaded.
        """
        result = await self.db.execute(
            select(KnowledgeDocument)
            .options(selectinload(KnowledgeDocument.chunks))
            .where(KnowledgeDocument.id == doc_id)
        )
        return result.scalar_one_or_none()

    async def get_documents(self) -> list[KnowledgeDocument]:
        """
        List all uploaded documents.
        """
        result = await self.db.execute(
            select(KnowledgeDocument).order_by(KnowledgeDocument.uploaded_at.desc())
        )
        docs = list(result.scalars().all())
        logger.debug("Retrieved %d documents from database", len(docs))
        return docs

    async def delete_document(self, doc_id: uuid.UUID) -> int:
        """
        Delete a document and cascade delete its chunks.
        """
        # SQLAlchemy with passive_deletes/cascade will delete chunks in database
        result = await self.db.execute(
            delete(KnowledgeDocument).where(KnowledgeDocument.id == doc_id)
        )
        deleted_count = result.rowcount
        logger.info("Deleted document %s (rowcount=%d)", doc_id, deleted_count)
        return deleted_count

    async def get_document_chunks(self, doc_id: uuid.UUID) -> list[KnowledgeChunk]:
        """
        Get all chunks for a specific document.
        """
        result = await self.db.execute(
            select(KnowledgeChunk)
            .where(KnowledgeChunk.document_id == doc_id)
            .order_by(KnowledgeChunk.chunk_index.asc())
        )
        return list(result.scalars().all())

    async def get_all_chunks(self) -> list[KnowledgeChunk]:
        """
        Get all chunks in the entire database (used for reindexing).
        """
        result = await self.db.execute(
            select(KnowledgeChunk)
            .options(selectinload(KnowledgeChunk.document))
            .order_by(KnowledgeChunk.document_id, KnowledgeChunk.chunk_index)
        )
        return list(result.scalars().all())
