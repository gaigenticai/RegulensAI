"""
Distributed Tracing Implementation for RegulensAI.
Provides comprehensive tracing across all services and integrations.
"""

import asyncio
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Union
from functools import wraps
from contextlib import asynccontextmanager
import structlog
from opentelemetry import trace, baggage
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.propagate import inject, extract
from opentelemetry.trace.status import Status, StatusCode

logger = structlog.get_logger(__name__)


class RegulensAITracer:
    """
    Comprehensive distributed tracing for RegulensAI platform.
    """
    
    def __init__(
        self,
        service_name: str,
        jaeger_endpoint: str = "http://jaeger-collector:14268/api/traces",
        environment: str = "production"
    ):
        self.service_name = service_name
        self.jaeger_endpoint = jaeger_endpoint
        self.environment = environment
        self.tracer = None
        
        self._initialize_tracing()
    
    def _initialize_tracing(self):
        """Initialize OpenTelemetry tracing."""
        try:
            # Create resource with service information
            resource = Resource.create({
                "service.name": self.service_name,
                "service.version": "1.0.0",
                "deployment.environment": self.environment,
                "service.namespace": "regulensai"
            })
            
            # Set up tracer provider
            trace.set_tracer_provider(TracerProvider(resource=resource))
            
            # Configure Jaeger exporter
            jaeger_exporter = JaegerExporter(
                agent_host_name="jaeger-agent",
                agent_port=6831,
                collector_endpoint=self.jaeger_endpoint,
            )
            
            # Add span processor
            span_processor = BatchSpanProcessor(jaeger_exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)
            
            # Get tracer
            self.tracer = trace.get_tracer(__name__)
            
            # Instrument common libraries
            self._instrument_libraries()
            
            logger.info(f"Distributed tracing initialized for {self.service_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize tracing: {e}")
            raise
    
    def _instrument_libraries(self):
        """Instrument common libraries for automatic tracing."""
        try:
            # Instrument HTTP clients
            HTTPXClientInstrumentor().instrument()
            
            # Instrument Redis
            RedisInstrumentor().instrument()
            
            # Instrument PostgreSQL
            Psycopg2Instrumentor().instrument()
            
            logger.info("Library instrumentation completed")
            
        except Exception as e:
            logger.warning(f"Failed to instrument some libraries: {e}")
    
    def trace_operation(
        self,
        operation_name: str,
        operation_type: str = "internal",
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """Decorator to trace operations."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self._trace_async_operation(
                    func, operation_name, operation_type, tenant_id, user_id, attributes, *args, **kwargs
                )
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self._trace_sync_operation(
                    func, operation_name, operation_type, tenant_id, user_id, attributes, *args, **kwargs
                )
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        
        return decorator
    
    async def _trace_async_operation(
        self,
        func: Callable,
        operation_name: str,
        operation_type: str,
        tenant_id: Optional[str],
        user_id: Optional[str],
        attributes: Optional[Dict[str, Any]],
        *args,
        **kwargs
    ):
        """Trace async operation."""
        with self.tracer.start_as_current_span(operation_name) as span:
            try:
                # Set span attributes
                self._set_span_attributes(span, operation_type, tenant_id, user_id, attributes)
                
                # Extract tenant_id and user_id from kwargs if not provided
                if not tenant_id:
                    tenant_id = kwargs.get('tenant_id') or self._extract_tenant_from_args(args)
                if not user_id:
                    user_id = kwargs.get('user_id') or self._extract_user_from_args(args)
                
                # Set baggage for context propagation
                if tenant_id:
                    baggage.set_baggage("tenant_id", tenant_id)
                if user_id:
                    baggage.set_baggage("user_id", user_id)
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Set success status
                span.set_status(Status(StatusCode.OK))
                
                # Add result attributes if available
                if isinstance(result, dict):
                    self._add_result_attributes(span, result)
                
                return result
                
            except Exception as e:
                # Set error status
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
    
    def _trace_sync_operation(
        self,
        func: Callable,
        operation_name: str,
        operation_type: str,
        tenant_id: Optional[str],
        user_id: Optional[str],
        attributes: Optional[Dict[str, Any]],
        *args,
        **kwargs
    ):
        """Trace sync operation."""
        with self.tracer.start_as_current_span(operation_name) as span:
            try:
                # Set span attributes
                self._set_span_attributes(span, operation_type, tenant_id, user_id, attributes)
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Set success status
                span.set_status(Status(StatusCode.OK))
                
                # Add result attributes if available
                if isinstance(result, dict):
                    self._add_result_attributes(span, result)
                
                return result
                
            except Exception as e:
                # Set error status
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
    
    def _set_span_attributes(
        self,
        span,
        operation_type: str,
        tenant_id: Optional[str],
        user_id: Optional[str],
        attributes: Optional[Dict[str, Any]]
    ):
        """Set standard span attributes."""
        span.set_attribute("operation.type", operation_type)
        span.set_attribute("service.name", self.service_name)
        span.set_attribute("service.version", "1.0.0")
        
        if tenant_id:
            span.set_attribute("tenant.id", tenant_id)
        if user_id:
            span.set_attribute("user.id", user_id)
        
        # Add custom attributes
        if attributes:
            for key, value in attributes.items():
                if isinstance(value, (str, int, float, bool)):
                    span.set_attribute(key, value)
                else:
                    span.set_attribute(key, str(value))
    
    def _add_result_attributes(self, span, result: Dict[str, Any]):
        """Add result-specific attributes to span."""
        # Add common result attributes
        if 'status' in result:
            span.set_attribute("result.status", result['status'])
        
        if 'total_processed' in result:
            span.set_attribute("result.total_processed", result['total_processed'])
        
        if 'duration_ms' in result:
            span.set_attribute("result.duration_ms", result['duration_ms'])
        
        if 'error_count' in result:
            span.set_attribute("result.error_count", result['error_count'])
    
    def _extract_tenant_from_args(self, args) -> Optional[str]:
        """Extract tenant_id from function arguments."""
        for arg in args:
            if isinstance(arg, dict) and 'tenant_id' in arg:
                return arg['tenant_id']
        return None
    
    def _extract_user_from_args(self, args) -> Optional[str]:
        """Extract user_id from function arguments."""
        for arg in args:
            if isinstance(arg, dict) and 'user_id' in arg:
                return arg['user_id']
        return None
    
    @asynccontextmanager
    async def trace_external_request(
        self,
        provider: str,
        operation: str,
        url: str,
        method: str = "GET"
    ):
        """Context manager for tracing external API requests."""
        span_name = f"{provider}.{operation}"
        
        with self.tracer.start_as_current_span(span_name) as span:
            try:
                # Set HTTP attributes
                span.set_attribute("http.method", method)
                span.set_attribute("http.url", url)
                span.set_attribute("external.provider", provider)
                span.set_attribute("external.operation", operation)
                
                # Inject trace context into headers
                headers = {}
                inject(headers)
                
                yield span, headers
                
                span.set_status(Status(StatusCode.OK))
                
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
    
    @asynccontextmanager
    async def trace_database_operation(
        self,
        operation: str,
        table: str,
        query: Optional[str] = None
    ):
        """Context manager for tracing database operations."""
        span_name = f"db.{operation}.{table}"
        
        with self.tracer.start_as_current_span(span_name) as span:
            try:
                # Set database attributes
                span.set_attribute("db.operation", operation)
                span.set_attribute("db.table", table)
                span.set_attribute("db.system", "postgresql")
                
                if query:
                    # Sanitize query for logging
                    sanitized_query = self._sanitize_query(query)
                    span.set_attribute("db.statement", sanitized_query)
                
                yield span
                
                span.set_status(Status(StatusCode.OK))
                
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
    
    @asynccontextmanager
    async def trace_cache_operation(
        self,
        operation: str,
        cache_type: str,
        key: Optional[str] = None
    ):
        """Context manager for tracing cache operations."""
        span_name = f"cache.{operation}"
        
        with self.tracer.start_as_current_span(span_name) as span:
            try:
                # Set cache attributes
                span.set_attribute("cache.operation", operation)
                span.set_attribute("cache.type", cache_type)
                
                if key:
                    # Hash the key for privacy
                    key_hash = str(hash(key))
                    span.set_attribute("cache.key_hash", key_hash)
                
                yield span
                
                span.set_status(Status(StatusCode.OK))
                
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add an event to the current span."""
        current_span = trace.get_current_span()
        if current_span:
            current_span.add_event(name, attributes or {})
    
    def set_attribute(self, key: str, value: Union[str, int, float, bool]):
        """Set an attribute on the current span."""
        current_span = trace.get_current_span()
        if current_span:
            current_span.set_attribute(key, value)
    
    def get_trace_id(self) -> Optional[str]:
        """Get the current trace ID."""
        current_span = trace.get_current_span()
        if current_span and current_span.get_span_context().is_valid:
            return format(current_span.get_span_context().trace_id, '032x')
        return None
    
    def get_span_id(self) -> Optional[str]:
        """Get the current span ID."""
        current_span = trace.get_current_span()
        if current_span and current_span.get_span_context().is_valid:
            return format(current_span.get_span_context().span_id, '016x')
        return None
    
    def _sanitize_query(self, query: str) -> str:
        """Sanitize SQL query for logging."""
        # Remove potential sensitive data from queries
        # This is a basic implementation - enhance based on your needs
        import re
        
        # Remove string literals that might contain sensitive data
        sanitized = re.sub(r"'[^']*'", "'***'", query)
        sanitized = re.sub(r'"[^"]*"', '"***"', sanitized)
        
        # Limit query length
        if len(sanitized) > 500:
            sanitized = sanitized[:500] + "..."
        
        return sanitized


# Specialized tracers for different services
class APITracer(RegulensAITracer):
    """Tracer for API service."""
    
    def __init__(self, jaeger_endpoint: str = "http://jaeger-collector:14268/api/traces"):
        super().__init__("regulensai-api", jaeger_endpoint)
    
    def trace_api_endpoint(self, endpoint: str, method: str):
        """Trace API endpoint."""
        return self.trace_operation(
            operation_name=f"{method} {endpoint}",
            operation_type="http_request",
            attributes={
                "http.method": method,
                "http.route": endpoint
            }
        )


class NotificationTracer(RegulensAITracer):
    """Tracer for notification service."""
    
    def __init__(self, jaeger_endpoint: str = "http://jaeger-collector:14268/api/traces"):
        super().__init__("regulensai-notifications", jaeger_endpoint)
    
    def trace_notification_send(self, channel: str, template: str):
        """Trace notification sending."""
        return self.trace_operation(
            operation_name=f"send_notification.{channel}",
            operation_type="notification",
            attributes={
                "notification.channel": channel,
                "notification.template": template
            }
        )


class IntegrationTracer(RegulensAITracer):
    """Tracer for integration service."""
    
    def __init__(self, jaeger_endpoint: str = "http://jaeger-collector:14268/api/traces"):
        super().__init__("regulensai-integrations", jaeger_endpoint)
    
    def trace_external_integration(self, provider: str, operation: str):
        """Trace external integration."""
        return self.trace_operation(
            operation_name=f"{provider}.{operation}",
            operation_type="external_integration",
            attributes={
                "integration.provider": provider,
                "integration.operation": operation
            }
        )
    
    def trace_grc_sync(self, system_type: str, operation: str):
        """Trace GRC sync operation."""
        return self.trace_operation(
            operation_name=f"grc_sync.{system_type}.{operation}",
            operation_type="grc_sync",
            attributes={
                "grc.system_type": system_type,
                "grc.operation": operation
            }
        )


class WorkerTracer(RegulensAITracer):
    """Tracer for worker service."""
    
    def __init__(self, jaeger_endpoint: str = "http://jaeger-collector:14268/api/traces"):
        super().__init__("regulensai-worker", jaeger_endpoint)
    
    def trace_background_task(self, task_name: str, task_type: str):
        """Trace background task."""
        return self.trace_operation(
            operation_name=f"task.{task_name}",
            operation_type="background_task",
            attributes={
                "task.name": task_name,
                "task.type": task_type
            }
        )


# Global tracer instances
api_tracer = None
notification_tracer = None
integration_tracer = None
worker_tracer = None


def initialize_tracers(jaeger_endpoint: str = "http://jaeger-collector:14268/api/traces"):
    """Initialize all tracer instances."""
    global api_tracer, notification_tracer, integration_tracer, worker_tracer
    
    try:
        api_tracer = APITracer(jaeger_endpoint)
        notification_tracer = NotificationTracer(jaeger_endpoint)
        integration_tracer = IntegrationTracer(jaeger_endpoint)
        worker_tracer = WorkerTracer(jaeger_endpoint)
        
        logger.info("All tracers initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize tracers: {e}")
        raise


def get_tracer(service_name: str) -> Optional[RegulensAITracer]:
    """Get tracer by service name."""
    tracers = {
        "api": api_tracer,
        "notifications": notification_tracer,
        "integrations": integration_tracer,
        "worker": worker_tracer
    }
    
    return tracers.get(service_name)
