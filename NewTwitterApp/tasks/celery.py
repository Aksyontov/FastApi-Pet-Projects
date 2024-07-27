from celery import Celery

celery = Celery(
    "tasks",
    broker="redis://localhost",
    tasks=["app.tasks.tasks"]
)