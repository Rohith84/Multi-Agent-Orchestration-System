"""
Celery Application Configuration.

Configures Celery with Redis broker and result backend for background task processing.
"""

from __future__ import annotations

import os
from celery import Celery
from kombu import Queue

from app.core.config import get_settings

settings = get_settings()

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "multi_agent_worker",
    broker=redis_url,
    backend=redis_url,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_queues=[
        Queue("default", routing_key="default.#"),
        Queue("workflows", routing_key="workflow.#"),
        Queue("indexing", routing_key="indexing.#"),
        Queue("analytics", routing_key="analytics.#"),
        Queue("tools", routing_key="tool.#"),
    ],
    task_default_queue="default",
    task_default_exchange="tasks",
    task_default_routing_key="default",
)
