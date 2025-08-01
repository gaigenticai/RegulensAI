"""
Monitoring and observability module for RegulensAI
"""
import os
import time
from typing import Dict, Any
from prometheus_client import Counter, Histogram, generate_latest

# Metrics
request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')
database_operations = Counter('database_operations_total', 'Database operations', ['operation', 'table'])

def setup_tracing():
    """Setup distributed tracing"""
    # Basic tracing setup - can be enhanced with Jaeger/OpenTelemetry
    print("✅ Tracing setup initialized")
    return True

def get_metrics():
    """Get Prometheus metrics"""
    return generate_latest()

def record_request(method: str, endpoint: str, status: int, duration: float):
    """Record HTTP request metrics"""
    request_count.labels(method=method, endpoint=endpoint, status=status).inc()
    request_duration.observe(duration)

def record_database_operation(operation: str, table: str):
    """Record database operation metrics"""
    database_operations.labels(operation=operation, table=table).inc()

def track_operation(operation_name: str):
    """Simple operation tracking decorator"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                import structlog
                logger = structlog.get_logger(__name__)
                logger.error(f"Operation {operation_name} failed", error=str(e))
                raise
        return wrapper
    return decorator

class MetricsMiddleware:
    """Middleware to collect HTTP metrics"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.time()
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status = message["status"]
                duration = time.time() - start_time
                record_request(
                    method=scope["method"],
                    endpoint=scope["path"],
                    status=status,
                    duration=duration
                )
            await send(message)
        
        await self.app(scope, receive, send_wrapper) 