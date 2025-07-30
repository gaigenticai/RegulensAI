"""
Regulens AI - Enhanced UI Portal Manager
Enterprise-grade UI portal features with session management, analytics, and user experience optimization.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import structlog

from core_infra.config import get_settings
from core_infra.database.connection import get_database
from core_infra.api.auth import get_current_user
from core_infra.performance.caching import cache_manager
from core_infra.monitoring.observability import observability_manager
from core_infra.exceptions import BusinessLogicException, DataValidationException

# Initialize logging
logger = structlog.get_logger(__name__)
settings = get_settings()

class PortalType(Enum):
    """Portal type enumeration."""
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    ANALYTICS = "analytics"
    ADMIN = "admin"

class EventType(Enum):
    """Portal event type enumeration."""
    PAGE_VIEW = "page_view"
    SEARCH = "search"
    DOWNLOAD = "download"
    TEST_EXECUTION = "test_execution"
    USER_ACTION = "user_action"
    ERROR = "error"

@dataclass
class PortalSession:
    """Portal session data structure."""
    id: str
    session_id: str
    portal_type: PortalType
    user_id: Optional[str]
    tenant_id: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    started_at: datetime
    last_activity_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    session_data: Dict[str, Any]

@dataclass
class PortalAnalytics:
    """Portal analytics data structure."""
    id: str
    tenant_id: str
    portal_type: PortalType
    event_type: EventType
    event_data: Dict[str, Any]
    session_id: Optional[str]
    user_id: Optional[str]
    page_path: Optional[str]
    duration_ms: Optional[int]
    created_at: datetime

class PortalSessionManager:
    """Advanced portal session management with analytics."""
    
    def __init__(self):
        self.session_timeout = 3600  # 1 hour
        self.cleanup_interval = 300  # 5 minutes
        self.active_sessions = {}
        
    async def initialize(self):
        """Initialize portal session manager."""
        try:
            # Start background cleanup task
            asyncio.create_task(self._cleanup_expired_sessions())
            logger.info("Portal session manager initialized")
        except Exception as e:
            logger.error(f"Portal session manager initialization failed: {e}")
            raise
    
    async def create_session(self, portal_type: PortalType, user_id: Optional[str],
                           tenant_id: str, ip_address: Optional[str] = None,
                           user_agent: Optional[str] = None) -> PortalSession:
        """Create a new portal session."""
        try:
            session_id = str(uuid.uuid4())
            now = datetime.utcnow()
            expires_at = now + timedelta(seconds=self.session_timeout)
            
            session = PortalSession(
                id=str(uuid.uuid4()),
                session_id=session_id,
                portal_type=portal_type,
                user_id=user_id,
                tenant_id=tenant_id,
                ip_address=ip_address,
                user_agent=user_agent,
                started_at=now,
                last_activity_at=now,
                expires_at=expires_at,
                is_active=True,
                session_data={}
            )
            
            # Store in database
            await self._store_session(session)
            
            # Cache session for quick access
            self.active_sessions[session_id] = session
            
            # Record analytics event
            await self._record_analytics_event(
                tenant_id=tenant_id,
                portal_type=portal_type,
                event_type=EventType.PAGE_VIEW,
                event_data={'action': 'session_created'},
                session_id=session_id,
                user_id=user_id
            )
            
            logger.info(f"Portal session created: {session_id} for {portal_type.value}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to create portal session: {e}")
            raise BusinessLogicException(f"Session creation failed: {e}")
    
    async def get_session(self, session_id: str) -> Optional[PortalSession]:
        """Get portal session by ID."""
        try:
            # Check cache first
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                if session.expires_at and session.expires_at > datetime.utcnow():
                    return session
                else:
                    # Session expired, remove from cache
                    del self.active_sessions[session_id]
            
            # Check database
            async with get_database() as db:
                row = await db.fetchrow(
                    """
                    SELECT * FROM ui_portal_sessions 
                    WHERE session_id = $1 AND is_active = true
                    AND (expires_at IS NULL OR expires_at > NOW())
                    """,
                    session_id
                )
                
                if row:
                    session = PortalSession(
                        id=str(row['id']),
                        session_id=row['session_id'],
                        portal_type=PortalType(row['portal_type']),
                        user_id=str(row['user_id']) if row['user_id'] else None,
                        tenant_id=str(row['tenant_id']),
                        ip_address=str(row['ip_address']) if row['ip_address'] else None,
                        user_agent=row['user_agent'],
                        started_at=row['started_at'],
                        last_activity_at=row['last_activity_at'],
                        expires_at=row['expires_at'],
                        is_active=row['is_active'],
                        session_data=row['session_data'] or {}
                    )
                    
                    # Cache for future access
                    self.active_sessions[session_id] = session
                    return session
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get portal session {session_id}: {e}")
            return None
    
    async def update_session_activity(self, session_id: str, 
                                    session_data: Optional[Dict[str, Any]] = None) -> bool:
        """Update session last activity and data."""
        try:
            now = datetime.utcnow()
            
            # Update in cache
            if session_id in self.active_sessions:
                self.active_sessions[session_id].last_activity_at = now
                if session_data:
                    self.active_sessions[session_id].session_data.update(session_data)
            
            # Update in database
            async with get_database() as db:
                if session_data:
                    await db.execute(
                        """
                        UPDATE ui_portal_sessions 
                        SET last_activity_at = $1, session_data = session_data || $2
                        WHERE session_id = $3
                        """,
                        now, session_data, session_id
                    )
                else:
                    await db.execute(
                        """
                        UPDATE ui_portal_sessions 
                        SET last_activity_at = $1
                        WHERE session_id = $2
                        """,
                        now, session_id
                    )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update session activity {session_id}: {e}")
            return False
    
    async def end_session(self, session_id: str) -> bool:
        """End a portal session."""
        try:
            # Remove from cache
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                
                # Record session end analytics
                await self._record_analytics_event(
                    tenant_id=session.tenant_id,
                    portal_type=session.portal_type,
                    event_type=EventType.USER_ACTION,
                    event_data={'action': 'session_ended'},
                    session_id=session_id,
                    user_id=session.user_id,
                    duration_ms=int((datetime.utcnow() - session.started_at).total_seconds() * 1000)
                )
                
                del self.active_sessions[session_id]
            
            # Update database
            async with get_database() as db:
                await db.execute(
                    """
                    UPDATE ui_portal_sessions 
                    SET is_active = false, last_activity_at = NOW()
                    WHERE session_id = $1
                    """,
                    session_id
                )
            
            logger.info(f"Portal session ended: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to end portal session {session_id}: {e}")
            return False
    
    async def _store_session(self, session: PortalSession):
        """Store session in database."""
        async with get_database() as db:
            await db.execute(
                """
                INSERT INTO ui_portal_sessions (
                    id, session_id, portal_type, user_id, tenant_id,
                    ip_address, user_agent, started_at, last_activity_at,
                    expires_at, is_active, session_data
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                uuid.UUID(session.id),
                session.session_id,
                session.portal_type.value,
                uuid.UUID(session.user_id) if session.user_id else None,
                uuid.UUID(session.tenant_id),
                session.ip_address,
                session.user_agent,
                session.started_at,
                session.last_activity_at,
                session.expires_at,
                session.is_active,
                session.session_data
            )
    
    async def _record_analytics_event(self, tenant_id: str, portal_type: PortalType,
                                    event_type: EventType, event_data: Dict[str, Any],
                                    session_id: Optional[str] = None,
                                    user_id: Optional[str] = None,
                                    page_path: Optional[str] = None,
                                    duration_ms: Optional[int] = None):
        """Record analytics event."""
        try:
            async with get_database() as db:
                await db.execute(
                    """
                    INSERT INTO ui_portal_analytics (
                        id, tenant_id, portal_type, event_type, event_data,
                        session_id, user_id, page_path, duration_ms, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                    uuid.uuid4(),
                    uuid.UUID(tenant_id),
                    portal_type.value,
                    event_type.value,
                    event_data,
                    uuid.UUID(session_id) if session_id else None,
                    uuid.UUID(user_id) if user_id else None,
                    page_path,
                    duration_ms,
                    datetime.utcnow()
                )
        except Exception as e:
            logger.error(f"Failed to record analytics event: {e}")
    
    async def _cleanup_expired_sessions(self):
        """Background task to cleanup expired sessions."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                # Remove expired sessions from cache
                now = datetime.utcnow()
                expired_sessions = [
                    session_id for session_id, session in self.active_sessions.items()
                    if session.expires_at and session.expires_at <= now
                ]
                
                for session_id in expired_sessions:
                    del self.active_sessions[session_id]
                
                # Update database
                async with get_database() as db:
                    await db.execute(
                        """
                        UPDATE ui_portal_sessions 
                        SET is_active = false 
                        WHERE expires_at <= NOW() AND is_active = true
                        """
                    )
                
                if expired_sessions:
                    logger.info(f"Cleaned up {len(expired_sessions)} expired portal sessions")
                    
            except Exception as e:
                logger.error(f"Session cleanup error: {e}")
                await asyncio.sleep(60)  # Wait longer on error

class PortalSearchManager:
    """Advanced search functionality for documentation portal."""
    
    def __init__(self):
        self.search_cache = {}
        
    async def search_documentation(self, query: str, search_type: str,
                                 filters: Dict[str, Any], session_id: str,
                                 tenant_id: str) -> Dict[str, Any]:
        """Search documentation with analytics tracking."""
        try:
            start_time = datetime.utcnow()
            
            # Generate cache key
            cache_key = f"doc_search:{hash(query)}:{hash(str(sorted(filters.items())))}"
            
            # Check cache
            cached_result = await cache_manager.get_cached_data('analytics_data', cache_key)
            if cached_result:
                results = cached_result
                execution_time_ms = 0  # Cached result
            else:
                # Perform search (placeholder implementation)
                results = await self._perform_documentation_search(query, search_type, filters)
                execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                # Cache results
                await cache_manager.set_cached_data('analytics_data', cache_key, results)
            
            # Log search
            await self._log_search(
                session_id=session_id,
                tenant_id=tenant_id,
                search_query=query,
                search_type=search_type,
                results_count=len(results.get('items', [])),
                search_filters=filters,
                execution_time_ms=execution_time_ms
            )
            
            return {
                'query': query,
                'results': results,
                'execution_time_ms': execution_time_ms,
                'total_count': len(results.get('items', []))
            }
            
        except Exception as e:
            logger.error(f"Documentation search failed: {e}")
            raise BusinessLogicException(f"Search failed: {e}")
    
    async def _perform_documentation_search(self, query: str, search_type: str,
                                          filters: Dict[str, Any]) -> Dict[str, Any]:
        """Perform actual documentation search."""
        # This would integrate with a search engine like Elasticsearch
        # For now, return mock results
        return {
            'items': [
                {
                    'id': str(uuid.uuid4()),
                    'title': f'Documentation for {query}',
                    'content': f'Sample content related to {query}',
                    'type': search_type,
                    'relevance_score': 0.95
                }
            ],
            'facets': {
                'types': {'api': 5, 'guide': 3, 'tutorial': 2},
                'categories': {'authentication': 4, 'compliance': 6}
            }
        }
    
    async def _log_search(self, session_id: str, tenant_id: str, search_query: str,
                         search_type: str, results_count: int, search_filters: Dict[str, Any],
                         execution_time_ms: int):
        """Log search query and results."""
        try:
            async with get_database() as db:
                await db.execute(
                    """
                    INSERT INTO ui_search_logs (
                        id, session_id, tenant_id, search_query, search_type,
                        results_count, search_filters, execution_time_ms, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    uuid.uuid4(),
                    uuid.UUID(session_id),
                    uuid.UUID(tenant_id),
                    search_query,
                    search_type,
                    results_count,
                    search_filters,
                    execution_time_ms,
                    datetime.utcnow()
                )
        except Exception as e:
            logger.error(f"Failed to log search: {e}")

class PortalAnalyticsManager:
    """Advanced analytics for portal usage and performance."""
    
    async def get_portal_analytics(self, tenant_id: str, portal_type: Optional[PortalType] = None,
                                 start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get comprehensive portal analytics."""
        try:
            if not start_date:
                start_date = datetime.utcnow() - timedelta(days=30)
            if not end_date:
                end_date = datetime.utcnow()
            
            async with get_database() as db:
                # Session analytics
                session_stats = await self._get_session_analytics(db, tenant_id, portal_type, start_date, end_date)
                
                # Event analytics
                event_stats = await self._get_event_analytics(db, tenant_id, portal_type, start_date, end_date)
                
                # Search analytics
                search_stats = await self._get_search_analytics(db, tenant_id, start_date, end_date)
                
                # User engagement metrics
                engagement_stats = await self._get_engagement_metrics(db, tenant_id, portal_type, start_date, end_date)
                
                return {
                    'period': {
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat()
                    },
                    'sessions': session_stats,
                    'events': event_stats,
                    'search': search_stats,
                    'engagement': engagement_stats
                }
                
        except Exception as e:
            logger.error(f"Failed to get portal analytics: {e}")
            raise BusinessLogicException(f"Analytics retrieval failed: {e}")
    
    async def _get_session_analytics(self, db, tenant_id: str, portal_type: Optional[PortalType],
                                   start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get session analytics."""
        portal_filter = "AND portal_type = $4" if portal_type else ""
        params = [uuid.UUID(tenant_id), start_date, end_date]
        if portal_type:
            params.append(portal_type.value)
        
        query = f"""
            SELECT 
                COUNT(*) as total_sessions,
                COUNT(DISTINCT user_id) as unique_users,
                AVG(EXTRACT(EPOCH FROM (last_activity_at - started_at))) as avg_session_duration,
                portal_type,
                DATE_TRUNC('day', started_at) as session_date
            FROM ui_portal_sessions
            WHERE tenant_id = $1 AND started_at >= $2 AND started_at <= $3 {portal_filter}
            GROUP BY portal_type, session_date
            ORDER BY session_date
        """
        
        results = await db.fetch(query, *params)
        return [dict(row) for row in results]
    
    async def _get_event_analytics(self, db, tenant_id: str, portal_type: Optional[PortalType],
                                 start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get event analytics."""
        portal_filter = "AND portal_type = $4" if portal_type else ""
        params = [uuid.UUID(tenant_id), start_date, end_date]
        if portal_type:
            params.append(portal_type.value)
        
        query = f"""
            SELECT 
                event_type,
                COUNT(*) as event_count,
                portal_type,
                DATE_TRUNC('day', created_at) as event_date
            FROM ui_portal_analytics
            WHERE tenant_id = $1 AND created_at >= $2 AND created_at <= $3 {portal_filter}
            GROUP BY event_type, portal_type, event_date
            ORDER BY event_date, event_count DESC
        """
        
        results = await db.fetch(query, *params)
        return [dict(row) for row in results]
    
    async def _get_search_analytics(self, db, tenant_id: str,
                                  start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get search analytics."""
        query = """
            SELECT 
                COUNT(*) as total_searches,
                AVG(results_count) as avg_results_count,
                AVG(execution_time_ms) as avg_execution_time,
                search_type,
                DATE_TRUNC('day', created_at) as search_date
            FROM ui_search_logs
            WHERE tenant_id = $1 AND created_at >= $2 AND created_at <= $3
            GROUP BY search_type, search_date
            ORDER BY search_date
        """
        
        results = await db.fetch(query, uuid.UUID(tenant_id), start_date, end_date)
        return [dict(row) for row in results]
    
    async def _get_engagement_metrics(self, db, tenant_id: str, portal_type: Optional[PortalType],
                                    start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get user engagement metrics."""
        # Build query conditions
        conditions = ["tenant_id = $1", "created_at BETWEEN $2 AND $3"]
        params = [uuid.UUID(tenant_id), start_date, end_date]
        
        if portal_type:
            conditions.append(f"portal_type = ${len(params) + 1}")
            params.append(portal_type.value)
        
        where_clause = " AND ".join(conditions)
        
        # Calculate bounce rate (sessions with only 1 page view)
        bounce_query = f"""
            SELECT 
                COUNT(DISTINCT s.id) as total_sessions,
                COUNT(DISTINCT CASE 
                    WHEN page_view_count = 1 THEN s.id 
                END) as bounced_sessions
            FROM ui_portal_sessions s
            LEFT JOIN (
                SELECT session_id, COUNT(*) as page_view_count
                FROM ui_portal_events
                WHERE event_type = 'page_view'
                GROUP BY session_id
            ) pv ON s.id = pv.session_id
            WHERE {where_clause}
        """
        
        bounce_result = await db.fetchrow(bounce_query, *params)
        total_sessions = bounce_result['total_sessions'] or 0
        bounced_sessions = bounce_result['bounced_sessions'] or 0
        bounce_rate = bounced_sessions / total_sessions if total_sessions > 0 else 0
        
        # Calculate average pages per session
        pages_query = f"""
            SELECT 
                AVG(page_count) as avg_pages_per_session
            FROM (
                SELECT 
                    s.id,
                    COUNT(DISTINCT e.event_data->>'page_path') as page_count
                FROM ui_portal_sessions s
                LEFT JOIN ui_portal_events e ON s.id = e.session_id
                WHERE {where_clause} AND e.event_type = 'page_view'
                GROUP BY s.id
            ) session_pages
        """
        
        pages_result = await db.fetchrow(pages_query, *params)
        avg_pages_per_session = float(pages_result['avg_pages_per_session'] or 0)
        
        # Calculate average time on page
        time_query = f"""
            SELECT 
                AVG(EXTRACT(EPOCH FROM (next_event_time - created_at))) as avg_time_on_page
            FROM (
                SELECT 
                    created_at,
                    LEAD(created_at) OVER (PARTITION BY session_id ORDER BY created_at) as next_event_time
                FROM ui_portal_events
                WHERE session_id IN (
                    SELECT id FROM ui_portal_sessions WHERE {where_clause}
                ) AND event_type = 'page_view'
            ) page_times
            WHERE next_event_time IS NOT NULL
        """
        
        time_result = await db.fetchrow(time_query, *params)
        avg_time_on_page = float(time_result['avg_time_on_page'] or 0)
        
        # Calculate engagement score (0-100)
        # Lower bounce rate is better, more pages per session is better, more time on page is better
        engagement_score = self._calculate_engagement_score(
            bounce_rate, avg_pages_per_session, avg_time_on_page
        )
        
        # Get most visited pages
        popular_pages_query = f"""
            SELECT 
                event_data->>'page_path' as page_path,
                COUNT(*) as visit_count
            FROM ui_portal_events e
            JOIN ui_portal_sessions s ON e.session_id = s.id
            WHERE {where_clause} AND e.event_type = 'page_view'
            GROUP BY event_data->>'page_path'
            ORDER BY visit_count DESC
            LIMIT 10
        """
        
        popular_pages = await db.fetch(popular_pages_query, *params)
        
        return {
            'bounce_rate': round(bounce_rate, 3),
            'avg_pages_per_session': round(avg_pages_per_session, 2),
            'avg_time_on_page': round(avg_time_on_page, 1),
            'engagement_score': round(engagement_score, 1),
            'total_sessions': total_sessions,
            'popular_pages': [
                {'path': page['page_path'], 'visits': page['visit_count']} 
                for page in popular_pages
            ]
        }
    
    def _calculate_engagement_score(self, bounce_rate: float, avg_pages_per_session: float, 
                                   avg_time_on_page: float) -> float:
        """Calculate overall engagement score (0-100)."""
        # Normalize each metric to 0-100 scale
        
        # Bounce rate: lower is better (invert the scale)
        bounce_score = max(0, min(100, (1 - bounce_rate) * 100))
        
        # Pages per session: 1-2 is low, 3-5 is medium, 6+ is high
        pages_score = min(100, (avg_pages_per_session / 6) * 100)
        
        # Time on page: 0-30s is low, 30-120s is medium, 120s+ is high  
        time_score = min(100, (avg_time_on_page / 120) * 100)
        
        # Weighted average (bounce rate is most important)
        engagement_score = (
            bounce_score * 0.4 +
            pages_score * 0.3 +
            time_score * 0.3
        )
        
        return engagement_score

# Global portal managers
portal_session_manager = PortalSessionManager()
portal_search_manager = PortalSearchManager()
portal_analytics_manager = PortalAnalyticsManager()

# Convenience functions
async def create_portal_session(portal_type: PortalType, user_id: Optional[str],
                              tenant_id: str, ip_address: Optional[str] = None,
                              user_agent: Optional[str] = None) -> PortalSession:
    """Convenience function for creating portal sessions."""
    return await portal_session_manager.create_session(
        portal_type, user_id, tenant_id, ip_address, user_agent
    )

async def search_documentation(query: str, search_type: str, filters: Dict[str, Any],
                             session_id: str, tenant_id: str) -> Dict[str, Any]:
    """Convenience function for documentation search."""
    return await portal_search_manager.search_documentation(
        query, search_type, filters, session_id, tenant_id
    )

async def get_portal_analytics(tenant_id: str, portal_type: Optional[PortalType] = None) -> Dict[str, Any]:
    """Convenience function for getting portal analytics."""
    return await portal_analytics_manager.get_portal_analytics(tenant_id, portal_type)
