//! Database Schema Definitions for Metrics Module
//! 
//! This module contains all database table definitions used by the metrics system
//! for storing business KPIs, compliance data, risk assessments, and operational metrics.

use sqlx::{PgPool, Row};
use crate::errors::{MetricsError, MetricsResult};

/// Database schema manager for metrics tables
pub struct MetricsSchemaManager {
    pool: PgPool,
}

impl MetricsSchemaManager {
    pub fn new(pool: PgPool) -> Self {
        Self { pool }
    }

    /// Initialize all metrics database tables
    pub async fn initialize_schema(&self) -> MetricsResult<()> {
        self.create_business_metrics_tables().await?;
        self.create_compliance_metrics_tables().await?;
        self.create_risk_metrics_tables().await?;
        self.create_fraud_metrics_tables().await?;
        self.create_operational_metrics_tables().await?;
        Ok(())
    }

    /// Create business metrics tables
    async fn create_business_metrics_tables(&self) -> MetricsResult<()> {
        // Start of table structure
        let business_kpis_sql = r#"
            -- Business KPIs Table
            -- Stores key performance indicators for business metrics tracking
            CREATE TABLE IF NOT EXISTS business_kpis (
                -- Unique identifier for each KPI record
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                -- Name of the KPI (e.g., "Total Revenue", "Customer Count")
                name VARCHAR(255) NOT NULL,
                -- Numeric value of the KPI
                value DECIMAL(20,4) NOT NULL,
                -- Unit of measurement (e.g., "USD", "count", "percentage")
                unit VARCHAR(50) NOT NULL,
                -- Target value for this KPI
                target_value DECIMAL(20,4),
                -- KPI category (REVENUE, CUSTOMER, TRANSACTION, etc.)
                category VARCHAR(100) NOT NULL,
                -- Trend direction (UP, DOWN, STABLE, VOLATILE)
                trend VARCHAR(20) NOT NULL DEFAULT 'STABLE',
                -- Timestamp when this KPI value was recorded
                recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                -- Time period this KPI represents
                period_start TIMESTAMPTZ NOT NULL,
                period_end TIMESTAMPTZ NOT NULL,
                -- Additional metadata in JSON format
                metadata JSONB,
                -- Timestamp when record was created
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                -- Timestamp when record was last updated
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            -- Indexes for efficient querying
            CREATE INDEX IF NOT EXISTS idx_business_kpis_name ON business_kpis (name);
            CREATE INDEX IF NOT EXISTS idx_business_kpis_category ON business_kpis (category);
            CREATE INDEX IF NOT EXISTS idx_business_kpis_recorded_at ON business_kpis (recorded_at);
            CREATE INDEX IF NOT EXISTS idx_business_kpis_period ON business_kpis (period_start, period_end);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_business_kpis_unique ON business_kpis (name, period_start, period_end);
        "#;
        // End of table structure

        // Start of table structure
        let business_events_sql = r#"
            -- Business Events Table
            -- Stores individual business events for metrics calculation
            CREATE TABLE IF NOT EXISTS business_events (
                -- Unique identifier for each business event
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                -- Type of business event (TRANSACTION_COMPLETED, CUSTOMER_REGISTERED, etc.)
                event_type VARCHAR(100) NOT NULL,
                -- Associated customer ID (if applicable)
                customer_id VARCHAR(255),
                -- Associated transaction ID (if applicable)
                transaction_id VARCHAR(255),
                -- Monetary amount (if applicable)
                amount DECIMAL(20,4),
                -- Currency code (if applicable)
                currency VARCHAR(3),
                -- Processing time in milliseconds
                processing_time_ms INTEGER,
                -- Additional event data in JSON format
                event_data JSONB,
                -- Timestamp when the event occurred
                event_timestamp TIMESTAMPTZ NOT NULL,
                -- Timestamp when the event was recorded in the system
                recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            -- Indexes for efficient querying and aggregation
            CREATE INDEX IF NOT EXISTS idx_business_events_type ON business_events (event_type);
            CREATE INDEX IF NOT EXISTS idx_business_events_customer ON business_events (customer_id);
            CREATE INDEX IF NOT EXISTS idx_business_events_transaction ON business_events (transaction_id);
            CREATE INDEX IF NOT EXISTS idx_business_events_timestamp ON business_events (event_timestamp);
            CREATE INDEX IF NOT EXISTS idx_business_events_amount ON business_events (amount) WHERE amount IS NOT NULL;
        "#;
        // End of table structure

        sqlx::query(business_kpis_sql)
            .execute(&self.pool)
            .await
            .map_err(|e| MetricsError::Database(e.to_string()))?;

        sqlx::query(business_events_sql)
            .execute(&self.pool)
            .await
            .map_err(|e| MetricsError::Database(e.to_string()))?;

        Ok(())
    }

    /// Create compliance metrics tables
    async fn create_compliance_metrics_tables(&self) -> MetricsResult<()> {
        // Start of table structure
        let compliance_metrics_sql = r#"
            -- Compliance Metrics Table
            -- Stores compliance scores and violation tracking
            CREATE TABLE IF NOT EXISTS compliance_metrics (
                -- Unique identifier for each compliance record
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                -- Regulation type (AML, KYC, GDPR, SOX, PCI_DSS)
                regulation VARCHAR(50) NOT NULL,
                -- Overall compliance score (0-100)
                compliance_score DECIMAL(5,2) NOT NULL,
                -- Number of compliance checks performed
                checks_performed INTEGER NOT NULL DEFAULT 0,
                -- Number of compliance checks passed
                checks_passed INTEGER NOT NULL DEFAULT 0,
                -- Number of violations detected
                violations_count INTEGER NOT NULL DEFAULT 0,
                -- Number of pending reviews
                pending_reviews INTEGER NOT NULL DEFAULT 0,
                -- Time period for these metrics
                period_start TIMESTAMPTZ NOT NULL,
                period_end TIMESTAMPTZ NOT NULL,
                -- Additional compliance data
                compliance_data JSONB,
                -- Timestamp when metrics were calculated
                calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            -- Indexes for compliance reporting
            CREATE INDEX IF NOT EXISTS idx_compliance_metrics_regulation ON compliance_metrics (regulation);
            CREATE INDEX IF NOT EXISTS idx_compliance_metrics_period ON compliance_metrics (period_start, period_end);
            CREATE INDEX IF NOT EXISTS idx_compliance_metrics_score ON compliance_metrics (compliance_score);
        "#;
        // End of table structure

        // Start of table structure
        let compliance_violations_sql = r#"
            -- Compliance Violations Table
            -- Stores detailed information about compliance violations
            CREATE TABLE IF NOT EXISTS compliance_violations (
                -- Unique identifier for each violation
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                -- Regulation that was violated
                regulation VARCHAR(50) NOT NULL,
                -- Severity level (LOW, MEDIUM, HIGH, CRITICAL)
                severity VARCHAR(20) NOT NULL,
                -- Description of the violation
                description TEXT NOT NULL,
                -- Entity that caused the violation (customer, transaction, etc.)
                entity_type VARCHAR(50),
                entity_id VARCHAR(255),
                -- Current status (OPEN, IN_REVIEW, REMEDIATED, CLOSED)
                status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
                -- Timestamp when violation was detected
                detected_at TIMESTAMPTZ NOT NULL,
                -- Timestamp when violation was remediated (if applicable)
                remediated_at TIMESTAMPTZ,
                -- User who remediated the violation
                remediated_by VARCHAR(255),
                -- Additional violation details
                violation_data JSONB,
                -- Timestamp when record was created
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                -- Timestamp when record was last updated
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            -- Indexes for violation tracking and reporting
            CREATE INDEX IF NOT EXISTS idx_compliance_violations_regulation ON compliance_violations (regulation);
            CREATE INDEX IF NOT EXISTS idx_compliance_violations_severity ON compliance_violations (severity);
            CREATE INDEX IF NOT EXISTS idx_compliance_violations_status ON compliance_violations (status);
            CREATE INDEX IF NOT EXISTS idx_compliance_violations_detected ON compliance_violations (detected_at);
            CREATE INDEX IF NOT EXISTS idx_compliance_violations_entity ON compliance_violations (entity_type, entity_id);
        "#;
        // End of table structure

        sqlx::query(compliance_metrics_sql)
            .execute(&self.pool)
            .await
            .map_err(|e| MetricsError::Database(e.to_string()))?;

        sqlx::query(compliance_violations_sql)
            .execute(&self.pool)
            .await
            .map_err(|e| MetricsError::Database(e.to_string()))?;

        Ok(())
    }

    /// Create risk metrics tables
    async fn create_risk_metrics_tables(&self) -> MetricsResult<()> {
        // Start of table structure
        let risk_assessments_sql = r#"
            -- Risk Assessments Table
            -- Stores risk assessment results for customers and transactions
            CREATE TABLE IF NOT EXISTS risk_assessments (
                -- Unique identifier for each risk assessment
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                -- Entity being assessed (customer, transaction, etc.)
                entity_type VARCHAR(50) NOT NULL,
                entity_id VARCHAR(255) NOT NULL,
                -- Overall risk score (0-100)
                risk_score DECIMAL(5,2) NOT NULL,
                -- Risk level classification (LOW, MEDIUM, HIGH, CRITICAL)
                risk_level VARCHAR(20) NOT NULL,
                -- Type of assessment (ONBOARDING, PERIODIC, TRANSACTION_BASED, EVENT_DRIVEN)
                assessment_type VARCHAR(50) NOT NULL,
                -- Individual risk factors and their scores
                risk_factors JSONB NOT NULL,
                -- Recommendations based on risk assessment
                recommendations TEXT[],
                -- User or system that performed the assessment
                assessed_by VARCHAR(255) NOT NULL,
                -- Timestamp when assessment was performed
                assessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                -- Timestamp until when this assessment is valid
                valid_until TIMESTAMPTZ NOT NULL,
                -- Current status of the assessment
                status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
            );

            -- Indexes for risk reporting and monitoring
            CREATE INDEX IF NOT EXISTS idx_risk_assessments_entity ON risk_assessments (entity_type, entity_id);
            CREATE INDEX IF NOT EXISTS idx_risk_assessments_score ON risk_assessments (risk_score);
            CREATE INDEX IF NOT EXISTS idx_risk_assessments_level ON risk_assessments (risk_level);
            CREATE INDEX IF NOT EXISTS idx_risk_assessments_assessed ON risk_assessments (assessed_at);
            CREATE INDEX IF NOT EXISTS idx_risk_assessments_valid ON risk_assessments (valid_until);
        "#;
        // End of table structure

        sqlx::query(risk_assessments_sql)
            .execute(&self.pool)
            .await
            .map_err(|e| MetricsError::Database(e.to_string()))?;

        Ok(())
    }

    /// Create fraud metrics tables
    async fn create_fraud_metrics_tables(&self) -> MetricsResult<()> {
        // Start of table structure
        let fraud_detections_sql = r#"
            -- Fraud Detections Table
            -- Stores fraud detection results and model performance data
            CREATE TABLE IF NOT EXISTS fraud_detections (
                -- Unique identifier for each fraud detection
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                -- Transaction or entity being analyzed
                entity_type VARCHAR(50) NOT NULL,
                entity_id VARCHAR(255) NOT NULL,
                -- Fraud score from ML model (0.0-1.0)
                fraud_score DECIMAL(5,4) NOT NULL,
                -- Risk level based on fraud score
                risk_level VARCHAR(20) NOT NULL,
                -- Fraud indicators detected
                fraud_indicators JSONB,
                -- Model recommendation (APPROVE, REVIEW, BLOCK)
                recommendation VARCHAR(20) NOT NULL,
                -- ML model version used for detection
                model_version VARCHAR(50) NOT NULL,
                -- Whether this was a true positive (for model training)
                true_positive BOOLEAN,
                -- Timestamp when analysis was performed
                analyzed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                -- Additional detection metadata
                detection_metadata JSONB
            );

            -- Indexes for fraud monitoring and model performance tracking
            CREATE INDEX IF NOT EXISTS idx_fraud_detections_entity ON fraud_detections (entity_type, entity_id);
            CREATE INDEX IF NOT EXISTS idx_fraud_detections_score ON fraud_detections (fraud_score);
            CREATE INDEX IF NOT EXISTS idx_fraud_detections_level ON fraud_detections (risk_level);
            CREATE INDEX IF NOT EXISTS idx_fraud_detections_recommendation ON fraud_detections (recommendation);
            CREATE INDEX IF NOT EXISTS idx_fraud_detections_analyzed ON fraud_detections (analyzed_at);
            CREATE INDEX IF NOT EXISTS idx_fraud_detections_model ON fraud_detections (model_version);
        "#;
        // End of table structure

        sqlx::query(fraud_detections_sql)
            .execute(&self.pool)
            .await
            .map_err(|e| MetricsError::Database(e.to_string()))?;

        Ok(())
    }

    /// Create operational metrics tables
    async fn create_operational_metrics_tables(&self) -> MetricsResult<()> {
        // Start of table structure
        let system_metrics_sql = r#"
            -- System Metrics Table
            -- Stores operational health and performance metrics
            CREATE TABLE IF NOT EXISTS system_metrics (
                -- Unique identifier for each metrics record
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                -- Service or system component name
                service_name VARCHAR(100) NOT NULL,
                -- Metric type (CPU, MEMORY, DISK, NETWORK, RESPONSE_TIME, etc.)
                metric_type VARCHAR(50) NOT NULL,
                -- Metric value
                metric_value DECIMAL(10,4) NOT NULL,
                -- Unit of measurement
                unit VARCHAR(20) NOT NULL,
                -- Additional metric labels/tags
                labels JSONB,
                -- Timestamp when metric was collected
                collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            -- Indexes for time-series queries and monitoring
            CREATE INDEX IF NOT EXISTS idx_system_metrics_service ON system_metrics (service_name);
            CREATE INDEX IF NOT EXISTS idx_system_metrics_type ON system_metrics (metric_type);
            CREATE INDEX IF NOT EXISTS idx_system_metrics_collected ON system_metrics (collected_at);
            CREATE INDEX IF NOT EXISTS idx_system_metrics_composite ON system_metrics (service_name, metric_type, collected_at);
        "#;
        // End of table structure

        sqlx::query(system_metrics_sql)
            .execute(&self.pool)
            .await
            .map_err(|e| MetricsError::Database(e.to_string()))?;

        Ok(())
    }

    /// Verify schema integrity
    pub async fn verify_schema(&self) -> MetricsResult<bool> {
        let tables = vec![
            "business_kpis",
            "business_events", 
            "compliance_metrics",
            "compliance_violations",
            "risk_assessments",
            "fraud_detections",
            "system_metrics"
        ];

        for table in tables {
            let exists = sqlx::query("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)")
                .bind(table)
                .fetch_one(&self.pool)
                .await
                .map_err(|e| MetricsError::Database(e.to_string()))?
                .get::<bool, _>(0);

            if !exists {
                return Ok(false);
            }
        }

        Ok(true)
    }
}
