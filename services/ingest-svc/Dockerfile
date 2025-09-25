FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY services/ /app/services/

WORKDIR /app/services/ingest-svc

RUN pip install --no-cache-dir -r requirements.txt

# Copy data into the image so /ingest/seed works without mounts
COPY data /data

EXPOSE 8084

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8084"]
