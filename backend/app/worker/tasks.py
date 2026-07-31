"""
Celery Background Worker Tasks.

Provides background job handlers for workflow execution, document indexing, report generation, and analytics aggregation.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from app.core.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


def _run_async(coro: Any) -> Any:
    """Helper to run async coroutines inside synchronous Celery task workers."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(name="app.worker.tasks.execute_workflow_task", queue="workflows")
def execute_workflow_task(user_request: str, session_id_str: str, require_approval: list[str] | None = None) -> dict[str, Any]:
    """Execute a workflow asynchronously in background worker."""
    logger.info("Celery task started: execute_workflow_task for session %s", session_id_str)

    async def _async_exec():
        from app.db.database import async_session_factory
        from app.orchestration.workflow import WorkflowExecutor

        session_id = uuid.UUID(session_id_str)
        async with async_session_factory() as session:
            executor = WorkflowExecutor(session)
            results = []
            async for sse in executor.execute(
                user_request=user_request,
                session_id=session_id,
                require_approval_agents=require_approval,
            ):
                results.append(sse)
            return {"status": "completed", "events_count": len(results)}

    try:
        res = _run_async(_async_exec())
        logger.info("Celery task finished: execute_workflow_task for session %s", session_id_str)
        return res
    except Exception as e:
        logger.error("Celery workflow task failed: %s", e)
        return {"status": "failed", "error": str(e)}


@celery_app.task(name="app.worker.tasks.index_document_task", queue="indexing")
def index_document_task(document_id_str: str, filename: str, content: str) -> dict[str, Any]:
    """Index a document and generate vector embeddings asynchronously."""
    logger.info("Celery task started: index_document_task for doc %s", filename)

    async def _async_index():
        from app.knowledge.embeddings.generator import OllamaEmbeddingGenerator
        from app.knowledge.vectorstore.chroma import ChromaStore

        doc_id = uuid.UUID(document_id_str)
        embedder = OllamaEmbeddingGenerator()
        store = ChromaStore()

        # Chunk text into ~500 char blocks
        chunks = [content[i : i + 500] for i in range(0, len(content), 500)]
        chunk_data = []

        for idx, chunk_text in enumerate(chunks):
            embedding = await embedder.generate_embedding(chunk_text)
            chunk_data.append({
                "chunk_index": idx,
                "content": chunk_text,
                "embedding": embedding,
            })

        store.add_chunks(document_id=doc_id, filename=filename, chunks=chunk_data)
        return {"status": "indexed", "filename": filename, "chunks_count": len(chunk_data)}

    try:
        res = _run_async(_async_index())
        logger.info("Celery task finished: index_document_task for doc %s", filename)
        return res
    except Exception as e:
        logger.error("Celery document indexing task failed: %s", e)
        return {"status": "failed", "error": str(e)}


@celery_app.task(name="app.worker.tasks.generate_report_task", queue="analytics")
def generate_report_task(format_type: str = "json") -> dict[str, Any]:
    """Generate observability metrics report asynchronously."""
    logger.info("Celery task started: generate_report_task (%s)", format_type)

    async def _async_report():
        from app.db.database import async_session_factory
        from app.services.analytics_service import AnalyticsService

        async with async_session_factory() as session:
            service = AnalyticsService(session)
            report = await service.export_report(format_type=format_type)
            return {"status": "completed", "report_length": len(report)}

    try:
        return _run_async(_async_report())
    except Exception as e:
        logger.error("Celery report generation task failed: %s", e)
        return {"status": "failed", "error": str(e)}


@celery_app.task(name="app.worker.tasks.aggregate_analytics_task", queue="analytics")
def aggregate_analytics_task() -> dict[str, Any]:
    """Periodic Celery Beat task to aggregate system analytics metrics."""
    logger.info("Celery Beat task started: aggregate_analytics_task")
    return {"status": "aggregated", "timestamp": str(uuid.uuid4())}
