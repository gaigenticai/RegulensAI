"""
APM-Enhanced Decorators for RegulensAI API Routes
Automatic performance tracking, error monitoring, and business metrics collection for FastAPI routes.
"""

import asyncio
import time
import functools
from datetime import datetime
from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import structlog

from core_infra.monitoring.apm_integration import (
    apm_manager,
    track_api_response_time,
    track_error,
    track_compliance_processing_time,
    track_regulatory_data_ingestion
)
from core_infra.logging.centralized_logging import get_centralized_logger, LogCategory


logger = structlog.get_logger(__name__)


def apm_track_api(
    operation_name: Optional[str] = None,
    track_business_metrics: bool = True,
    track_database_queries: bool = True,
    track_external_calls: bool = True
):
    """
    Decorator for automatic APM tracking of API endpoints.
    
    Args:
        operation_name: Custom operation name (defaults to function name)
        track_business_metrics: Whether to track business-specific metrics
        track_database_queries: Whether to track database query performance
        track_external_calls: Whether to track external API calls
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request and response objects
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            # Get operation details
            op_name = operation_name or func.__name__
            method = request.method if request else "UNKNOWN"
            endpoint = request.url.path if request else "unknown"
            
            # Extract user context
            user_id = getattr(request.state, 'user_id', None) if request else None
            tenant_id = getattr(request.state, 'tenant_id', None) if request else None
            
            start_time = time.time()
            status_code = 200
            error_occurred = None
            
            try:
                # Track operation with APM
                async with apm_manager.track_operation(
                    op_name,
                    "api",
                    user_id=user_id,
                    tenant_id=tenant_id,
                    method=method,
                    endpoint=endpoint
                ):
                    result = await func(*args, **kwargs)
                    
                    # Extract status code from response
                    if isinstance(result, Response):
                        status_code = result.status_code
                    elif isinstance(result, JSONResponse):
                        status_code = result.status_code
                    
                    return result
                    
            except Exception as e:
                error_occurred = e
                status_code = 500
                
                # Track error
                await track_error(e, {
                    'service': 'api',
                    'operation': op_name,
                    'method': method,
                    'endpoint': endpoint,
                    'user_id': user_id,
                    'tenant_id': tenant_id
                })
                
                raise
                
            finally:
                # Calculate response time
                response_time = (time.time() - start_time) * 1000  # milliseconds
                
                # Track API response time
                await track_api_response_time(endpoint, method, response_time, status_code)
                
                # Track business metrics if enabled
                if track_business_metrics:
                    await _track_business_metrics(
                        op_name, response_time, method, endpoint, 
                        user_id, tenant_id, status_code, error_occurred
                    )
                
                # Log to centralized logging
                apm_logger = await get_centralized_logger("apm_api")
                await apm_logger.info(
                    f"API call tracked: {method} {endpoint}",
                    category=LogCategory.API,
                    operation=op_name,
                    method=method,
                    endpoint=endpoint,
                    response_time_ms=response_time,
                    status_code=status_code,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    success=error_occurred is None
                )
        
        return wrapper
    return decorator


def apm_track_compliance_operation(regulation_type: str = None):
    """
    Decorator for tracking compliance-specific operations.
    
    Args:
        regulation_type: Type of regulation being processed (e.g., 'basel_iii', 'mifid_ii')
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Extract context
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            tenant_id = getattr(request.state, 'tenant_id', None) if request else None
            reg_type = regulation_type or kwargs.get('regulation_type', 'unknown')
            
            try:
                result = await func(*args, **kwargs)
                
                # Calculate processing time
                processing_time = time.time() - start_time
                
                # Track compliance processing time
                await track_compliance_processing_time(
                    processing_time,
                    reg_type,
                    tenant_id or 'unknown'
                )
                
                return result
                
            except Exception as e:
                # Still track the processing time even on error
                processing_time = time.time() - start_time
                await track_compliance_processing_time(
                    processing_time,
                    reg_type,
                    tenant_id or 'unknown'
                )
                
                raise
        
        return wrapper
    return decorator


def apm_track_regulatory_data_operation(source: str = None):
    """
    Decorator for tracking regulatory data ingestion operations.
    
    Args:
        source: Data source identifier (e.g., 'sec', 'fca', 'ecb')
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            data_source = source or kwargs.get('source', 'unknown')
            records_processed = 0
            
            try:
                result = await func(*args, **kwargs)
                
                # Extract records processed from result
                if isinstance(result, dict):
                    records_processed = result.get('records_processed', 0)
                elif isinstance(result, (list, tuple)):
                    records_processed = len(result)
                
                # Calculate duration
                duration = time.time() - start_time
                
                # Track regulatory data ingestion
                await track_regulatory_data_ingestion(
                    records_processed,
                    data_source,
                    duration
                )
                
                return result
                
            except Exception as e:
                # Track failed ingestion
                duration = time.time() - start_time
                await track_regulatory_data_ingestion(
                    records_processed,
                    data_source,
                    duration
                )
                
                raise
        
        return wrapper
    return decorator


def apm_track_database_operation(operation_type: str = None):
    """
    Decorator for tracking database operations.
    
    Args:
        operation_type: Type of database operation (e.g., 'query', 'insert', 'update')
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            op_type = operation_type or func.__name__
            
            async with apm_manager.track_operation(
                f"db_{op_type}",
                "database",
                operation_type=op_type
            ):
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def apm_track_external_api_call(service_name: str, operation: str = None):
    """
    Decorator for tracking external API calls.
    
    Args:
        service_name: Name of the external service
        operation: Specific operation being performed
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            op_name = operation or func.__name__
            
            async with apm_manager.track_operation(
                f"{service_name}_{op_name}",
                "external_api",
                service=service_name,
                operation=op_name
            ):
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def apm_track_cache_operation(cache_type: str = "redis"):
    """
    Decorator for tracking cache operations.
    
    Args:
        cache_type: Type of cache being used
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            cache_hit = False
            
            try:
                result = await func(*args, **kwargs)
                
                # Determine if it was a cache hit
                if isinstance(result, dict) and 'cache_hit' in result:
                    cache_hit = result['cache_hit']
                elif result is not None:
                    cache_hit = True
                
                return result
                
            finally:
                duration = (time.time() - start_time) * 1000  # milliseconds
                
                # Track cache performance
                await apm_manager.track_business_metric(
                    'cache_operation_time',
                    duration,
                    cache_type=cache_type,
                    operation=func.__name__,
                    hit=str(cache_hit)
                )
        
        return wrapper
    return decorator


async def _track_business_metrics(
    operation_name: str,
    response_time: float,
    method: str,
    endpoint: str,
    user_id: Optional[str],
    tenant_id: Optional[str],
    status_code: int,
    error_occurred: Optional[Exception]
):
    """Track business-specific metrics based on operation type."""
    
    # Track user session activity
    if user_id:
        await apm_manager.track_business_metric(
            'user_api_activity',
            1,  # Count
            user_id=user_id,
            tenant_id=tenant_id or 'unknown',
            endpoint=endpoint,
            method=method
        )
    
    # Track compliance-related operations
    if any(keyword in endpoint.lower() for keyword in ['compliance', 'regulation', 'audit']):
        await apm_manager.track_business_metric(
            'compliance_api_calls',
            1,  # Count
            endpoint=endpoint,
            response_time=response_time,
            tenant_id=tenant_id or 'unknown'
        )
    
    # Track reporting operations
    if any(keyword in endpoint.lower() for keyword in ['report', 'export', 'download']):
        await apm_manager.track_business_metric(
            'reporting_operations',
            response_time,
            endpoint=endpoint,
            tenant_id=tenant_id or 'unknown',
            success=str(error_occurred is None)
        )
    
    # Track search operations
    if any(keyword in endpoint.lower() for keyword in ['search', 'query', 'filter']):
        await apm_manager.track_business_metric(
            'search_operations',
            response_time,
            endpoint=endpoint,
            tenant_id=tenant_id or 'unknown'
        )
    
    # Track authentication operations
    if any(keyword in endpoint.lower() for keyword in ['auth', 'login', 'token']):
        await apm_manager.track_business_metric(
            'authentication_operations',
            response_time,
            endpoint=endpoint,
            success=str(status_code < 400)
        )


# Middleware for automatic APM tracking
class APMMiddleware:
    """FastAPI middleware for automatic APM tracking."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Extract request information
        method = scope["method"]
        path = scope["path"]
        
        start_time = time.time()
        status_code = 200
        
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            # Track request
            response_time = (time.time() - start_time) * 1000
            await track_api_response_time(path, method, response_time, status_code)


# Context manager for tracking custom operations
class APMOperationTracker:
    """Context manager for tracking custom operations."""
    
    def __init__(self, operation_name: str, operation_type: str = "custom", **context):
        self.operation_name = operation_name
        self.operation_type = operation_type
        self.context = context
    
    async def __aenter__(self):
        self.tracker = apm_manager.track_operation(
            self.operation_name,
            self.operation_type,
            **self.context
        )
        return await self.tracker.__aenter__()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return await self.tracker.__aexit__(exc_type, exc_val, exc_tb)
