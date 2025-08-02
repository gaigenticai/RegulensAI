-- RegulateAI Risk Management, Fraud Detection, Cybersecurity, and AI Services Schema
-- This migration creates tables for the remaining four services

-- =============================================================================
-- RISK MANAGEMENT SERVICE TABLES
-- =============================================================================

-- Start of table structure: risk_categories
CREATE TABLE risk_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    parent_category_id UUID REFERENCES risk_categories(id),
    risk_type VARCHAR(50) NOT NULL CHECK (risk_type IN ('CREDIT', 'MARKET', 'OPERATIONAL', 'LIQUIDITY', 'REGULATORY', 'REPUTATIONAL')),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1
);
-- End of table structure: risk_categories

-- Start of table structure: risk_assessments
CREATE TABLE risk_assessments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    risk_category_id UUID NOT NULL REFERENCES risk_categories(id),
    organization_id UUID REFERENCES organizations(id),
    assessor_id UUID NOT NULL REFERENCES users(id),
    assessment_date DATE NOT NULL,
    likelihood_score DECIMAL(3,1) NOT NULL CHECK (likelihood_score >= 1.0 AND likelihood_score <= 5.0),
    impact_score DECIMAL(3,1) NOT NULL CHECK (impact_score >= 1.0 AND impact_score <= 5.0),
    inherent_risk_score DECIMAL(4,2) GENERATED ALWAYS AS (likelihood_score * impact_score) STORED,
    control_effectiveness DECIMAL(3,1) CHECK (control_effectiveness >= 1.0 AND control_effectiveness <= 5.0),
    residual_risk_score DECIMAL(4,2),
    risk_appetite_threshold DECIMAL(4,2),
    risk_tolerance_threshold DECIMAL(4,2),
    mitigation_strategies JSONB DEFAULT '[]'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'REVIEW', 'APPROVED', 'ACTIVE', 'ARCHIVED')),
    next_review_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb
);
-- End of table structure: risk_assessments

-- Start of table structure: key_risk_indicators
CREATE TABLE key_risk_indicators (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    risk_category_id UUID NOT NULL REFERENCES risk_categories(id),
    metric_type VARCHAR(50) NOT NULL,
    calculation_method TEXT,
    data_source VARCHAR(100),
    frequency VARCHAR(20) NOT NULL CHECK (frequency IN ('REAL_TIME', 'DAILY', 'WEEKLY', 'MONTHLY', 'QUARTERLY')),
    green_threshold DECIMAL(15,4),
    amber_threshold DECIMAL(15,4),
    red_threshold DECIMAL(15,4),
    unit_of_measure VARCHAR(50),
    owner_id UUID NOT NULL REFERENCES users(id),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1
);
-- End of table structure: key_risk_indicators

-- Start of table structure: kri_measurements
CREATE TABLE kri_measurements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    kri_id UUID NOT NULL REFERENCES key_risk_indicators(id),
    measurement_date DATE NOT NULL,
    value DECIMAL(15,4) NOT NULL,
    status VARCHAR(10) NOT NULL CHECK (status IN ('GREEN', 'AMBER', 'RED')),
    notes TEXT,
    data_quality_score DECIMAL(3,2) CHECK (data_quality_score >= 0 AND data_quality_score <= 1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(kri_id, measurement_date)
);
-- End of table structure: kri_measurements

-- Start of table structure: stress_tests
CREATE TABLE stress_tests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    test_type VARCHAR(50) NOT NULL CHECK (test_type IN ('SENSITIVITY', 'SCENARIO', 'REVERSE_STRESS')),
    scenario_description TEXT,
    parameters JSONB NOT NULL,
    execution_date DATE NOT NULL,
    executor_id UUID NOT NULL REFERENCES users(id),
    monte_carlo_iterations INTEGER,
    confidence_level DECIMAL(4,3) CHECK (confidence_level > 0 AND confidence_level < 1),
    results JSONB,
    var_95 DECIMAL(20,2),
    var_99 DECIMAL(20,2),
    expected_shortfall DECIMAL(20,2),
    status VARCHAR(20) NOT NULL DEFAULT 'PLANNED' CHECK (status IN ('PLANNED', 'RUNNING', 'COMPLETED', 'FAILED')),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1
);
-- End of table structure: stress_tests

-- =============================================================================
-- FRAUD DETECTION SERVICE TABLES
-- =============================================================================

-- Start of table structure: fraud_rules
CREATE TABLE fraud_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    rule_type VARCHAR(50) NOT NULL CHECK (rule_type IN ('VELOCITY', 'AMOUNT', 'LOCATION', 'PATTERN', 'BEHAVIORAL')),
    conditions JSONB NOT NULL,
    threshold_value DECIMAL(15,4),
    threshold_operator VARCHAR(10) CHECK (threshold_operator IN ('>', '>=', '<', '<=', '=', '!=')),
    time_window_minutes INTEGER,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    action VARCHAR(50) NOT NULL CHECK (action IN ('ALERT', 'BLOCK', 'REVIEW', 'DECLINE')),
    is_active BOOLEAN NOT NULL DEFAULT true,
    false_positive_rate DECIMAL(5,4),
    true_positive_rate DECIMAL(5,4),
    last_tuned_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1
);
-- End of table structure: fraud_rules

-- Start of table structure: fraud_alerts
CREATE TABLE fraud_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_type VARCHAR(50) NOT NULL,
    customer_id UUID REFERENCES customers(id),
    transaction_id UUID REFERENCES transactions(id),
    rule_id UUID REFERENCES fraud_rules(id),
    fraud_score DECIMAL(5,2) NOT NULL CHECK (fraud_score >= 0 AND fraud_score <= 100),
    risk_factors JSONB DEFAULT '[]'::jsonb,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'INVESTIGATING', 'CONFIRMED', 'FALSE_POSITIVE', 'CLOSED')),
    assigned_to UUID REFERENCES users(id),
    investigation_notes TEXT,
    resolution TEXT,
    confirmed_loss_amount DECIMAL(20,2),
    recovery_amount DECIMAL(20,2),
    closed_at TIMESTAMPTZ,
    escalated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb
);
-- End of table structure: fraud_alerts

-- Start of table structure: ml_models
CREATE TABLE ml_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(100) NOT NULL UNIQUE,
    model_type VARCHAR(50) NOT NULL CHECK (model_type IN ('CLASSIFICATION', 'REGRESSION', 'CLUSTERING', 'ANOMALY_DETECTION')),
    algorithm VARCHAR(100) NOT NULL,
    model_version VARCHAR(20) NOT NULL,
    description TEXT,
    training_data_period DATERANGE,
    features JSONB NOT NULL,
    hyperparameters JSONB,
    performance_metrics JSONB,
    accuracy DECIMAL(5,4),
    precision_score DECIMAL(5,4),
    recall DECIMAL(5,4),
    f1_score DECIMAL(5,4),
    auc_score DECIMAL(5,4),
    model_file_path VARCHAR(500),
    status VARCHAR(20) NOT NULL DEFAULT 'TRAINING' CHECK (status IN ('TRAINING', 'TESTING', 'DEPLOYED', 'RETIRED')),
    deployed_at TIMESTAMPTZ,
    last_retrained_at TIMESTAMPTZ,
    next_retrain_due TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1
);
-- End of table structure: ml_models

-- =============================================================================
-- CYBERSECURITY SERVICE TABLES
-- =============================================================================

-- Start of table structure: vulnerabilities
CREATE TABLE vulnerabilities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cve_id VARCHAR(20),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO')),
    cvss_score DECIMAL(3,1) CHECK (cvss_score >= 0.0 AND cvss_score <= 10.0),
    cvss_vector VARCHAR(100),
    affected_systems JSONB DEFAULT '[]'::jsonb,
    asset_tags JSONB DEFAULT '[]'::jsonb,
    discovery_date DATE NOT NULL,
    disclosure_date DATE,
    patch_available BOOLEAN NOT NULL DEFAULT false,
    patch_release_date DATE,
    vendor VARCHAR(100),
    product VARCHAR(100),
    version_affected VARCHAR(100),
    exploit_available BOOLEAN NOT NULL DEFAULT false,
    exploit_maturity VARCHAR(20) CHECK (exploit_maturity IN ('UNPROVEN', 'PROOF_OF_CONCEPT', 'FUNCTIONAL', 'HIGH')),
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'ASSIGNED', 'PATCHED', 'MITIGATED', 'ACCEPTED', 'CLOSED')),
    assigned_to UUID REFERENCES users(id),
    remediation_plan TEXT,
    target_resolution_date DATE,
    actual_resolution_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1
);
-- End of table structure: vulnerabilities

-- Start of table structure: security_incidents
CREATE TABLE security_incidents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_number VARCHAR(50) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    incident_type VARCHAR(50) NOT NULL CHECK (incident_type IN ('DATA_BREACH', 'MALWARE', 'PHISHING', 'UNAUTHORIZED_ACCESS', 'DENIAL_OF_SERVICE', 'INSIDER_THREAT')),
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
    priority VARCHAR(20) NOT NULL CHECK (priority IN ('URGENT', 'HIGH', 'MEDIUM', 'LOW')),
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'INVESTIGATING', 'CONTAINED', 'RESOLVED', 'CLOSED')),
    source VARCHAR(50),
    affected_systems JSONB DEFAULT '[]'::jsonb,
    affected_users JSONB DEFAULT '[]'::jsonb,
    data_classification VARCHAR(20) CHECK (data_classification IN ('PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED')),
    estimated_impact TEXT,
    actual_impact TEXT,
    discovery_date TIMESTAMPTZ NOT NULL,
    containment_date TIMESTAMPTZ,
    resolution_date TIMESTAMPTZ,
    assigned_to UUID REFERENCES users(id),
    incident_commander UUID REFERENCES users(id),
    investigation_notes TEXT,
    lessons_learned TEXT,
    regulatory_notification_required BOOLEAN NOT NULL DEFAULT false,
    regulatory_notification_sent BOOLEAN NOT NULL DEFAULT false,
    notification_sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb
);
-- End of table structure: security_incidents

-- =============================================================================
-- AI ORCHESTRATION SERVICE TABLES
-- =============================================================================

-- Start of table structure: ai_agents
CREATE TABLE ai_agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name VARCHAR(100) NOT NULL UNIQUE,
    agent_type VARCHAR(50) NOT NULL CHECK (agent_type IN ('QA', 'MAPPING', 'HEALING', 'RECOMMENDATION', 'WORKFLOW')),
    description TEXT,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(20),
    system_prompt TEXT,
    temperature DECIMAL(3,2) CHECK (temperature >= 0.0 AND temperature <= 2.0),
    max_tokens INTEGER CHECK (max_tokens > 0),
    context_window_size INTEGER CHECK (context_window_size > 0),
    capabilities JSONB DEFAULT '[]'::jsonb,
    configuration JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT true,
    performance_metrics JSONB,
    last_performance_update TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1
);
-- End of table structure: ai_agents

-- Start of table structure: ai_conversations
CREATE TABLE ai_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES ai_agents(id),
    user_id UUID REFERENCES users(id),
    session_id VARCHAR(100),
    conversation_type VARCHAR(50) NOT NULL,
    context JSONB DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    message_count INTEGER NOT NULL DEFAULT 0,
    total_tokens_used INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'COMPLETED', 'TIMEOUT', 'ERROR')),
    metadata JSONB DEFAULT '{}'::jsonb
);
-- End of table structure: ai_conversations

-- Start of table structure: ai_messages
CREATE TABLE ai_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
    message_type VARCHAR(20) NOT NULL CHECK (message_type IN ('USER', 'ASSISTANT', 'SYSTEM')),
    content TEXT NOT NULL,
    tokens_used INTEGER,
    processing_time_ms INTEGER,
    confidence_score DECIMAL(4,3) CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    sources JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- End of table structure: ai_messages

-- Start of table structure: workflow_automations
CREATE TABLE workflow_automations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    trigger_type VARCHAR(50) NOT NULL CHECK (trigger_type IN ('SCHEDULE', 'EVENT', 'MANUAL', 'API')),
    trigger_config JSONB NOT NULL,
    workflow_steps JSONB NOT NULL,
    agent_id UUID REFERENCES ai_agents(id),
    is_active BOOLEAN NOT NULL DEFAULT true,
    success_rate DECIMAL(5,4),
    average_execution_time_ms INTEGER,
    last_execution_at TIMESTAMPTZ,
    next_execution_at TIMESTAMPTZ,
    execution_count INTEGER NOT NULL DEFAULT 0,
    failure_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1
);
-- End of table structure: workflow_automations

-- Create additional indexes for performance
CREATE INDEX idx_risk_assessments_category ON risk_assessments(risk_category_id);
CREATE INDEX idx_risk_assessments_org ON risk_assessments(organization_id);
CREATE INDEX idx_risk_assessments_date ON risk_assessments(assessment_date);
CREATE INDEX idx_kri_measurements_kri ON kri_measurements(kri_id);
CREATE INDEX idx_kri_measurements_date ON kri_measurements(measurement_date);
CREATE INDEX idx_stress_tests_date ON stress_tests(execution_date);
CREATE INDEX idx_fraud_rules_active ON fraud_rules(is_active);
CREATE INDEX idx_fraud_alerts_customer ON fraud_alerts(customer_id);
CREATE INDEX idx_fraud_alerts_status ON fraud_alerts(status);
CREATE INDEX idx_fraud_alerts_severity ON fraud_alerts(severity);
CREATE INDEX idx_ml_models_status ON ml_models(status);
CREATE INDEX idx_vulnerabilities_severity ON vulnerabilities(severity);
CREATE INDEX idx_vulnerabilities_status ON vulnerabilities(status);
CREATE INDEX idx_vulnerabilities_cve ON vulnerabilities(cve_id);
CREATE INDEX idx_security_incidents_type ON security_incidents(incident_type);
CREATE INDEX idx_security_incidents_status ON security_incidents(status);
CREATE INDEX idx_security_incidents_discovery ON security_incidents(discovery_date);
CREATE INDEX idx_ai_agents_type ON ai_agents(agent_type);
CREATE INDEX idx_ai_agents_active ON ai_agents(is_active);
CREATE INDEX idx_ai_conversations_agent ON ai_conversations(agent_id);
CREATE INDEX idx_ai_conversations_user ON ai_conversations(user_id);
CREATE INDEX idx_ai_messages_conversation ON ai_messages(conversation_id);
CREATE INDEX idx_workflow_automations_active ON workflow_automations(is_active);

-- Create triggers for updated_at timestamps
CREATE TRIGGER update_risk_categories_updated_at BEFORE UPDATE ON risk_categories FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_risk_assessments_updated_at BEFORE UPDATE ON risk_assessments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_key_risk_indicators_updated_at BEFORE UPDATE ON key_risk_indicators FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_stress_tests_updated_at BEFORE UPDATE ON stress_tests FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_fraud_rules_updated_at BEFORE UPDATE ON fraud_rules FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_fraud_alerts_updated_at BEFORE UPDATE ON fraud_alerts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_ml_models_updated_at BEFORE UPDATE ON ml_models FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_vulnerabilities_updated_at BEFORE UPDATE ON vulnerabilities FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_security_incidents_updated_at BEFORE UPDATE ON security_incidents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_ai_agents_updated_at BEFORE UPDATE ON ai_agents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_workflow_automations_updated_at BEFORE UPDATE ON workflow_automations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
