"""Celery application — YU-NA background jobs.

Faza 5: Background Jobs infrastructure.
"""
from __future__ import annotations

import sys
sys.path.insert(0, "/home/ubuntu/terra-os/packages/vendor")

import os
from celery import Celery
from kombu import Queue

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")

celery_app = Celery(
    "terra",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["services.api.services.api.tasks"],
)

celery_app.conf.update(
    task_queues=(
        Queue("critical", routing_key="critical"),
        Queue("normal", routing_key="normal"),
        Queue("batch", routing_key="batch"),
    ),
    task_default_queue="normal",
    task_default_routing_key="normal",
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Warsaw",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    beat_schedule={
        "sync-bzp-every-15-min": {
            "task": "services.api.services.api.tasks.sync_bzp_task",
            "schedule": 900.0,  # 15 minutes
            "options": {"queue": "normal"},
        },
    },
)
