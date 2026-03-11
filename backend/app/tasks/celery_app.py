from celery import Celery

from app.config import settings

celery_app = Celery(
    "stacksniper",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=540,
)

celery_app.autodiscover_tasks(["app.tasks"])

# Beat schedule: refresh data post-game Tuesday 6am ET, pre-TNF Thursday 6pm ET
celery_app.conf.beat_schedule = {
    "refresh-tuesday-morning": {
        "task": "refresh_nfl_data",
        "schedule": {
            "crontab": {"minute": "0", "hour": "11", "day_of_week": "2"},
        },
        "args": (2025, 1),
    },
    "refresh-thursday-evening": {
        "task": "refresh_nfl_data",
        "schedule": {
            "crontab": {"minute": "0", "hour": "23", "day_of_week": "4"},
        },
        "args": (2025, 1),
    },
}
