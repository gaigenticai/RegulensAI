-- Migration: Notification System Enhancements
-- Description: Add notification templates, preferences, and advanced routing
-- Date: 2024-01-29

-- Create notification templates table
CREATE TABLE IF NOT EXISTS notification_templates (
    id VARCHAR(255) PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    template_name VARCHAR(100) NOT NULL,
    template_type VARCHAR(50) NOT NULL, -- email, sms, slack, etc.
    language VARCHAR(10) NOT NULL DEFAULT 'en',
    subject_template TEXT,
    text_template TEXT,
    html_template TEXT,
    sms_template TEXT,
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_tenant_template UNIQUE (tenant_id, template_name, template_type, language)
);

-- Create user notification preferences table
CREATE TABLE IF NOT EXISTS user_notification_preferences (
    user_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    preferences JSONB NOT NULL DEFAULT '{}',
    quiet_hours JSONB,
    escalation_rules JSONB DEFAULT '[]',
    language VARCHAR(10) DEFAULT 'en',
    timezone VARCHAR(50) DEFAULT 'UTC',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    PRIMARY KEY (user_id, tenant_id),
    FOREIGN KEY (user_id, tenant_id) REFERENCES users(id, tenant_id) ON DELETE CASCADE
);

-- Create tenant notification preferences table
CREATE TABLE IF NOT EXISTS tenant_notification_preferences (
    tenant_id UUID PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    default_preferences JSONB NOT NULL DEFAULT '{}',
    routing_rules JSONB DEFAULT '[]',
    escalation_matrix JSONB DEFAULT '{}',
    compliance_settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create notification routing logs table
CREATE TABLE IF NOT EXISTS notification_routing_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_id UUID NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
    user_id UUID,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    routing_decision JSONB NOT NULL,
    applied_rules JSONB DEFAULT '[]',
    escalation_triggered BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create notification acknowledgments table
CREATE TABLE IF NOT EXISTS notification_acknowledgments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_id UUID NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    acknowledged_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    acknowledgment_method VARCHAR(50), -- web, email_reply, api
    notes TEXT,
    
    CONSTRAINT unique_notification_acknowledgment UNIQUE (notification_id, user_id)
);

-- Create notification escalations table
CREATE TABLE IF NOT EXISTS notification_escalations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_notification_id UUID NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
    escalated_notification_id UUID REFERENCES notifications(id) ON DELETE CASCADE,
    escalation_level INTEGER NOT NULL DEFAULT 1,
    escalation_reason VARCHAR(100) NOT NULL,
    escalated_to_users UUID[] DEFAULT '{}',
    escalated_to_roles VARCHAR(50)[] DEFAULT '{}',
    escalated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE
);

-- Create notification metrics table for analytics
CREATE TABLE IF NOT EXISTS notification_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    metric_date DATE NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    channel VARCHAR(50) NOT NULL,
    total_sent INTEGER DEFAULT 0,
    total_delivered INTEGER DEFAULT 0,
    total_failed INTEGER DEFAULT 0,
    total_acknowledged INTEGER DEFAULT 0,
    average_delivery_time_seconds FLOAT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_daily_metric UNIQUE (tenant_id, metric_date, notification_type, channel)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_notification_templates_tenant ON notification_templates(tenant_id);
CREATE INDEX IF NOT EXISTS idx_notification_templates_name ON notification_templates(template_name);
CREATE INDEX IF NOT EXISTS idx_notification_templates_type ON notification_templates(template_type);
CREATE INDEX IF NOT EXISTS idx_notification_templates_active ON notification_templates(is_active);

CREATE INDEX IF NOT EXISTS idx_user_notification_prefs_user ON user_notification_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_user_notification_prefs_tenant ON user_notification_preferences(tenant_id);

CREATE INDEX IF NOT EXISTS idx_notification_routing_logs_notification ON notification_routing_logs(notification_id);
CREATE INDEX IF NOT EXISTS idx_notification_routing_logs_user ON notification_routing_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_notification_routing_logs_tenant ON notification_routing_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_notification_routing_logs_processed ON notification_routing_logs(processed_at);

CREATE INDEX IF NOT EXISTS idx_notification_acks_notification ON notification_acknowledgments(notification_id);
CREATE INDEX IF NOT EXISTS idx_notification_acks_user ON notification_acknowledgments(user_id);
CREATE INDEX IF NOT EXISTS idx_notification_acks_tenant ON notification_acknowledgments(tenant_id);
CREATE INDEX IF NOT EXISTS idx_notification_acks_acknowledged ON notification_acknowledgments(acknowledged_at);

CREATE INDEX IF NOT EXISTS idx_notification_escalations_original ON notification_escalations(original_notification_id);
CREATE INDEX IF NOT EXISTS idx_notification_escalations_escalated ON notification_escalations(escalated_notification_id);
CREATE INDEX IF NOT EXISTS idx_notification_escalations_tenant ON notification_escalations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_notification_escalations_level ON notification_escalations(escalation_level);

CREATE INDEX IF NOT EXISTS idx_notification_metrics_tenant ON notification_metrics(tenant_id);
CREATE INDEX IF NOT EXISTS idx_notification_metrics_date ON notification_metrics(metric_date);
CREATE INDEX IF NOT EXISTS idx_notification_metrics_type ON notification_metrics(notification_type);
CREATE INDEX IF NOT EXISTS idx_notification_metrics_channel ON notification_metrics(channel);

-- Add new columns to existing notifications table
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS template_name VARCHAR(100);
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS template_variables JSONB DEFAULT '{}';
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'en';
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'UTC';
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 0;
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS requires_acknowledgment BOOLEAN DEFAULT FALSE;
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS escalation_level INTEGER DEFAULT 0;
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS parent_notification_id UUID REFERENCES notifications(id);

-- Add new columns to existing notification_deliveries table
ALTER TABLE notification_deliveries ADD COLUMN IF NOT EXISTS delivery_attempt INTEGER DEFAULT 1;
ALTER TABLE notification_deliveries ADD COLUMN IF NOT EXISTS retry_after TIMESTAMP WITH TIME ZONE;
ALTER TABLE notification_deliveries ADD COLUMN IF NOT EXISTS delivery_time_seconds FLOAT;
ALTER TABLE notification_deliveries ADD COLUMN IF NOT EXISTS user_agent TEXT;
ALTER TABLE notification_deliveries ADD COLUMN IF NOT EXISTS ip_address INET;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_notification_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_notification_templates_updated_at 
    BEFORE UPDATE ON notification_templates 
    FOR EACH ROW EXECUTE FUNCTION update_notification_updated_at();

CREATE TRIGGER update_user_notification_prefs_updated_at 
    BEFORE UPDATE ON user_notification_preferences 
    FOR EACH ROW EXECUTE FUNCTION update_notification_updated_at();

CREATE TRIGGER update_tenant_notification_prefs_updated_at 
    BEFORE UPDATE ON tenant_notification_preferences 
    FOR EACH ROW EXECUTE FUNCTION update_notification_updated_at();

-- Insert default notification templates
INSERT INTO notification_templates (id, tenant_id, template_name, template_type, language, subject_template, text_template, html_template) VALUES
('default_alert_email_en', NULL, 'alert_created', 'email', 'en', 
 '[{{ severity|upper }}] {{ title }}',
 'Alert: {{ title }}\n\nDescription: {{ description }}\n\nSeverity: {{ severity }}\nType: {{ alert_type }}\nCreated: {{ created_at|datetime }}\n\nPlease review this alert in the RegulensAI dashboard.',
 'alert_created.html'),

('default_compliance_email_en', NULL, 'compliance_violation', 'email', 'en',
 'Compliance Violation Detected - {{ violation_type }}',
 'A compliance violation has been detected:\n\nViolation Type: {{ violation_type }}\nEntity: {{ entity_name }}\nRisk Score: {{ risk_score }}\nDetected: {{ detected_at|datetime }}\n\nDetails: {{ details }}\n\nPlease review and take appropriate action.',
 'compliance_violation.html'),

('default_transaction_email_en', NULL, 'transaction_flagged', 'email', 'en',
 'Transaction Flagged for Review - {{ transaction_id }}',
 'A transaction has been flagged for review:\n\nTransaction ID: {{ transaction_id }}\nAmount: {{ amount|currency }}\nCustomer: {{ customer_name }}\nFlagged: {{ flagged_at|datetime }}\n\nReason: {{ flag_reason }}\n\nPlease review in the transaction monitoring dashboard.',
 'transaction_flagged.html'),

('default_welcome_email_en', NULL, 'user_welcome', 'email', 'en',
 'Welcome to {{ company_name }}',
 'Welcome {{ user_name }},\n\nYour account has been created successfully.\n\nUsername: {{ username }}\nRole: {{ role }}\n\nPlease log in to the RegulensAI platform to get started.',
 'user_welcome.html'),

('default_password_reset_email_en', NULL, 'password_reset', 'email', 'en',
 'Password Reset Request',
 'A password reset has been requested for your account.\n\nClick the link below to reset your password:\n{{ reset_link }}\n\nThis link will expire in 24 hours.\n\nIf you did not request this reset, please ignore this email.',
 'password_reset.html')

ON CONFLICT (tenant_id, template_name, template_type, language) DO NOTHING;

-- Insert default SMS templates
INSERT INTO notification_templates (id, tenant_id, template_name, template_type, language, sms_template) VALUES
('default_alert_sms_en', NULL, 'alert_created', 'sms', 'en', 
 '[{{ severity|upper }}] {{ title }}: {{ description|truncate(100) }}'),

('default_compliance_sms_en', NULL, 'compliance_violation', 'sms', 'en',
 'Compliance violation detected: {{ violation_type }} - {{ entity_name }}. Risk score: {{ risk_score }}'),

('default_transaction_sms_en', NULL, 'transaction_flagged', 'sms', 'en',
 'Transaction {{ transaction_id }} flagged: {{ amount|currency }} - {{ flag_reason|truncate(50) }}')

ON CONFLICT (tenant_id, template_name, template_type, language) DO NOTHING;

-- Create view for notification analytics
CREATE OR REPLACE VIEW notification_analytics AS
SELECT 
    n.tenant_id,
    n.notification_type,
    DATE(n.created_at) as notification_date,
    COUNT(*) as total_notifications,
    COUNT(CASE WHEN nd.status = 'sent' THEN 1 END) as delivered_count,
    COUNT(CASE WHEN nd.status = 'failed' THEN 1 END) as failed_count,
    COUNT(CASE WHEN na.id IS NOT NULL THEN 1 END) as acknowledged_count,
    COUNT(CASE WHEN ne.id IS NOT NULL THEN 1 END) as escalated_count,
    AVG(nd.delivery_time_seconds) as avg_delivery_time,
    ROUND(
        (COUNT(CASE WHEN nd.status = 'sent' THEN 1 END)::FLOAT / COUNT(*)) * 100, 2
    ) as delivery_rate
FROM notifications n
LEFT JOIN notification_deliveries nd ON n.id = nd.notification_id
LEFT JOIN notification_acknowledgments na ON n.id = na.notification_id
LEFT JOIN notification_escalations ne ON n.id = ne.original_notification_id
GROUP BY n.tenant_id, n.notification_type, DATE(n.created_at);

-- Create view for user notification summary
CREATE OR REPLACE VIEW user_notification_summary AS
SELECT 
    u.id as user_id,
    u.tenant_id,
    u.email,
    u.first_name,
    u.last_name,
    COUNT(nrl.id) as total_notifications_received,
    COUNT(na.id) as total_acknowledged,
    COUNT(CASE WHEN n.created_at >= NOW() - INTERVAL '7 days' THEN 1 END) as notifications_last_7_days,
    COUNT(CASE WHEN n.created_at >= NOW() - INTERVAL '30 days' THEN 1 END) as notifications_last_30_days,
    MAX(n.created_at) as last_notification_received,
    MAX(na.acknowledged_at) as last_acknowledgment
FROM users u
LEFT JOIN notification_routing_logs nrl ON u.id = nrl.user_id
LEFT JOIN notifications n ON nrl.notification_id = n.id
LEFT JOIN notification_acknowledgments na ON n.id = na.notification_id AND u.id = na.user_id
WHERE u.is_active = true
GROUP BY u.id, u.tenant_id, u.email, u.first_name, u.last_name;

-- Add table comments
COMMENT ON TABLE notification_templates IS 'Customizable notification templates with multi-language support';
COMMENT ON TABLE user_notification_preferences IS 'User-specific notification preferences and routing rules';
COMMENT ON TABLE tenant_notification_preferences IS 'Tenant-level notification configuration and escalation matrix';
COMMENT ON TABLE notification_routing_logs IS 'Audit log of notification routing decisions';
COMMENT ON TABLE notification_acknowledgments IS 'User acknowledgments of received notifications';
COMMENT ON TABLE notification_escalations IS 'Notification escalation tracking and management';
COMMENT ON TABLE notification_metrics IS 'Daily aggregated notification delivery metrics';

-- Grant appropriate permissions (adjust based on your user roles)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON notification_templates TO regulens_app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON user_notification_preferences TO regulens_app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON tenant_notification_preferences TO regulens_app_user;
-- GRANT SELECT, INSERT ON notification_routing_logs TO regulens_app_user;
-- GRANT SELECT, INSERT, UPDATE ON notification_acknowledgments TO regulens_app_user;
-- GRANT SELECT, INSERT, UPDATE ON notification_escalations TO regulens_app_user;
-- GRANT SELECT, INSERT, UPDATE ON notification_metrics TO regulens_app_user;
