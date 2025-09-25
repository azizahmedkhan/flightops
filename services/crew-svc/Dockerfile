FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY services/ /app/services/

WORKDIR /app/services/crew-svc

RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8086

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8086"]
