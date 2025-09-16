FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1

WORKDIR /app
COPY services/comms-svc/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared directory first
COPY services/shared ./shared

# Copy service files
COPY services/comms-svc/ .
EXPOSE 8083
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8083"]
