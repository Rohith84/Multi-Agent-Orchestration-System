"""
Knowledge base API endpoints.
Provides:
- POST /api/knowledge/upload   — upload document
- GET /api/knowledge          — list uploaded documents
- DELETE /api/knowledge/{id}  — delete document
- POST /api/knowledge/reindex  — recreate vector database embeddings
- GET /api/knowledge/reindex/progress — get reindexing status
"""

import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.logging import get_logger
from app.services.knowledge_service import KnowledgeService
from app.loader import UnsupportedFileTypeError # type: ignore # import placeholder just in case, but we use the custom exception from loader module below

from app.knowledge.loader import UnsupportedFileTypeError

logger = get_logger(__name__)

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


def _get_knowledge_service(db: AsyncSession = Depends(get_db)) -> KnowledgeService:
    return KnowledgeService(db)


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    service: KnowledgeService = Depends(_get_knowledge_service),
) -> dict:
    """
    Upload and index a document.
    """
    logger.info("API request: upload document: %s", file.filename)
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty")

    try:
        content_bytes = await file.read()
        doc = await service.upload_document(file.filename, content_bytes)
        return {
            "message": "Document uploaded and indexed successfully",
            "document": {
                "id": str(doc.id),
                "filename": doc.filename,
                "file_type": doc.file_type,
                "uploaded_at": doc.uploaded_at.isoformat(),
            }
        }
    except UnsupportedFileTypeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error uploading document: %s", file.filename)
        raise HTTPException(status_code=500, detail=f"Failed to ingest document: {str(e)}")


@router.get("")
async def list_documents(
    service: KnowledgeService = Depends(_get_knowledge_service),
) -> list[dict]:
    """
    List all uploaded documents.
    """
    logger.info("API request: list documents")
    try:
        docs = await service.list_documents()
        return [
            {
                "id": str(doc.id),
                "filename": doc.filename,
                "file_type": doc.file_type,
                "uploaded_at": doc.uploaded_at.isoformat(),
            }
            for doc in docs
        ]
    except Exception as e:
        logger.exception("Failed to list documents")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    service: KnowledgeService = Depends(_get_knowledge_service),
) -> dict:
    """
    Delete a document and its index elements.
    """
    logger.info("API request: delete document: %s", doc_id)
    try:
        uid = uuid.UUID(doc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format")

    try:
        await service.delete_document(uid)
        return {
            "message": "Document deleted successfully",
            "id": doc_id,
        }
    except Exception as e:
        logger.exception("Failed to delete document %s", doc_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reindex")
async def reindex_documents(
    background_tasks: BackgroundTasks,
    service: KnowledgeService = Depends(_get_knowledge_service),
) -> dict:
    """
    Trigger recreation of vector store embeddings from database chunks.
    Runs asynchronously in a background task.
    """
    logger.info("API request: reindex documents")
    status = service.get_reindex_progress()
    if status["status"] == "running":
        return {"message": "Reindexing is already in progress"}

    background_tasks.add_task(service.reindex_all_documents)
    return {"message": "Reindexing started in background"}


@router.get("/reindex/progress")
async def get_reindex_progress() -> dict:
    """
    Get the status and progress of the background reindexing task.
    """
    return KnowledgeService.get_reindex_progress()
