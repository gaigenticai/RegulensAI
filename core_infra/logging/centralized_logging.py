"""
RegulensAI Centralized Logging System
Enterprise-grade log aggregation with ELK stack integration, structured logging, and intelligent routing.
"""

import asyncio
import json
import time
import uuid
import logging as stdlib_logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path
import structlog
import aiofiles
import aiohttp
from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import ConnectionError, RequestError

# Internal logger for the logging module itself
internal_logger = stdlib_logging.getLogger(__name__)

from core_infra.config import get_settings
from core_infra.exceptions import SystemException


class LogLevel(str, Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(str, Enum):
    """Log category enumeration for intelligent routing."""
    APPLICATION = "application"
    SECURITY = "security"
    PERFORMANCE = "performance"
    AUDIT = "audit"
    SYSTEM = "system"
    DATABASE = "database"
    API = "api"
    COMPLIANCE = "compliance"
    BACKUP = "backup"
    MONITORING = "monitoring"


@dataclass
class LogEntry:
    """Structured log entry with comprehensive metadata."""
    timestamp: datetime
    level: LogLevel
    category: LogCategory
    service: str
    message: str
    logger_name: str
    module: str
    function: str
    line_number: int
    thread_id: str
    process_id: int
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    tags: Dict[str, str] = None
    extra_data: Dict[str, Any] = None
    stack_trace: Optional[str] = None
    duration_ms: Optional[float] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}
        if self.extra_data is None:
            self.extra_data = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary for serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['@timestamp'] = self.timestamp.isoformat()  # Elasticsearch standard
        return data
    
    def to_json(self) -> str:
        """Convert log entry to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class LogShipper:
    """
    Intelligent log shipping to multiple destinations with buffering and retry logic.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.elasticsearch_client = None
        self.buffer = []
        self.buffer_size = config.get('buffer_size', 1000)
        self.flush_interval = config.get('flush_interval', 30)  # seconds
        self.retry_attempts = config.get('retry_attempts', 3)
        self.retry_delay = config.get('retry_delay', 5)  # seconds
        
        # Initialize Elasticsearch client if configured
        if config.get('elasticsearch', {}).get('enabled', False):
            self._init_elasticsearch()
        
        # Start background flush task
        self._flush_task = None
        self.running = False
    
    def _init_elasticsearch(self):
        """Initialize Elasticsearch client."""
        es_config = self.config['elasticsearch']
        
        self.elasticsearch_client = AsyncElasticsearch(
            hosts=[{
                'host': es_config.get('host', 'localhost'),
                'port': es_config.get('port', 9200),
                'scheme': es_config.get('scheme', 'http')
            }],
            http_auth=(
                es_config.get('username'),
                es_config.get('password')
            ) if es_config.get('username') else None,
            verify_certs=es_config.get('verify_certs', False),
            ssl_show_warn=False,
            request_timeout=es_config.get('timeout', 30),
            max_retries=3,
            retry_on_timeout=True
        )
    
    async def start(self):
        """Start the log shipper."""
        self.running = True
        self._flush_task = asyncio.create_task(self._periodic_flush())
        
        # Test Elasticsearch connection
        if self.elasticsearch_client:
            await self._test_elasticsearch_connection()
    
    async def stop(self):
        """Stop the log shipper and flush remaining logs."""
        self.running = False
        
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Final flush
        await self._flush_logs()
        
        # Close Elasticsearch client
        if self.elasticsearch_client:
            await self.elasticsearch_client.close()
    
    async def ship_log(self, log_entry: LogEntry):
        """Ship a single log entry."""
        self.buffer.append(log_entry)
        
        # Flush if buffer is full
        if len(self.buffer) >= self.buffer_size:
            await self._flush_logs()
    
    async def ship_logs(self, log_entries: List[LogEntry]):
        """Ship multiple log entries."""
        self.buffer.extend(log_entries)
        
        # Flush if buffer is full
        if len(self.buffer) >= self.buffer_size:
            await self._flush_logs()
    
    async def _periodic_flush(self):
        """Periodically flush logs."""
        while self.running:
            try:
                await asyncio.sleep(self.flush_interval)
                if self.buffer:
                    await self._flush_logs()
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue running
                internal_logger.error(f"Error in periodic flush: {e}")
    
    async def _flush_logs(self):
        """Flush buffered logs to all configured destinations."""
        if not self.buffer:
            return
        
        logs_to_flush = self.buffer.copy()
        self.buffer.clear()
        
        # Ship to Elasticsearch
        if self.elasticsearch_client:
            await self._ship_to_elasticsearch(logs_to_flush)
        
        # Ship to file (always enabled as fallback)
        await self._ship_to_file(logs_to_flush)
        
        # Ship to external services (webhooks, etc.)
        await self._ship_to_external_services(logs_to_flush)
    
    async def _ship_to_elasticsearch(self, logs: List[LogEntry]):
        """Ship logs to Elasticsearch."""
        try:
            # Prepare bulk index operations
            operations = []
            
            for log_entry in logs:
                # Determine index name based on category and date
                index_name = self._get_elasticsearch_index(log_entry)
                
                # Add index operation
                operations.append({
                    "index": {
                        "_index": index_name,
                        "_id": str(uuid.uuid4())
                    }
                })
                operations.append(log_entry.to_dict())
            
            # Bulk index
            if operations:
                response = await self.elasticsearch_client.bulk(
                    operations=operations,
                    refresh=False
                )
                
                # Check for errors
                if response.get('errors'):
                    error_count = sum(1 for item in response['items'] if 'error' in item.get('index', {}))
                    internal_logger.warning(f"Elasticsearch bulk index errors: {error_count}/{len(logs)}")
        
        except Exception as e:
            internal_logger.error(f"Failed to ship logs to Elasticsearch: {e}")
            # Re-add logs to buffer for retry
            self.buffer.extend(logs)
    
    async def _ship_to_file(self, logs: List[LogEntry]):
        """Ship logs to local files."""
        try:
            log_dir = Path(self.config.get('file_output', {}).get('directory', '/var/log/regulensai'))
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Group logs by category for separate files
            logs_by_category = {}
            for log_entry in logs:
                category = log_entry.category.value
                if category not in logs_by_category:
                    logs_by_category[category] = []
                logs_by_category[category].append(log_entry)
            
            # Write to category-specific files
            for category, category_logs in logs_by_category.items():
                log_file = log_dir / f"regulensai-{category}.log"
                
                async with aiofiles.open(log_file, 'a') as f:
                    for log_entry in category_logs:
                        await f.write(log_entry.to_json() + '\n')
        
        except Exception as e:
            internal_logger.error(f"Failed to ship logs to file: {e}")
    
    async def _ship_to_external_services(self, logs: List[LogEntry]):
        """Ship logs to external services (webhooks, SIEM, etc.)."""
        external_config = self.config.get('external_services', {})
        
        # Ship to webhooks
        webhooks = external_config.get('webhooks', [])
        for webhook_config in webhooks:
            await self._ship_to_webhook(logs, webhook_config)
        
        # Ship to SIEM
        siem_config = external_config.get('siem')
        if siem_config and siem_config.get('enabled'):
            await self._ship_to_siem(logs, siem_config)
    
    async def _ship_to_webhook(self, logs: List[LogEntry], webhook_config: Dict[str, Any]):
        """Ship logs to webhook endpoint."""
        try:
            # Filter logs based on webhook configuration
            filtered_logs = self._filter_logs_for_webhook(logs, webhook_config)
            
            if not filtered_logs:
                return
            
            # Prepare payload
            payload = {
                "timestamp": datetime.utcnow().isoformat(),
                "source": "regulensai",
                "log_count": len(filtered_logs),
                "logs": [log.to_dict() for log in filtered_logs]
            }
            
            # Send to webhook
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_config['url'],
                    json=payload,
                    headers=webhook_config.get('headers', {}),
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status >= 400:
                        internal_logger.error(f"Webhook error: {response.status} - {await response.text()}")
        
        except Exception as e:
            internal_logger.error(f"Failed to ship logs to webhook: {e}")
    
    async def _ship_to_siem(self, logs: List[LogEntry], siem_config: Dict[str, Any]):
        """Ship logs to SIEM system with support for multiple SIEM platforms."""
        try:
            siem_type = siem_config.get('type', 'splunk').lower()

            if siem_type == 'splunk':
                await self._ship_to_splunk(logs, siem_config)
            elif siem_type == 'qradar':
                await self._ship_to_qradar(logs, siem_config)
            elif siem_type == 'sentinel':
                await self._ship_to_azure_sentinel(logs, siem_config)
            elif siem_type == 'elastic':
                await self._ship_to_elastic_siem(logs, siem_config)
            elif siem_type == 'sumo':
                await self._ship_to_sumo_logic(logs, siem_config)
            else:
                internal_logger.warning(f"Unsupported SIEM type: {siem_type}")

        except Exception as e:
            internal_logger.error(f"Failed to ship logs to SIEM: {e}")

    async def _ship_to_splunk(self, logs: List[LogEntry], config: Dict[str, Any]):
        """Ship logs to Splunk via HTTP Event Collector (HEC)."""
        try:
            import aiohttp

            hec_url = config.get('hec_url')
            hec_token = config.get('hec_token')
            index = config.get('index', 'regulensai')

            if not hec_url or not hec_token:
                raise ValueError("Splunk HEC URL and token are required")

            headers = {
                'Authorization': f'Splunk {hec_token}',
                'Content-Type': 'application/json'
            }

            events = []
            for log in logs:
                event = {
                    'time': log.timestamp.timestamp(),
                    'index': index,
                    'source': 'regulensai',
                    'sourcetype': f'regulensai:{log.category}',
                    'event': {
                        'level': log.level,
                        'category': log.category,
                        'message': log.message,
                        'component': log.component,
                        'service_name': log.service_name,
                        'user_id': log.user_id,
                        'session_id': log.session_id,
                        'request_id': log.request_id,
                        'correlation_id': log.correlation_id,
                        'metadata': log.metadata,
                        'structured_data': log.structured_data
                    }
                }
                events.append(event)

            async with aiohttp.ClientSession() as session:
                for event in events:
                    async with session.post(hec_url, json=event, headers=headers) as response:
                        if response.status != 200:
                            internal_logger.error(f"Splunk HEC error: {response.status} - {await response.text()}")

            internal_logger.info(f"Successfully shipped {len(events)} logs to Splunk")

        except Exception as e:
            internal_logger.error(f"Failed to ship logs to Splunk: {e}")

    async def _ship_to_qradar(self, logs: List[LogEntry], config: Dict[str, Any]):
        """Ship logs to IBM QRadar via REST API."""
        try:
            import aiohttp

            qradar_url = config.get('url')
            api_token = config.get('api_token')

            if not qradar_url or not api_token:
                raise ValueError("QRadar URL and API token are required")

            headers = {
                'SEC': api_token,
                'Content-Type': 'application/json',
                'Version': '12.0'
            }

            # Convert logs to QRadar format
            events = []
            for log in logs:
                event = {
                    'qid': 1001,  # Custom event ID for RegulensAI
                    'message': f"[{log.level}] {log.category}: {log.message}",
                    'properties': [
                        {'name': 'component', 'value': log.component},
                        {'name': 'service_name', 'value': log.service_name},
                        {'name': 'user_id', 'value': log.user_id},
                        {'name': 'correlation_id', 'value': log.correlation_id}
                    ]
                }
                events.append(event)

            async with aiohttp.ClientSession() as session:
                url = f"{qradar_url}/api/siem/events"
                async with session.post(url, json={'events': events}, headers=headers) as response:
                    if response.status not in [200, 201]:
                        internal_logger.error(f"QRadar API error: {response.status} - {await response.text()}")
                    else:
                        internal_logger.info(f"Successfully shipped {len(events)} logs to QRadar")

        except Exception as e:
            internal_logger.error(f"Failed to ship logs to QRadar: {e}")

    async def _ship_to_azure_sentinel(self, logs: List[LogEntry], config: Dict[str, Any]):
        """Ship logs to Azure Sentinel via Log Analytics API."""
        try:
            import aiohttp
            import hmac
            import hashlib
            import base64
            from datetime import datetime

            workspace_id = config.get('workspace_id')
            shared_key = config.get('shared_key')
            log_type = config.get('log_type', 'RegulensAI')

            if not workspace_id or not shared_key:
                raise ValueError("Azure Sentinel workspace ID and shared key are required")

            # Prepare log data
            log_data = []
            for log in logs:
                log_entry = {
                    'TimeGenerated': log.timestamp.isoformat(),
                    'Level': log.level,
                    'Category': log.category,
                    'Message': log.message,
                    'Component': log.component,
                    'ServiceName': log.service_name,
                    'UserId': log.user_id,
                    'SessionId': log.session_id,
                    'RequestId': log.request_id,
                    'CorrelationId': log.correlation_id,
                    'Metadata': json.dumps(log.metadata) if log.metadata else None,
                    'StructuredData': json.dumps(log.structured_data) if log.structured_data else None
                }
                log_data.append(log_entry)

            # Build signature for authentication
            body = json.dumps(log_data)
            method = 'POST'
            content_type = 'application/json'
            resource = '/api/logs'
            rfc1123date = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
            content_length = len(body)

            string_to_hash = f"{method}\n{content_length}\n{content_type}\nx-ms-date:{rfc1123date}\n{resource}"
            bytes_to_hash = bytes(string_to_hash, 'utf-8')
            decoded_key = base64.b64decode(shared_key)
            encoded_hash = base64.b64encode(hmac.new(decoded_key, bytes_to_hash, digestmod=hashlib.sha256).digest()).decode()
            authorization = f"SharedKey {workspace_id}:{encoded_hash}"

            headers = {
                'Authorization': authorization,
                'Log-Type': log_type,
                'x-ms-date': rfc1123date,
                'Content-Type': content_type
            }

            url = f"https://{workspace_id}.ods.opinsights.azure.com{resource}?api-version=2016-04-01"

            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=body, headers=headers) as response:
                    if response.status == 200:
                        internal_logger.info(f"Successfully shipped {len(log_data)} logs to Azure Sentinel")
                    else:
                        internal_logger.error(f"Azure Sentinel error: {response.status} - {await response.text()}")

        except Exception as e:
            internal_logger.error(f"Failed to ship logs to Azure Sentinel: {e}")

    async def _ship_to_elastic_siem(self, logs: List[LogEntry], config: Dict[str, Any]):
        """Ship logs to Elastic SIEM via Elasticsearch API."""
        try:
            from elasticsearch import AsyncElasticsearch

            es_hosts = config.get('hosts', ['localhost:9200'])
            username = config.get('username')
            password = config.get('password')
            index_pattern = config.get('index_pattern', 'regulensai-logs')

            # Initialize Elasticsearch client
            if username and password:
                es = AsyncElasticsearch(
                    es_hosts,
                    http_auth=(username, password),
                    verify_certs=config.get('verify_certs', True)
                )
            else:
                es = AsyncElasticsearch(es_hosts)

            # Bulk index logs
            actions = []
            for log in logs:
                doc = {
                    '@timestamp': log.timestamp.isoformat(),
                    'log': {
                        'level': log.level,
                        'logger': log.category
                    },
                    'message': log.message,
                    'service': {
                        'name': log.service_name,
                        'component': log.component
                    },
                    'user': {'id': log.user_id} if log.user_id else None,
                    'trace': {
                        'id': log.correlation_id
                    } if log.correlation_id else None,
                    'labels': log.metadata,
                    'structured_data': log.structured_data
                }

                action = {
                    '_index': f"{index_pattern}-{datetime.utcnow().strftime('%Y.%m.%d')}",
                    '_source': doc
                }
                actions.append(action)

            # Bulk index
            from elasticsearch.helpers import async_bulk
            await async_bulk(es, actions)

            internal_logger.info(f"Successfully shipped {len(actions)} logs to Elastic SIEM")
            await es.close()

        except Exception as e:
            internal_logger.error(f"Failed to ship logs to Elastic SIEM: {e}")

    async def _ship_to_sumo_logic(self, logs: List[LogEntry], config: Dict[str, Any]):
        """Ship logs to Sumo Logic via HTTP collector."""
        try:
            import aiohttp

            collector_url = config.get('collector_url')

            if not collector_url:
                raise ValueError("Sumo Logic collector URL is required")

            # Format logs for Sumo Logic
            log_lines = []
            for log in logs:
                log_line = {
                    'timestamp': log.timestamp.isoformat(),
                    'level': log.level,
                    'category': log.category,
                    'message': log.message,
                    'component': log.component,
                    'service_name': log.service_name,
                    'user_id': log.user_id,
                    'correlation_id': log.correlation_id,
                    'metadata': log.metadata,
                    'structured_data': log.structured_data
                }
                log_lines.append(json.dumps(log_line))

            body = '\n'.join(log_lines)

            headers = {
                'Content-Type': 'application/json',
                'X-Sumo-Category': 'regulensai/logs'
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(collector_url, data=body, headers=headers) as response:
                    if response.status == 200:
                        internal_logger.info(f"Successfully shipped {len(log_lines)} logs to Sumo Logic")
                    else:
                        internal_logger.error(f"Sumo Logic error: {response.status} - {await response.text()}")

        except Exception as e:
            internal_logger.error(f"Failed to ship logs to Sumo Logic: {e}")
    
    def _filter_logs_for_webhook(self, logs: List[LogEntry], webhook_config: Dict[str, Any]) -> List[LogEntry]:
        """Filter logs based on webhook configuration."""
        filters = webhook_config.get('filters', {})
        
        filtered_logs = []
        for log in logs:
            # Filter by level
            if 'min_level' in filters:
                min_level = LogLevel(filters['min_level'])
                if self._compare_log_levels(log.level, min_level) < 0:
                    continue
            
            # Filter by category
            if 'categories' in filters:
                if log.category.value not in filters['categories']:
                    continue
            
            # Filter by tags
            if 'tags' in filters:
                if not all(log.tags.get(k) == v for k, v in filters['tags'].items()):
                    continue
            
            filtered_logs.append(log)
        
        return filtered_logs
    
    def _compare_log_levels(self, level1: LogLevel, level2: LogLevel) -> int:
        """Compare log levels (-1, 0, 1)."""
        levels = [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR, LogLevel.CRITICAL]
        return levels.index(level1) - levels.index(level2)
    
    def _get_elasticsearch_index(self, log_entry: LogEntry) -> str:
        """Get Elasticsearch index name for log entry."""
        date_str = log_entry.timestamp.strftime("%Y.%m.%d")
        return f"regulensai-{log_entry.category.value}-{date_str}"
    
    async def _test_elasticsearch_connection(self):
        """Test Elasticsearch connection."""
        try:
            await self.elasticsearch_client.ping()
            internal_logger.info("Elasticsearch connection successful")
        except Exception as e:
            internal_logger.error(f"Elasticsearch connection failed: {e}")


class CentralizedLogger:
    """
    Centralized logger with intelligent routing and structured logging.
    """
    
    def __init__(self, name: str, log_shipper: LogShipper):
        self.name = name
        self.log_shipper = log_shipper
        self._context = {}
    
    def with_context(self, **kwargs) -> 'CentralizedLogger':
        """Create logger with additional context."""
        new_logger = CentralizedLogger(self.name, self.log_shipper)
        new_logger._context = {**self._context, **kwargs}
        return new_logger
    
    async def log(self, level: LogLevel, message: str, category: LogCategory = LogCategory.APPLICATION, **kwargs):
        """Log a message with specified level and category."""
        import inspect
        import threading
        import os
        
        # Get caller information
        frame = inspect.currentframe().f_back
        
        # Create log entry
        log_entry = LogEntry(
            timestamp=datetime.utcnow(),
            level=level,
            category=category,
            service="regulensai",
            message=message,
            logger_name=self.name,
            module=frame.f_globals.get('__name__', 'unknown'),
            function=frame.f_code.co_name,
            line_number=frame.f_lineno,
            thread_id=str(threading.get_ident()),
            process_id=os.getpid(),
            **{**self._context, **kwargs}
        )
        
        # Ship log
        await self.log_shipper.ship_log(log_entry)
    
    async def debug(self, message: str, **kwargs):
        """Log debug message."""
        await self.log(LogLevel.DEBUG, message, **kwargs)
    
    async def info(self, message: str, **kwargs):
        """Log info message."""
        await self.log(LogLevel.INFO, message, **kwargs)
    
    async def warning(self, message: str, **kwargs):
        """Log warning message."""
        await self.log(LogLevel.WARNING, message, **kwargs)
    
    async def error(self, message: str, **kwargs):
        """Log error message."""
        await self.log(LogLevel.ERROR, message, **kwargs)
    
    async def critical(self, message: str, **kwargs):
        """Log critical message."""
        await self.log(LogLevel.CRITICAL, message, **kwargs)
    
    async def audit(self, message: str, **kwargs):
        """Log audit message."""
        await self.log(LogLevel.INFO, message, category=LogCategory.AUDIT, **kwargs)
    
    async def security(self, message: str, level: LogLevel = LogLevel.WARNING, **kwargs):
        """Log security message."""
        await self.log(level, message, category=LogCategory.SECURITY, **kwargs)
    
    async def performance(self, message: str, duration_ms: float = None, **kwargs):
        """Log performance message."""
        await self.log(LogLevel.INFO, message, category=LogCategory.PERFORMANCE,
                      duration_ms=duration_ms, **kwargs)


class LoggingManager:
    """
    Central logging manager for RegulensAI with ELK stack integration.
    """

    def __init__(self):
        self.settings = get_settings()
        self.log_shipper = None
        self.loggers = {}
        self.running = False

        # Load logging configuration
        self.config = self._load_logging_config()

    def _load_logging_config(self) -> Dict[str, Any]:
        """Load logging configuration from settings and environment."""
        return {
            'buffer_size': getattr(self.settings, 'log_buffer_size', 1000),
            'flush_interval': getattr(self.settings, 'log_flush_interval', 30),
            'retry_attempts': getattr(self.settings, 'log_retry_attempts', 3),
            'retry_delay': getattr(self.settings, 'log_retry_delay', 5),
            'elasticsearch': {
                'enabled': getattr(self.settings, 'elasticsearch_enabled', False),
                'host': getattr(self.settings, 'elasticsearch_host', 'localhost'),
                'port': getattr(self.settings, 'elasticsearch_port', 9200),
                'scheme': getattr(self.settings, 'elasticsearch_scheme', 'http'),
                'username': getattr(self.settings, 'elasticsearch_username', None),
                'password': getattr(self.settings, 'elasticsearch_password', None),
                'verify_certs': getattr(self.settings, 'elasticsearch_verify_certs', False),
                'timeout': getattr(self.settings, 'elasticsearch_timeout', 30)
            },
            'file_output': {
                'directory': getattr(self.settings, 'log_directory', '/var/log/regulensai'),
                'enabled': getattr(self.settings, 'file_logging_enabled', True)
            },
            'external_services': {
                'webhooks': getattr(self.settings, 'log_webhooks', []),
                'siem': {
                    'enabled': getattr(self.settings, 'siem_logging_enabled', False),
                    'endpoint': getattr(self.settings, 'siem_endpoint', None),
                    'api_key': getattr(self.settings, 'siem_api_key', None)
                }
            }
        }

    async def start(self):
        """Start the logging manager."""
        if self.running:
            return

        # Initialize log shipper
        self.log_shipper = LogShipper(self.config)
        await self.log_shipper.start()

        self.running = True

        # Log startup
        logger = self.get_logger("logging_manager")
        await logger.info("Centralized logging system started",
                         elasticsearch_enabled=self.config['elasticsearch']['enabled'],
                         file_logging_enabled=self.config['file_output']['enabled'])

    async def stop(self):
        """Stop the logging manager."""
        if not self.running:
            return

        # Log shutdown
        if self.log_shipper:
            logger = self.get_logger("logging_manager")
            await logger.info("Centralized logging system stopping")

            await self.log_shipper.stop()

        self.running = False

    def get_logger(self, name: str) -> CentralizedLogger:
        """Get or create a centralized logger."""
        if name not in self.loggers:
            if not self.log_shipper:
                raise SystemException("logging_not_initialized", "Logging manager not started")

            self.loggers[name] = CentralizedLogger(name, self.log_shipper)

        return self.loggers[name]

    async def get_log_statistics(self) -> Dict[str, Any]:
        """Get logging system statistics."""
        if not self.log_shipper:
            return {"status": "not_initialized"}

        return {
            "status": "running" if self.running else "stopped",
            "buffer_size": len(self.log_shipper.buffer),
            "max_buffer_size": self.log_shipper.buffer_size,
            "elasticsearch_enabled": self.config['elasticsearch']['enabled'],
            "file_logging_enabled": self.config['file_output']['enabled'],
            "active_loggers": len(self.loggers),
            "logger_names": list(self.loggers.keys())
        }

    async def flush_logs(self):
        """Manually flush all buffered logs."""
        if self.log_shipper:
            await self.log_shipper._flush_logs()

    async def test_elasticsearch_connection(self) -> Dict[str, Any]:
        """Test Elasticsearch connection."""
        if not self.config['elasticsearch']['enabled']:
            return {"status": "disabled", "message": "Elasticsearch logging is disabled"}

        if not self.log_shipper or not self.log_shipper.elasticsearch_client:
            return {"status": "error", "message": "Elasticsearch client not initialized"}

        try:
            await self.log_shipper.elasticsearch_client.ping()

            # Get cluster info
            info = await self.log_shipper.elasticsearch_client.info()

            return {
                "status": "connected",
                "cluster_name": info.get('cluster_name'),
                "version": info.get('version', {}).get('number'),
                "message": "Elasticsearch connection successful"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Elasticsearch connection failed: {str(e)}"
            }


# Global logging manager instance
logging_manager = LoggingManager()


# Convenience functions for backward compatibility
async def get_centralized_logger(name: str) -> CentralizedLogger:
    """Get centralized logger instance."""
    return logging_manager.get_logger(name)


async def init_centralized_logging():
    """Initialize centralized logging system."""
    await logging_manager.start()


async def stop_centralized_logging():
    """Stop centralized logging system."""
    await logging_manager.stop()


# Context manager for performance logging
class PerformanceLogger:
    """Context manager for performance logging."""

    def __init__(self, logger: CentralizedLogger, operation: str, **context):
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time = None

    async def __aenter__(self):
        self.start_time = time.time()
        await self.logger.performance(f"Starting {self.operation}", **self.context)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000

        if exc_type:
            await self.logger.error(f"Failed {self.operation}",
                                   duration_ms=duration_ms,
                                   error=str(exc_val),
                                   **self.context)
        else:
            await self.logger.performance(f"Completed {self.operation}",
                                        duration_ms=duration_ms,
                                        **self.context)


# Decorator for automatic performance logging
def log_performance(operation: str = None, category: LogCategory = LogCategory.PERFORMANCE):
    """Decorator for automatic performance logging."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            logger = logging_manager.get_logger(func.__module__)
            op_name = operation or f"{func.__name__}"

            async with PerformanceLogger(logger, op_name, function=func.__name__, module=func.__module__):
                return await func(*args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            # For sync functions, we can't use async logging directly
            # This would need to be handled differently in a real implementation
            return func(*args, **kwargs)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
