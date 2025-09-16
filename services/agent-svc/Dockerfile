FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1

WORKDIR /app
COPY services/agent-svc/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared directory first
COPY services/shared ./shared

# Copy service files
COPY services/agent-svc/ .
EXPOSE 8082
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8082"]
