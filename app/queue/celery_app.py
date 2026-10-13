import os
from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown

from app.clients.assistant_client import close_checkpointer_pool, get_checkpointer

celery_app = Celery(
    "replyai", broker=os.getenv("REDIS_URL"), backend=os.getenv("CELERY_RESULT_BACKEND")
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

celery_app.autodiscover_tasks(["app.queue"])


@worker_process_init.connect
def initialize_worker_resources(**kwargs):
    get_checkpointer()


@worker_process_shutdown.connect
def close_worker_resources(**kwargs):
    close_checkpointer_pool()
