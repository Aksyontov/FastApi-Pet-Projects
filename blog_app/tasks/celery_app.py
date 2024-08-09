from celery import Celery

celery_app = Celery(
    'blog_app',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/0'
)

celery_app.conf.update(
    result_expires=3600,
)