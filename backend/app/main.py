"""
FastAPI application entry point.

Configures:
- CORS middleware
- Lifespan handler (DB init/teardown)
- Router includes
- Exception handlers
- Structured logging
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.agents import router as agents_router
from app.api.knowledge import router as knowledge_router
from app.api.tools import router as tools_router
from app.api.workflows import router as workflows_router
from app.api.analytics import router as analytics_router
from app.api.prompts import router as prompts_router
from app.api.operations import router as operations_router
from app.api.workspace import router as workspace_router
from app.api.artifacts import router as artifacts_router
from app.api.workflow_builder import router as workflow_builder_router
from app.core.rate_limit import RateLimitMiddleware
from app.services.scheduler import get_workflow_scheduler
from app.core.config import get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.db.database import close_db, init_db

# Initialize logging before anything else
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan handler.

    Startup: initializes database tables.
    Shutdown: disposes database engine.
    """
    # Startup
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning("Database initialization failed: %s", e)
        logger.warning("The backend will still run but DB features won't work.")

    # Initialize MCP Server and register all tools
    try:
        from app.mcp.tools import register_all_tools
        from app.mcp.server import get_mcp_server

        register_all_tools()
        mcp_server = get_mcp_server()
        mcp_server.initialize()
        logger.info("MCP Server initialized successfully")
    except Exception as e:
        logger.warning("MCP Server initialization failed: %s", e)
        logger.warning("The backend will still run but MCP tools won't work.")

    # Start background scheduler
    scheduler = get_workflow_scheduler()
    scheduler.start()

    yield

    # Shutdown
    scheduler.stop()
    await close_db()
    logger.info("Database connection closed")


def create_app() -> FastAPI:
    """
    Application factory.

    Creates and configures the FastAPI instance.
    Using a factory pattern makes testing easier
    and supports multiple app configurations.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="Multi Agent Orchestration System API",
        version="0.4.0",
        lifespan=lifespan,
    )

    # CORS — allow frontend origin
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(RateLimitMiddleware)

    # Register exception handlers
    register_exception_handlers(app)

    # Include routers
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(agents_router)
    app.include_router(knowledge_router)
    app.include_router(tools_router)
    app.include_router(workflows_router)
    app.include_router(analytics_router)
    app.include_router(prompts_router)
    app.include_router(operations_router)
    app.include_router(workspace_router)
    app.include_router(artifacts_router)
    app.include_router(workflow_builder_router)

    logger.info(
        "Application created: %s (model=%s)",
        settings.app_name,
        settings.model_name,
    )

    return app


# Create the application instance
app = create_app()
