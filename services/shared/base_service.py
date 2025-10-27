from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram
import os
import logging
from typing import Optional

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["service", "path", "method", "code"],
)
LATENCY = Histogram(
    "http_request_latency_seconds",
    "Request latency",
    ["service", "path", "method"],
)

ENV_KEYS_TO_LOG = [
    "DB_HOST",
    "DB_NAME",
    "CHAT_MODEL",
    "EMBEDDINGS_MODEL",
    "ALLOW_UNGROUNDED_ANSWERS",
]

class BaseService:
    """Base service class with common functionality for all microservices"""
    
    def __init__(self, service_name: str, version: str = "1.0.0"):
        self.service_name = service_name
        self.version = version
        self.app = FastAPI(
            title=service_name,
            version=version,
            description=f"{service_name} microservice for AeroOps"
        )
        self._setup_cors()
        self._setup_logging()
        self._setup_routes()
        self.request_count = REQUEST_COUNT
        self.latency_histogram = LATENCY
    
    def _setup_cors(self):
        """Setup CORS middleware for all services"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # In production, specify actual origins
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_logging(self):
        """Setup structured logging for the service"""
        logging.basicConfig(
            level=logging.INFO,
            format=f'%(asctime)s - {self.service_name} - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(self.service_name)
    
    def _setup_routes(self):
        """Setup common routes for all services"""
        
        @self.app.get("/")
        def root():
            return {
                "service": self.service_name,
                "version": self.version,
                "status": "running",
                "docs": "/docs"
            }
        
        @self.app.get("/health")
        def health():
            return {"ok": True, "service": self.service_name}
        
        @self.app.get("/metrics")
        def metrics():
            return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
        
        @self.app.get("/info")
        def info():
            return {
                "service": self.service_name,
                "version": self.version,
                "environment": os.getenv("ENVIRONMENT", "development"),
                "python_version": os.sys.version
            }
    
    def get_app(self) -> FastAPI:
        """Return the FastAPI app instance"""
        return self.app
    
    def log_request(self, request: Request, response_data: dict = None):
        """Log request details for monitoring"""
        self.logger.info(
            f"Request: {request.method} {request.url.path} - "
            f"Status: {response_data.get('status', 'unknown') if response_data else 'processing'}"
        )
    
    def log_error(self, error: Exception, context: str = ""):
        """Log errors with context"""
        self.logger.error(f"Error in {context}: {str(error)}", exc_info=True)

    def get_env_var(self, key: str, default: Optional[str] = None) -> str:
        """Get environment variable with logging"""
        value = os.getenv(key, default)
        if value is None:
            self.logger.warning(f"Environment variable {key} not set, using default: {default}")
        return value
    
    def get_env_int(self, key: str, default: Optional[int] = None) -> int:
        """Get environment variable as integer, with optional default"""
        raw_default = str(default) if default is not None else None
        value = self.get_env_var(key, raw_default)

        if value is None:
            if default is None:
                raise ValueError(f"Environment variable {key} is required and has no default")
            return default

        try:
            return int(value)
        except (TypeError, ValueError):
            if default is None:
                raise ValueError(f"Invalid integer value for {key}: {value}")
            self.logger.warning(f"Invalid integer value for {key}, using default: {default}")
            return default
    
    def get_env_bool(self, key: str, default: bool = False) -> bool:
        """Get environment variable as boolean"""
        value = self.get_env_var(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')

    def log_startup(self):
        """Emit startup information for the service"""
        env_snapshot = {
            key: value
            for key, value in os.environ.items()
            if key in ENV_KEYS_TO_LOG and value is not None
        }
        self.logger.info("%s starting...", self.service_name)
        self.logger.info("ENV snapshot: %s", env_snapshot)


def log_startup(service_name: str):
    """Module-level helper to preserve backwards compatibility"""
    logger = logging.getLogger(service_name)
    env_snapshot = {
        key: value
        for key, value in os.environ.items()
        if key in ENV_KEYS_TO_LOG and value is not None
    }
    logger.info("%s starting...", service_name)
    logger.info("ENV snapshot: %s", env_snapshot)
