FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY services/predictive-svc/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities and application code
COPY services/shared ./shared
COPY services/predictive-svc/ ./

# Expose port
EXPOSE 8085

# Run the application
CMD ["python", "main.py"]
