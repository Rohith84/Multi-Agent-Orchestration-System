"""
Multi-Agent API endpoints.

Provides:
- POST /api/agents/chat          — runs complete workflow and streams progress via SSE
- GET /api/agents/history/{id}   — gets chat history, execution details, and order
- DELETE /api/agents/history/{id}— deletes workflow history and executions
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.logging import get_logger
from app.schemas.agents import AgentRequest, AgentHistoryResponse, AgentExecutionSchema
from app.schemas.chat import ChatMessageSchema
from app.repositories.agent_repository import AgentExecutionRepository
from app.repositories.chat_repository import ChatRepository
from app.orchestration.workflow import WorkflowExecutor

logger = get_logger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])


def _get_agent_repository(db: AsyncSession = Depends(get_db)) -> AgentExecutionRepository:
    return AgentExecutionRepository(db)


def _get_chat_repository(db: AsyncSession = Depends(get_db)) -> ChatRepository:
    return ChatRepository(db)


@router.post("/chat")
async def run_agent_workflow(
    request: AgentRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Start a multi-agent orchestration request.
    Streams execution state updates sequentially via Server-Sent Events (SSE).
    """
    session_id = uuid.UUID(request.session_id) if request.session_id else uuid.uuid4()
    logger.info("Starting multi-agent workflow execution for session: %s", session_id)

    executor = WorkflowExecutor(db)

    return StreamingResponse(
        executor.execute(
            user_request=request.message,
            session_id=session_id,
            require_approval_agents=request.require_approval_agents,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Prevents buffering in Nginx/proxies
        }
    )


@router.get("/history/{session_id}", response_model=AgentHistoryResponse)
async def get_workflow_history(
    session_id: str,
    agent_repo: AgentExecutionRepository = Depends(_get_agent_repository),
    chat_repo: ChatRepository = Depends(_get_chat_repository),
) -> AgentHistoryResponse:
    """
    Retrieve aggregated history for a session, including messages and agent logs.
    """
    sid = uuid.UUID(session_id)

    # Check if session exists in either place
    chat_exists = await chat_repo.session_exists(sid)
    executions = await agent_repo.get_session_executions(sid)

    if not chat_exists and len(executions) == 0:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = await chat_repo.get_history(sid)

    chat_history = [
        ChatMessageSchema(
            id=str(msg.id),
            session_id=str(msg.session_id),
            role=msg.role,
            message=msg.message,
            llm_model=msg.model,
            created_at=msg.created_at,
        )
        for msg in messages
        if msg.role != "system"
    ]

    agent_executions = [
        AgentExecutionSchema(
            id=str(ex.id),
            session_id=str(ex.session_id),
            agent_name=ex.agent_name,
            input_content=ex.input_content,
            output_content=ex.output_content,
            execution_time=ex.execution_time,
            status=ex.status,
            created_at=ex.created_at,
        )
        for ex in executions
    ]

    # Chronological execution order list
    execution_order = [ex.agent_name for ex in executions]

    return AgentHistoryResponse(
        session_id=session_id,
        chat_history=chat_history,
        agent_executions=agent_executions,
        execution_order=execution_order,
    )


@router.delete("/history/{session_id}")
async def delete_workflow_history(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    agent_repo: AgentExecutionRepository = Depends(_get_agent_repository),
    chat_repo: ChatRepository = Depends(_get_chat_repository),
) -> dict:
    """
    IRREVERSIBLE: Delete all messages and agent run logs for this session.
    """
    sid = uuid.UUID(session_id)

    # Check if session exists
    chat_exists = await chat_repo.session_exists(sid)
    executions = await agent_repo.get_session_executions(sid)

    if not chat_exists and len(executions) == 0:
        raise HTTPException(status_code=404, detail="Session not found")

    deleted_msgs = await chat_repo.delete_session(sid)
    deleted_execs = await agent_repo.delete_session_executions(sid)
    await db.commit()

    return {
        "message": "Workflow history deleted successfully.",
        "session_id": session_id,
        "deleted_messages": deleted_msgs,
        "deleted_executions": deleted_execs,
    }
