from loguru import logger
import os, time
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["service","path","method","code"])
LATENCY = Histogram("http_request_latency_seconds", "Request latency", ["service","path","method"])

def log_startup(service: str):
    logger.info(f"{service} starting...")
    logger.info(f"ENV: { {k:v for k,v in os.environ.items() if k in ['DB_HOST','DB_NAME','CHAT_MODEL','EMBEDDINGS_MODEL','ALLOW_UNGROUNDED_ANSWERS','OPENAI_API_KEY']} }")

