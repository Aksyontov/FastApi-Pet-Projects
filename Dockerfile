FROM python:3.12

# Set the working directory
WORKDIR /app

# Copy and install dependencies
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the application files
COPY ./alembic.ini /app/alembic.ini
COPY ./blog_app /app/blog_app

# Copy the wait-for-it.sh script
COPY ./wait-for-it.sh /app/wait-for-it.sh
RUN chmod +x /app/wait-for-it.sh

# Expose the port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "blog_app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]