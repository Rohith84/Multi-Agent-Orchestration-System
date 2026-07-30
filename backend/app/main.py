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

    yield

    # Shutdown
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
        version="0.2.0",
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

    # Register exception handlers
    register_exception_handlers(app)

    # Include routers
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(agents_router)

    logger.info(
        "Application created: %s (model=%s)",
        settings.app_name,
        settings.model_name,
    )

    return app


# Create the application instance
app = create_app()
