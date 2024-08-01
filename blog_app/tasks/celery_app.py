from celery import Celery

celery_app = Celery(
    "tasks",
    broker="redis://localhost",
    include=["blog_app.tasks.tasks"]
)