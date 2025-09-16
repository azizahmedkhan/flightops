from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import os
import logging
from typing import Optional

class BaseService:
    """Base service class with common functionality for all microservices"""
    
    def __init__(self, service_name: str, version: str = "1.0.0"):
        self.service_name = service_name
        self.version = version
        self.app = FastAPI(
            title=service_name,
            version=version,
            description=f"{service_name} microservice for FlightOps"
        )
        self._setup_cors()
        self._setup_logging()
        self._setup_routes()
    
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
    
    def get_env_int(self, key: str, default: int) -> int:
        """Get environment variable as integer"""
        try:
            return int(self.get_env_var(key, str(default)))
        except ValueError:
            self.logger.warning(f"Invalid integer value for {key}, using default: {default}")
            return default
    
    def get_env_bool(self, key: str, default: bool = False) -> bool:
        """Get environment variable as boolean"""
        value = self.get_env_var(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
