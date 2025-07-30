"""
Feature Flag Management System for RegulensAI.
Enables gradual rollout and A/B testing of new features.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import structlog
import redis.asyncio as redis
from dataclasses import dataclass, asdict

logger = structlog.get_logger(__name__)


class FeatureFlagType(Enum):
    """Types of feature flags."""
    BOOLEAN = "boolean"
    PERCENTAGE = "percentage"
    WHITELIST = "whitelist"
    EXPERIMENT = "experiment"


class FeatureFlagStatus(Enum):
    """Feature flag status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SCHEDULED = "scheduled"
    EXPIRED = "expired"


@dataclass
class FeatureFlag:
    """Feature flag configuration."""
    name: str
    type: FeatureFlagType
    status: FeatureFlagStatus
    value: Union[bool, int, List[str], Dict[str, Any]]
    description: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    tenant_whitelist: Optional[List[str]] = None
    user_whitelist: Optional[List[str]] = None
    percentage_rollout: Optional[int] = None
    experiment_config: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class FeatureFlagManager:
    """
    Manages feature flags for gradual rollout and experimentation.
    """
    
    def __init__(self, redis_client: redis.Redis, cache_ttl: int = 300):
        self.redis = redis_client
        self.cache_ttl = cache_ttl
        self.local_cache = {}
        self.cache_timestamps = {}
        
        # Default feature flags for RegulensAI components
        self.default_flags = {
            "enhanced_notifications": FeatureFlag(
                name="enhanced_notifications",
                type=FeatureFlagType.PERCENTAGE,
                status=FeatureFlagStatus.ACTIVE,
                value=True,
                description="Enhanced notification system with templates and bulk processing",
                created_by="system",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                percentage_rollout=100
            ),
            "external_data_providers": FeatureFlag(
                name="external_data_providers",
                type=FeatureFlagType.PERCENTAGE,
                status=FeatureFlagStatus.ACTIVE,
                value=True,
                description="External data provider integrations (Refinitiv, Experian, etc.)",
                created_by="system",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                percentage_rollout=100
            ),
            "grc_connectors": FeatureFlag(
                name="grc_connectors",
                type=FeatureFlagType.PERCENTAGE,
                status=FeatureFlagStatus.ACTIVE,
                value=True,
                description="GRC system connectors (Archer, ServiceNow, MetricStream)",
                created_by="system",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                percentage_rollout=100
            ),
            "advanced_analytics": FeatureFlag(
                name="advanced_analytics",
                type=FeatureFlagType.PERCENTAGE,
                status=FeatureFlagStatus.INACTIVE,
                value=False,
                description="Advanced analytics and reporting features",
                created_by="system",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                percentage_rollout=0
            ),
            "ml_risk_scoring": FeatureFlag(
                name="ml_risk_scoring",
                type=FeatureFlagType.WHITELIST,
                status=FeatureFlagStatus.INACTIVE,
                value=False,
                description="Machine learning-based risk scoring",
                created_by="system",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                tenant_whitelist=[]
            ),
            "real_time_monitoring": FeatureFlag(
                name="real_time_monitoring",
                type=FeatureFlagType.EXPERIMENT,
                status=FeatureFlagStatus.SCHEDULED,
                value=False,
                description="Real-time monitoring and alerting",
                created_by="system",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                start_date=datetime.utcnow() + timedelta(days=7),
                experiment_config={
                    "control_group": 50,
                    "treatment_group": 50,
                    "success_metrics": ["response_time", "error_rate"]
                }
            )
        }
    
    async def initialize_default_flags(self):
        """Initialize default feature flags in Redis."""
        try:
            for flag_name, flag in self.default_flags.items():
                await self.create_or_update_flag(flag)
            
            logger.info("Default feature flags initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize default feature flags: {e}")
            raise
    
    async def create_or_update_flag(self, flag: FeatureFlag) -> bool:
        """Create or update a feature flag."""
        try:
            flag.updated_at = datetime.utcnow()
            flag_data = self._serialize_flag(flag)
            
            # Store in Redis
            await self.redis.hset(
                "feature_flags",
                flag.name,
                json.dumps(flag_data)
            )
            
            # Update local cache
            self.local_cache[flag.name] = flag
            self.cache_timestamps[flag.name] = time.time()
            
            # Log flag update
            await self._log_flag_change(flag, "updated")
            
            logger.info(f"Feature flag '{flag.name}' updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update feature flag '{flag.name}': {e}")
            return False
    
    async def get_flag(self, flag_name: str) -> Optional[FeatureFlag]:
        """Get a feature flag by name."""
        try:
            # Check local cache first
            if self._is_cache_valid(flag_name):
                return self.local_cache[flag_name]
            
            # Fetch from Redis
            flag_data = await self.redis.hget("feature_flags", flag_name)
            
            if flag_data:
                flag = self._deserialize_flag(json.loads(flag_data))
                
                # Update local cache
                self.local_cache[flag_name] = flag
                self.cache_timestamps[flag_name] = time.time()
                
                return flag
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get feature flag '{flag_name}': {e}")
            return None
    
    async def is_enabled(
        self,
        flag_name: str,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if a feature flag is enabled for the given context.
        """
        try:
            flag = await self.get_flag(flag_name)
            
            if not flag:
                logger.warning(f"Feature flag '{flag_name}' not found, defaulting to False")
                return False
            
            # Check if flag is active
            if flag.status != FeatureFlagStatus.ACTIVE:
                if flag.status == FeatureFlagStatus.SCHEDULED:
                    if flag.start_date and datetime.utcnow() < flag.start_date:
                        return False
                    if flag.end_date and datetime.utcnow() > flag.end_date:
                        return False
                else:
                    return False
            
            # Check flag type and evaluate
            if flag.type == FeatureFlagType.BOOLEAN:
                return bool(flag.value)
            
            elif flag.type == FeatureFlagType.PERCENTAGE:
                if flag.percentage_rollout is None:
                    return bool(flag.value)
                
                # Use tenant_id or user_id for consistent percentage calculation
                identifier = tenant_id or user_id or "default"
                hash_value = hash(f"{flag_name}:{identifier}") % 100
                return hash_value < flag.percentage_rollout
            
            elif flag.type == FeatureFlagType.WHITELIST:
                if tenant_id and flag.tenant_whitelist:
                    return tenant_id in flag.tenant_whitelist
                if user_id and flag.user_whitelist:
                    return user_id in flag.user_whitelist
                return False
            
            elif flag.type == FeatureFlagType.EXPERIMENT:
                return await self._evaluate_experiment(flag, tenant_id, user_id, context)
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to evaluate feature flag '{flag_name}': {e}")
            return False
    
    async def get_variant(
        self,
        flag_name: str,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Get the variant for an experiment feature flag.
        """
        try:
            flag = await self.get_flag(flag_name)
            
            if not flag or flag.type != FeatureFlagType.EXPERIMENT:
                return None
            
            if not await self.is_enabled(flag_name, tenant_id, user_id, context):
                return None
            
            # Determine variant based on experiment configuration
            if flag.experiment_config:
                identifier = tenant_id or user_id or "default"
                hash_value = hash(f"{flag_name}:variant:{identifier}") % 100
                
                control_percentage = flag.experiment_config.get("control_group", 50)
                
                if hash_value < control_percentage:
                    return "control"
                else:
                    return "treatment"
            
            return "control"
            
        except Exception as e:
            logger.error(f"Failed to get variant for flag '{flag_name}': {e}")
            return None
    
    async def list_flags(self, status: Optional[FeatureFlagStatus] = None) -> List[FeatureFlag]:
        """List all feature flags, optionally filtered by status."""
        try:
            flag_data = await self.redis.hgetall("feature_flags")
            flags = []
            
            for flag_name, data in flag_data.items():
                flag = self._deserialize_flag(json.loads(data))
                
                if status is None or flag.status == status:
                    flags.append(flag)
            
            return sorted(flags, key=lambda f: f.name)
            
        except Exception as e:
            logger.error(f"Failed to list feature flags: {e}")
            return []
    
    async def delete_flag(self, flag_name: str) -> bool:
        """Delete a feature flag."""
        try:
            # Remove from Redis
            result = await self.redis.hdel("feature_flags", flag_name)
            
            # Remove from local cache
            self.local_cache.pop(flag_name, None)
            self.cache_timestamps.pop(flag_name, None)
            
            # Log flag deletion
            await self._log_flag_change(None, "deleted", flag_name)
            
            logger.info(f"Feature flag '{flag_name}' deleted successfully")
            return bool(result)
            
        except Exception as e:
            logger.error(f"Failed to delete feature flag '{flag_name}': {e}")
            return False
    
    async def update_percentage_rollout(self, flag_name: str, percentage: int) -> bool:
        """Update the percentage rollout for a feature flag."""
        try:
            if not 0 <= percentage <= 100:
                raise ValueError("Percentage must be between 0 and 100")
            
            flag = await self.get_flag(flag_name)
            if not flag:
                return False
            
            if flag.type != FeatureFlagType.PERCENTAGE:
                raise ValueError("Flag must be of type PERCENTAGE")
            
            flag.percentage_rollout = percentage
            flag.updated_at = datetime.utcnow()
            
            return await self.create_or_update_flag(flag)
            
        except Exception as e:
            logger.error(f"Failed to update percentage rollout for '{flag_name}': {e}")
            return False
    
    async def add_to_whitelist(self, flag_name: str, tenant_id: str) -> bool:
        """Add a tenant to a whitelist feature flag."""
        try:
            flag = await self.get_flag(flag_name)
            if not flag:
                return False
            
            if flag.type != FeatureFlagType.WHITELIST:
                raise ValueError("Flag must be of type WHITELIST")
            
            if flag.tenant_whitelist is None:
                flag.tenant_whitelist = []
            
            if tenant_id not in flag.tenant_whitelist:
                flag.tenant_whitelist.append(tenant_id)
                flag.updated_at = datetime.utcnow()
                
                return await self.create_or_update_flag(flag)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add tenant to whitelist for '{flag_name}': {e}")
            return False
    
    async def remove_from_whitelist(self, flag_name: str, tenant_id: str) -> bool:
        """Remove a tenant from a whitelist feature flag."""
        try:
            flag = await self.get_flag(flag_name)
            if not flag:
                return False
            
            if flag.type != FeatureFlagType.WHITELIST:
                raise ValueError("Flag must be of type WHITELIST")
            
            if flag.tenant_whitelist and tenant_id in flag.tenant_whitelist:
                flag.tenant_whitelist.remove(tenant_id)
                flag.updated_at = datetime.utcnow()
                
                return await self.create_or_update_flag(flag)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove tenant from whitelist for '{flag_name}': {e}")
            return False
    
    async def get_flag_metrics(self, flag_name: str) -> Dict[str, Any]:
        """Get metrics for a feature flag."""
        try:
            # Get flag evaluation metrics from Redis
            metrics_key = f"flag_metrics:{flag_name}"
            metrics_data = await self.redis.hgetall(metrics_key)
            
            metrics = {}
            for key, value in metrics_data.items():
                try:
                    metrics[key.decode()] = json.loads(value)
                except (json.JSONDecodeError, AttributeError):
                    metrics[key.decode()] = value.decode() if hasattr(value, 'decode') else value
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get metrics for flag '{flag_name}': {e}")
            return {}
    
    def _is_cache_valid(self, flag_name: str) -> bool:
        """Check if local cache entry is still valid."""
        if flag_name not in self.local_cache:
            return False
        
        timestamp = self.cache_timestamps.get(flag_name, 0)
        return time.time() - timestamp < self.cache_ttl
    
    def _serialize_flag(self, flag: FeatureFlag) -> Dict[str, Any]:
        """Serialize a feature flag to dictionary."""
        data = asdict(flag)
        
        # Convert datetime objects to ISO strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, Enum):
                data[key] = value.value
        
        return data
    
    def _deserialize_flag(self, data: Dict[str, Any]) -> FeatureFlag:
        """Deserialize a feature flag from dictionary."""
        # Convert ISO strings back to datetime objects
        datetime_fields = ['created_at', 'updated_at', 'start_date', 'end_date']
        for field in datetime_fields:
            if field in data and data[field]:
                data[field] = datetime.fromisoformat(data[field])
        
        # Convert enum strings back to enums
        if 'type' in data:
            data['type'] = FeatureFlagType(data['type'])
        if 'status' in data:
            data['status'] = FeatureFlagStatus(data['status'])
        
        return FeatureFlag(**data)
    
    async def _evaluate_experiment(
        self,
        flag: FeatureFlag,
        tenant_id: Optional[str],
        user_id: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> bool:
        """Evaluate an experiment feature flag."""
        if not flag.experiment_config:
            return False
        
        # Check if experiment is within date range
        now = datetime.utcnow()
        if flag.start_date and now < flag.start_date:
            return False
        if flag.end_date and now > flag.end_date:
            return False
        
        # For experiments, we consider them "enabled" if the user is in either group
        return True
    
    async def _log_flag_change(
        self,
        flag: Optional[FeatureFlag],
        action: str,
        flag_name: Optional[str] = None
    ):
        """Log feature flag changes for audit purposes."""
        try:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "action": action,
                "flag_name": flag.name if flag else flag_name,
                "flag_data": self._serialize_flag(flag) if flag else None
            }
            
            # Store in Redis for audit trail
            await self.redis.lpush(
                "flag_audit_log",
                json.dumps(log_entry)
            )
            
            # Keep only last 1000 entries
            await self.redis.ltrim("flag_audit_log", 0, 999)
            
        except Exception as e:
            logger.error(f"Failed to log flag change: {e}")


# Decorator for feature flag checks
def feature_flag_required(flag_name: str, default_value: bool = False):
    """
    Decorator to check feature flags before executing a function.
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract tenant_id from kwargs or args
            tenant_id = kwargs.get('tenant_id')
            if not tenant_id and args:
                # Try to find tenant_id in first argument if it's a dict
                if isinstance(args[0], dict) and 'tenant_id' in args[0]:
                    tenant_id = args[0]['tenant_id']
            
            # Get feature flag manager (assuming it's available in the context)
            flag_manager = kwargs.get('flag_manager')
            if not flag_manager:
                # Try to get from global context or create new instance
                # This would need to be adapted based on your application structure
                logger.warning(f"Feature flag manager not available for flag '{flag_name}'")
                if default_value:
                    return await func(*args, **kwargs)
                else:
                    return None
            
            # Check if feature is enabled
            is_enabled = await flag_manager.is_enabled(flag_name, tenant_id=tenant_id)
            
            if is_enabled:
                return await func(*args, **kwargs)
            else:
                logger.info(f"Feature '{flag_name}' is disabled for tenant {tenant_id}")
                return None
        
        return wrapper
    return decorator
