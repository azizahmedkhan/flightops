FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY services/crew-svc/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared directory first
COPY services/shared ./shared

# Copy application code
COPY services/crew-svc/. .

# Expose port
EXPOSE 8086

# Run the application
CMD ["python", "main.py"]
