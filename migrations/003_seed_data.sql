-- RegulateAI Seed Data
-- This migration inserts initial system data required for the application to function

-- Insert system roles
INSERT INTO roles (id, name, description, is_system_role, permissions) VALUES
    ('00000000-0000-0000-0000-000000000001', 'super_admin', 'Super Administrator with full system access', true, '["*"]'::jsonb),
    ('00000000-0000-0000-0000-000000000002', 'admin', 'System Administrator', true, '["admin", "read", "write", "delete"]'::jsonb),
    ('00000000-0000-0000-0000-000000000003', 'compliance_officer', 'Compliance Officer', true, '["compliance:*", "audit:*", "read", "write"]'::jsonb),
    ('00000000-0000-0000-0000-000000000004', 'risk_manager', 'Risk Manager', true, '["risk:*", "read", "write"]'::jsonb),
    ('00000000-0000-0000-0000-000000000005', 'analyst', 'Analyst', true, '["read", "write", "analyze"]'::jsonb),
    ('00000000-0000-0000-0000-000000000006', 'auditor', 'Auditor', true, '["audit", "read"]'::jsonb),
    ('00000000-0000-0000-0000-000000000007', 'user', 'Standard User', true, '["read"]'::jsonb),
    ('00000000-0000-0000-0000-000000000008', 'readonly', 'Read-only User', true, '["read"]'::jsonb);

-- Insert default system user
INSERT INTO users (id, email, username, password_hash, first_name, last_name, is_active, is_verified) VALUES
    ('00000000-0000-0000-0000-000000000001', 'admin@regulateai.com', 'admin', '$argon2id$v=19$m=65536,t=3,p=4$randomsalthere$hashedpasswordhere', 'System', 'Administrator', true, true);

-- Assign super_admin role to system user
INSERT INTO user_roles (user_id, role_id, granted_by) VALUES
    ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001');

-- Insert risk categories
INSERT INTO risk_categories (id, name, description, risk_type) VALUES
    ('10000000-0000-0000-0000-000000000001', 'Credit Risk', 'Risk of financial loss due to counterparty default', 'CREDIT'),
    ('10000000-0000-0000-0000-000000000002', 'Market Risk', 'Risk of losses due to market movements', 'MARKET'),
    ('10000000-0000-0000-0000-000000000003', 'Operational Risk', 'Risk of loss from inadequate or failed processes', 'OPERATIONAL'),
    ('10000000-0000-0000-0000-000000000004', 'Liquidity Risk', 'Risk of inability to meet financial obligations', 'LIQUIDITY'),
    ('10000000-0000-0000-0000-000000000005', 'Regulatory Risk', 'Risk of regulatory non-compliance', 'REGULATORY'),
    ('10000000-0000-0000-0000-000000000006', 'Reputational Risk', 'Risk of damage to reputation', 'REPUTATIONAL'),
    ('10000000-0000-0000-0000-000000000007', 'Concentration Risk', 'Risk from lack of diversification', 'CREDIT'),
    ('10000000-0000-0000-0000-000000000008', 'Interest Rate Risk', 'Risk from interest rate changes', 'MARKET'),
    ('10000000-0000-0000-0000-000000000009', 'Foreign Exchange Risk', 'Risk from currency fluctuations', 'MARKET'),
    ('10000000-0000-0000-0000-000000000010', 'Technology Risk', 'Risk from technology failures', 'OPERATIONAL');

-- Insert default fraud rules
INSERT INTO fraud_rules (id, rule_name, description, rule_type, conditions, threshold_value, threshold_operator, time_window_minutes, severity, action) VALUES
    ('20000000-0000-0000-0000-000000000001', 'High Value Transaction', 'Alert on transactions above threshold', 'AMOUNT', '{"field": "amount", "currency": "USD"}'::jsonb, 10000.00, '>', NULL, 'MEDIUM', 'ALERT'),
    ('20000000-0000-0000-0000-000000000002', 'Velocity Check - Daily', 'Alert on high transaction velocity per day', 'VELOCITY', '{"field": "transaction_count", "period": "daily"}'::jsonb, 50.00, '>', 1440, 'HIGH', 'REVIEW'),
    ('20000000-0000-0000-0000-000000000003', 'Round Amount Pattern', 'Detect round amount transactions', 'PATTERN', '{"field": "amount", "pattern": "round_numbers"}'::jsonb, NULL, NULL, NULL, 'LOW', 'ALERT'),
    ('20000000-0000-0000-0000-000000000004', 'Geographic Anomaly', 'Detect transactions from unusual locations', 'LOCATION', '{"field": "location", "check": "historical_pattern"}'::jsonb, NULL, NULL, NULL, 'MEDIUM', 'REVIEW'),
    ('20000000-0000-0000-0000-000000000005', 'Structuring Pattern', 'Detect potential structuring behavior', 'BEHAVIORAL', '{"field": "amount", "pattern": "just_under_threshold"}'::jsonb, 9999.99, '<', 1440, 'HIGH', 'ALERT');

-- Insert default AI agents
INSERT INTO ai_agents (id, agent_name, agent_type, description, model_name, model_version, system_prompt, temperature, max_tokens, context_window_size, capabilities) VALUES
    ('30000000-0000-0000-0000-000000000001', 'Regulatory QA Agent', 'QA', 'Answers regulatory compliance questions', 'gpt-4', '1.0', 'You are a regulatory compliance expert. Provide accurate, detailed answers about financial regulations, compliance requirements, and best practices.', 0.1, 4096, 8192, '["regulatory_qa", "compliance_guidance", "policy_interpretation"]'::jsonb),
    ('30000000-0000-0000-0000-000000000002', 'Control Mapping Agent', 'MAPPING', 'Maps regulatory requirements to controls', 'gpt-4', '1.0', 'You are an expert in mapping regulatory requirements to internal controls. Analyze requirements and suggest appropriate controls.', 0.2, 2048, 4096, '["requirement_analysis", "control_mapping", "gap_analysis"]'::jsonb),
    ('30000000-0000-0000-0000-000000000003', 'Self-Healing Agent', 'HEALING', 'Automatically remediates control failures', 'gpt-4', '1.0', 'You are an automated remediation expert. Analyze control failures and implement appropriate fixes.', 0.1, 1024, 2048, '["failure_analysis", "automated_remediation", "system_healing"]'::jsonb),
    ('30000000-0000-0000-0000-000000000004', 'Risk Assessment Agent', 'RECOMMENDATION', 'Provides risk assessment recommendations', 'gpt-4', '1.0', 'You are a risk assessment expert. Analyze risk scenarios and provide actionable recommendations.', 0.2, 3072, 6144, '["risk_analysis", "recommendation_generation", "scenario_planning"]'::jsonb),
    ('30000000-0000-0000-0000-000000000005', 'Workflow Orchestrator', 'WORKFLOW', 'Orchestrates complex compliance workflows', 'gpt-4', '1.0', 'You are a workflow orchestration expert. Design and execute complex compliance and risk management workflows.', 0.1, 2048, 4096, '["workflow_design", "process_automation", "task_coordination"]'::jsonb);

-- Insert default policies
INSERT INTO policies (id, title, description, policy_type, framework, content, version_number, status, effective_date, owner_id) VALUES
    ('40000000-0000-0000-0000-000000000001', 'Anti-Money Laundering Policy', 'Comprehensive AML policy covering customer due diligence, transaction monitoring, and reporting', 'AML', 'BSA', 'This policy establishes the framework for preventing money laundering and terrorist financing...', '1.0', 'ACTIVE', CURRENT_DATE, '00000000-0000-0000-0000-000000000001'),
    ('40000000-0000-0000-0000-000000000002', 'Information Security Policy', 'Information security policy covering data protection, access controls, and incident response', 'SECURITY', 'ISO27001', 'This policy establishes the framework for protecting information assets...', '1.0', 'ACTIVE', CURRENT_DATE, '00000000-0000-0000-0000-000000000001'),
    ('40000000-0000-0000-0000-000000000003', 'Risk Management Policy', 'Enterprise risk management policy covering risk identification, assessment, and mitigation', 'RISK', 'COSO', 'This policy establishes the framework for enterprise risk management...', '1.0', 'ACTIVE', CURRENT_DATE, '00000000-0000-0000-0000-000000000001'),
    ('40000000-0000-0000-0000-000000000004', 'Data Privacy Policy', 'Data privacy policy covering personal data protection and GDPR compliance', 'PRIVACY', 'GDPR', 'This policy establishes the framework for protecting personal data...', '1.0', 'ACTIVE', CURRENT_DATE, '00000000-0000-0000-0000-000000000001'),
    ('40000000-0000-0000-0000-000000000005', 'Business Continuity Policy', 'Business continuity and disaster recovery policy', 'CONTINUITY', 'ISO22301', 'This policy establishes the framework for business continuity management...', '1.0', 'ACTIVE', CURRENT_DATE, '00000000-0000-0000-0000-000000000001');

-- Insert default controls
INSERT INTO controls (id, control_id, title, description, control_type, control_category, framework, policy_id, owner_id, frequency, automation_level, risk_rating, status) VALUES
    ('50000000-0000-0000-0000-000000000001', 'AML-001', 'Customer Due Diligence', 'Perform enhanced due diligence on high-risk customers', 'PREVENTIVE', 'AML', 'BSA', '40000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 'CONTINUOUS', 'SEMI_AUTOMATED', 'HIGH', 'ACTIVE'),
    ('50000000-0000-0000-0000-000000000002', 'AML-002', 'Transaction Monitoring', 'Monitor transactions for suspicious patterns', 'DETECTIVE', 'AML', 'BSA', '40000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 'CONTINUOUS', 'FULLY_AUTOMATED', 'CRITICAL', 'ACTIVE'),
    ('50000000-0000-0000-0000-000000000003', 'SEC-001', 'Access Control Review', 'Review user access rights quarterly', 'DETECTIVE', 'SECURITY', 'ISO27001', '40000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000001', 'QUARTERLY', 'MANUAL', 'HIGH', 'ACTIVE'),
    ('50000000-0000-0000-0000-000000000004', 'SEC-002', 'Vulnerability Scanning', 'Perform automated vulnerability scans', 'DETECTIVE', 'SECURITY', 'ISO27001', '40000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000001', 'WEEKLY', 'FULLY_AUTOMATED', 'HIGH', 'ACTIVE'),
    ('50000000-0000-0000-0000-000000000005', 'RISK-001', 'Risk Assessment', 'Conduct annual enterprise risk assessment', 'DETECTIVE', 'RISK', 'COSO', '40000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000001', 'ANNUALLY', 'MANUAL', 'CRITICAL', 'ACTIVE');

-- Insert sample Key Risk Indicators
INSERT INTO key_risk_indicators (id, name, description, risk_category_id, metric_type, frequency, green_threshold, amber_threshold, red_threshold, unit_of_measure, owner_id) VALUES
    ('60000000-0000-0000-0000-000000000001', 'Credit Loss Rate', 'Percentage of credit losses to total credit exposure', '10000000-0000-0000-0000-000000000001', 'PERCENTAGE', 'MONTHLY', 1.0, 2.5, 5.0, 'Percentage', '00000000-0000-0000-0000-000000000001'),
    ('60000000-0000-0000-0000-000000000002', 'VaR Utilization', 'Value at Risk as percentage of risk appetite', '10000000-0000-0000-0000-000000000002', 'PERCENTAGE', 'DAILY', 70.0, 85.0, 95.0, 'Percentage', '00000000-0000-0000-0000-000000000001'),
    ('60000000-0000-0000-0000-000000000003', 'Operational Loss Frequency', 'Number of operational loss events per month', '10000000-0000-0000-0000-000000000003', 'COUNT', 'MONTHLY', 5.0, 10.0, 20.0, 'Count', '00000000-0000-0000-0000-000000000001'),
    ('60000000-0000-0000-0000-000000000004', 'Liquidity Coverage Ratio', 'LCR as percentage of regulatory minimum', '10000000-0000-0000-0000-000000000004', 'RATIO', 'DAILY', 120.0, 110.0, 100.0, 'Percentage', '00000000-0000-0000-0000-000000000001'),
    ('60000000-0000-0000-0000-000000000005', 'Regulatory Breach Count', 'Number of regulatory breaches per quarter', '10000000-0000-0000-0000-000000000005', 'COUNT', 'QUARTERLY', 0.0, 1.0, 3.0, 'Count', '00000000-0000-0000-0000-000000000001');

-- Insert sample workflow automations
INSERT INTO workflow_automations (id, workflow_name, description, trigger_type, trigger_config, workflow_steps, agent_id) VALUES
    ('70000000-0000-0000-0000-000000000001', 'AML Alert Investigation', 'Automated workflow for investigating AML alerts', 'EVENT', '{"event_type": "aml_alert_created", "severity": ["HIGH", "CRITICAL"]}'::jsonb, '[{"step": "gather_context", "agent": "regulatory_qa"}, {"step": "analyze_risk", "agent": "risk_assessment"}, {"step": "recommend_action", "agent": "recommendation"}]'::jsonb, '30000000-0000-0000-0000-000000000001'),
    ('70000000-0000-0000-0000-000000000002', 'Control Failure Remediation', 'Automated workflow for control failure remediation', 'EVENT', '{"event_type": "control_test_failed", "control_type": ["CRITICAL", "HIGH"]}'::jsonb, '[{"step": "analyze_failure", "agent": "control_mapping"}, {"step": "implement_fix", "agent": "self_healing"}, {"step": "verify_fix", "agent": "workflow_orchestrator"}]'::jsonb, '30000000-0000-0000-0000-000000000003'),
    ('70000000-0000-0000-0000-000000000003', 'Risk Assessment Review', 'Automated workflow for risk assessment reviews', 'SCHEDULE', '{"schedule": "0 0 1 * *", "timezone": "UTC"}'::jsonb, '[{"step": "gather_data", "agent": "workflow_orchestrator"}, {"step": "analyze_trends", "agent": "risk_assessment"}, {"step": "generate_report", "agent": "recommendation"}]'::jsonb, '30000000-0000-0000-0000-000000000004'),
    ('70000000-0000-0000-0000-000000000004', 'Regulatory Update Processing', 'Automated workflow for processing regulatory updates', 'EVENT', '{"event_type": "regulatory_update_received", "jurisdiction": ["US", "EU", "UK"]}'::jsonb, '[{"step": "analyze_impact", "agent": "regulatory_qa"}, {"step": "map_to_controls", "agent": "control_mapping"}, {"step": "update_policies", "agent": "workflow_orchestrator"}]'::jsonb, '30000000-0000-0000-0000-000000000002'),
    ('70000000-0000-0000-0000-000000000005', 'Incident Response Coordination', 'Automated workflow for security incident response', 'EVENT', '{"event_type": "security_incident_created", "severity": ["CRITICAL", "HIGH"]}'::jsonb, '[{"step": "assess_impact", "agent": "risk_assessment"}, {"step": "coordinate_response", "agent": "workflow_orchestrator"}, {"step": "track_remediation", "agent": "self_healing"}]'::jsonb, '30000000-0000-0000-0000-000000000005');

-- Insert sample ML models
INSERT INTO ml_models (id, model_name, model_type, algorithm, version, description, features, performance_metrics, accuracy, precision_score, recall, f1_score, status) VALUES
    ('80000000-0000-0000-0000-000000000001', 'Transaction Fraud Detector', 'CLASSIFICATION', 'Random Forest', '1.0', 'Detects fraudulent transactions using behavioral patterns', '["amount", "frequency", "location", "time_of_day", "merchant_category"]'::jsonb, '{"auc": 0.95, "precision": 0.87, "recall": 0.82}'::jsonb, 0.8500, 0.8700, 0.8200, 0.8440, 'DEPLOYED'),
    ('80000000-0000-0000-0000-000000000002', 'AML Risk Scorer', 'REGRESSION', 'Gradient Boosting', '1.0', 'Calculates AML risk scores for customers', '["transaction_volume", "geographic_risk", "business_type", "kyc_completeness"]'::jsonb, '{"rmse": 0.15, "mae": 0.12, "r2": 0.78}'::jsonb, NULL, NULL, NULL, NULL, 'DEPLOYED'),
    ('80000000-0000-0000-0000-000000000003', 'Anomaly Detector', 'ANOMALY_DETECTION', 'Isolation Forest', '1.0', 'Detects anomalous patterns in transaction data', '["amount_zscore", "frequency_zscore", "time_pattern", "network_features"]'::jsonb, '{"precision": 0.75, "recall": 0.68, "f1": 0.71}'::jsonb, NULL, 0.7500, 0.6800, 0.7100, 'DEPLOYED'),
    ('80000000-0000-0000-0000-000000000004', 'Credit Risk Model', 'CLASSIFICATION', 'Logistic Regression', '1.0', 'Predicts probability of default for credit exposures', '["debt_to_income", "credit_history", "employment_status", "loan_purpose"]'::jsonb, '{"auc": 0.88, "gini": 0.76, "ks": 0.45}'::jsonb, 0.8200, 0.7900, 0.8500, 0.8180, 'DEPLOYED'),
    ('80000000-0000-0000-0000-000000000005', 'Market Risk VaR Model', 'REGRESSION', 'Monte Carlo', '1.0', 'Calculates Value at Risk for market positions', '["position_delta", "volatility", "correlation_matrix", "time_horizon"]'::jsonb, '{"backtesting_exceptions": 3, "coverage_ratio": 0.95}'::jsonb, NULL, NULL, NULL, NULL, 'DEPLOYED');

-- Update sequences to avoid conflicts with seed data
SELECT setval('users_id_seq', (SELECT MAX(EXTRACT(EPOCH FROM created_at))::bigint FROM users), true);
SELECT setval('roles_id_seq', (SELECT MAX(EXTRACT(EPOCH FROM created_at))::bigint FROM roles), true);
