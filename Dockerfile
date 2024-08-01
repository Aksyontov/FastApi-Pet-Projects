FROM python:3.11

COPY ./requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

COPY ./alembic.ini /alembic.ini
COPY blog_app /NewTwitterApp

CMD ["uvicorn", "NewTwitterApp.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]


