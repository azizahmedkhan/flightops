FROM python:3.11-slim-bullseye

WORKDIR /app

# Install system dependencies and security updates
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && apt-get upgrade -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Copy requirements and install Python dependencies
COPY services/scalable-chatbot-svc/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip cache purge

# Copy shared modules
COPY services/shared /app/shared

# Copy service code
COPY services/scalable-chatbot-svc/ .

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8088

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8088/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8088"]
