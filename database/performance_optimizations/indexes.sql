-- RegulensAI Database Performance Optimization - Indexes
-- This script creates optimized indexes based on Phase 1 performance analysis

-- ============================================================================
-- NOTIFICATION SYSTEM INDEXES
-- ============================================================================

-- Index for notification queue processing (priority + created_at)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_queue_processing 
ON notifications (priority DESC, created_at ASC) 
WHERE status IN ('pending', 'processing');

-- Index for notification delivery tracking
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_delivery_tracking 
ON notifications (tenant_id, channel, status, created_at DESC);

-- Index for notification template usage analytics
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_template_analytics 
ON notifications (template_name, created_at DESC) 
WHERE status = 'delivered';

-- Index for notification retry processing
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_retry_processing 
ON notifications (retry_count, next_retry_at) 
WHERE status = 'failed' AND retry_count < 3;

-- Partial index for failed notifications requiring attention
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_failed_attention 
ON notifications (tenant_id, created_at DESC) 
WHERE status = 'failed' AND retry_count >= 3;

-- Index for notification delivery performance metrics
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_performance_metrics 
ON notifications (channel, template_name, created_at DESC, delivery_duration_ms) 
WHERE status = 'delivered';

-- ============================================================================
-- EXTERNAL DATA INTEGRATION INDEXES
-- ============================================================================

-- Index for entity screening lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entity_screenings_lookup 
ON entity_screenings (entity_name, entity_type, tenant_id, created_at DESC);

-- Index for screening results by risk level
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entity_screenings_risk_level 
ON entity_screenings (risk_level, tenant_id, created_at DESC) 
WHERE risk_level IN ('HIGH', 'CRITICAL');

-- Index for provider performance tracking
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_external_data_requests_performance 
ON external_data_requests (provider, operation, created_at DESC, response_time_ms);

-- Index for provider error tracking
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_external_data_requests_errors 
ON external_data_requests (provider, status, created_at DESC) 
WHERE status = 'error';

-- Index for data freshness monitoring
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_external_data_cache_freshness 
ON external_data_cache (provider, data_type, last_updated DESC);

-- Index for cache hit ratio analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_external_data_cache_analytics 
ON external_data_cache (provider, cache_key_hash, hit_count, miss_count);

-- Composite index for entity screening history
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entity_screening_history 
ON entity_screenings (entity_id, tenant_id, created_at DESC);

-- ============================================================================
-- GRC INTEGRATION INDEXES
-- ============================================================================

-- Index for GRC sync operations tracking
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_grc_sync_operations_tracking 
ON grc_sync_operations (system_type, operation_type, status, created_at DESC);

-- Index for GRC data synchronization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_grc_records_sync 
ON grc_records (system_type, external_id, last_sync_at DESC);

-- Index for GRC conflict resolution
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_grc_records_conflicts 
ON grc_records (tenant_id, conflict_status, last_modified DESC) 
WHERE conflict_status IS NOT NULL;

-- Index for GRC audit trail
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_grc_audit_trail 
ON grc_audit_log (record_id, action, created_at DESC);

-- Index for GRC performance metrics
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_grc_sync_performance 
ON grc_sync_operations (system_type, operation_type, duration_ms, created_at DESC);

-- ============================================================================
-- TENANT AND USER MANAGEMENT INDEXES
-- ============================================================================

-- Index for tenant-based data access
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tenant_data_access 
ON tenant_users (tenant_id, user_id, role, is_active) 
WHERE is_active = true;

-- Index for user authentication
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_authentication 
ON users (email, is_active, last_login_at DESC) 
WHERE is_active = true;

-- Index for tenant configuration lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tenant_configurations 
ON tenant_configurations (tenant_id, config_key, is_active) 
WHERE is_active = true;

-- Index for user session management
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_sessions_active 
ON user_sessions (user_id, expires_at DESC) 
WHERE is_active = true;

-- ============================================================================
-- AUDIT AND COMPLIANCE INDEXES
-- ============================================================================

-- Index for audit log queries by tenant and date
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_tenant_date 
ON audit_logs (tenant_id, created_at DESC, action_type);

-- Index for compliance violation tracking
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_compliance_violations_tracking 
ON compliance_violations (tenant_id, severity, status, created_at DESC);

-- Index for risk assessment queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_risk_assessments_queries 
ON risk_assessments (tenant_id, risk_level, assessment_date DESC);

-- Index for regulatory reporting
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_regulatory_reports 
ON regulatory_reports (tenant_id, report_type, reporting_period, created_at DESC);

-- ============================================================================
-- FEATURE FLAGS AND CONFIGURATION INDEXES
-- ============================================================================

-- Index for feature flag evaluations
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_feature_flag_evaluations 
ON feature_flag_evaluations (flag_name, tenant_id, created_at DESC);

-- Index for active feature flags
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_feature_flags_active 
ON feature_flags (name, status, tenant_id) 
WHERE status = 'active';

-- ============================================================================
-- PERFORMANCE MONITORING INDEXES
-- ============================================================================

-- Index for API request metrics
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_api_metrics_performance 
ON api_request_metrics (endpoint, method, tenant_id, timestamp DESC, response_time_ms);

-- Index for system metrics time series
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_system_metrics_timeseries 
ON system_metrics (metric_name, timestamp DESC, value);

-- Index for error tracking and analysis
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_error_logs_analysis 
ON error_logs (service_name, error_type, tenant_id, created_at DESC);

-- ============================================================================
-- COMPOSITE INDEXES FOR COMPLEX QUERIES
-- ============================================================================

-- Composite index for notification dashboard queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_dashboard 
ON notifications (tenant_id, status, priority, created_at DESC, channel);

-- Composite index for entity screening dashboard
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entity_screening_dashboard 
ON entity_screenings (tenant_id, risk_level, screening_type, created_at DESC);

-- Composite index for GRC dashboard queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_grc_dashboard 
ON grc_records (tenant_id, record_type, status, last_modified DESC);

-- Composite index for compliance reporting
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_compliance_reporting 
ON compliance_violations (tenant_id, violation_type, severity, created_at DESC, status);

-- ============================================================================
-- PARTIAL INDEXES FOR SPECIFIC USE CASES
-- ============================================================================

-- Partial index for pending notifications only
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_pending_only 
ON notifications (tenant_id, priority DESC, created_at ASC) 
WHERE status = 'pending';

-- Partial index for high-risk entities only
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entity_screenings_high_risk_only 
ON entity_screenings (tenant_id, entity_name, created_at DESC) 
WHERE risk_level IN ('HIGH', 'CRITICAL');

-- Partial index for failed external data requests
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_external_data_failed_only 
ON external_data_requests (provider, created_at DESC, error_message) 
WHERE status = 'error';

-- Partial index for active GRC sync operations
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_grc_sync_active_only 
ON grc_sync_operations (system_type, created_at DESC) 
WHERE status IN ('running', 'pending');

-- ============================================================================
-- EXPRESSION INDEXES FOR COMPUTED VALUES
-- ============================================================================

-- Index on lowercased entity names for case-insensitive searches
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entity_screenings_name_lower 
ON entity_screenings (tenant_id, LOWER(entity_name), created_at DESC);

-- Index on notification delivery success rate calculation
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_success_rate 
ON notifications (tenant_id, channel, 
    CASE WHEN status = 'delivered' THEN 1 ELSE 0 END, 
    created_at DESC);

-- Index on GRC record age for cleanup operations
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_grc_records_age 
ON grc_records (tenant_id, 
    EXTRACT(EPOCH FROM (NOW() - created_at))/86400 AS age_days) 
WHERE EXTRACT(EPOCH FROM (NOW() - created_at))/86400 > 365;

-- ============================================================================
-- UNIQUE INDEXES FOR DATA INTEGRITY
-- ============================================================================

-- Unique index for external data cache keys
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_external_data_cache_unique 
ON external_data_cache (provider, cache_key_hash, tenant_id);

-- Unique index for GRC external IDs
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_grc_records_external_id_unique 
ON grc_records (system_type, external_id, tenant_id);

-- Unique index for user sessions
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_user_sessions_token_unique 
ON user_sessions (session_token) 
WHERE is_active = true;

-- ============================================================================
-- COVERING INDEXES FOR READ-HEAVY QUERIES
-- ============================================================================

-- Covering index for notification list queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_list_covering 
ON notifications (tenant_id, created_at DESC) 
INCLUDE (id, template_name, channel, status, priority, recipient_email);

-- Covering index for entity screening list queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entity_screenings_list_covering 
ON entity_screenings (tenant_id, created_at DESC) 
INCLUDE (id, entity_name, entity_type, risk_level, screening_type, overall_score);

-- Covering index for GRC record list queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_grc_records_list_covering 
ON grc_records (tenant_id, last_modified DESC) 
INCLUDE (id, record_type, title, status, risk_level, owner);

-- ============================================================================
-- MAINTENANCE COMMANDS
-- ============================================================================

-- Analyze tables to update statistics after index creation
ANALYZE notifications;
ANALYZE entity_screenings;
ANALYZE external_data_requests;
ANALYZE external_data_cache;
ANALYZE grc_sync_operations;
ANALYZE grc_records;
ANALYZE tenant_users;
ANALYZE users;
ANALYZE audit_logs;
ANALYZE compliance_violations;
ANALYZE risk_assessments;
ANALYZE feature_flags;
ANALYZE api_request_metrics;
ANALYZE system_metrics;

-- ============================================================================
-- INDEX MONITORING QUERIES
-- ============================================================================

-- Query to monitor index usage
/*
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch,
    idx_scan
FROM pg_stat_user_indexes 
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
*/

-- Query to find unused indexes
/*
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_stat_user_indexes 
WHERE idx_scan = 0 
    AND schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;
*/

-- Query to monitor index bloat
/*
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as size,
    CASE 
        WHEN pg_relation_size(indexrelid) > 100 * 1024 * 1024 
        THEN 'Consider REINDEX'
        ELSE 'OK'
    END as recommendation
FROM pg_stat_user_indexes 
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;
*/
