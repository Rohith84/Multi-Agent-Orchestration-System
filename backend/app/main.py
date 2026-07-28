"""
FastAPI application entry point.

Configures:
- CORS middleware
- Lifespan handler (DB init/teardown)
- Router includes
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.core.config import get_settings
from app.db.database import close_db, init_db


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
        print("[OK] Database initialized successfully")
    except Exception as e:
        print(f"[WARN] Database initialization failed: {e}")
        print("   The backend will still run but DB features won't work.")

    yield

    # Shutdown
    await close_db()
    print("[INFO] Database connection closed")


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
        version="0.1.0",
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

    # Include routers
    app.include_router(health_router)

    return app


# Create the application instance
app = create_app()
