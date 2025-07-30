-- Migration: Create credential management tables
-- Description: Tables for secure credential storage and audit logging
-- Date: 2024-01-29

-- Create credentials table for encrypted credential storage
CREATE TABLE IF NOT EXISTS credentials (
    id VARCHAR(255) PRIMARY KEY,
    tenant_id UUID NOT NULL,
    service_name VARCHAR(100) NOT NULL,
    credential_type VARCHAR(50) NOT NULL,
    encrypted_data JSONB NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes for performance
    CONSTRAINT unique_tenant_service_type UNIQUE (tenant_id, service_name, credential_type)
);

-- Create indexes for credentials table
CREATE INDEX IF NOT EXISTS idx_credentials_tenant_id ON credentials(tenant_id);
CREATE INDEX IF NOT EXISTS idx_credentials_service_name ON credentials(service_name);
CREATE INDEX IF NOT EXISTS idx_credentials_expires_at ON credentials(expires_at);
CREATE INDEX IF NOT EXISTS idx_credentials_created_at ON credentials(created_at);

-- Create credential audit log table
CREATE TABLE IF NOT EXISTS credential_audit_log (
    id VARCHAR(255) PRIMARY KEY,
    tenant_id UUID NOT NULL,
    credential_id VARCHAR(255) NOT NULL,
    action VARCHAR(50) NOT NULL, -- store, retrieve, rotate, delete
    service_name VARCHAR(100),
    credential_type VARCHAR(50),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT,
    additional_metadata JSONB DEFAULT '{}'
);

-- Create indexes for audit log table
CREATE INDEX IF NOT EXISTS idx_audit_log_tenant_id ON credential_audit_log(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_credential_id ON credential_audit_log(credential_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON credential_audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON credential_audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_service_name ON credential_audit_log(service_name);

-- Create credential rotation schedule table
CREATE TABLE IF NOT EXISTS credential_rotation_schedule (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    service_name VARCHAR(100) NOT NULL,
    credential_type VARCHAR(50) NOT NULL,
    rotation_interval_days INTEGER NOT NULL DEFAULT 90,
    last_rotated_at TIMESTAMP WITH TIME ZONE,
    next_rotation_at TIMESTAMP WITH TIME ZONE,
    auto_rotation_enabled BOOLEAN DEFAULT FALSE,
    notification_days_before INTEGER DEFAULT 7,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_rotation_schedule UNIQUE (tenant_id, service_name, credential_type)
);

-- Create indexes for rotation schedule table
CREATE INDEX IF NOT EXISTS idx_rotation_schedule_tenant_id ON credential_rotation_schedule(tenant_id);
CREATE INDEX IF NOT EXISTS idx_rotation_schedule_next_rotation ON credential_rotation_schedule(next_rotation_at);
CREATE INDEX IF NOT EXISTS idx_rotation_schedule_auto_enabled ON credential_rotation_schedule(auto_rotation_enabled);

-- Create service account configurations table
CREATE TABLE IF NOT EXISTS service_account_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    service_name VARCHAR(100) NOT NULL,
    configuration_data JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    validation_status VARCHAR(50) DEFAULT 'pending', -- pending, valid, invalid, expired
    last_validated_at TIMESTAMP WITH TIME ZONE,
    validation_error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_service_config UNIQUE (tenant_id, service_name)
);

-- Create indexes for service account configurations
CREATE INDEX IF NOT EXISTS idx_service_config_tenant_id ON service_account_configurations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_service_config_service_name ON service_account_configurations(service_name);
CREATE INDEX IF NOT EXISTS idx_service_config_validation_status ON service_account_configurations(validation_status);
CREATE INDEX IF NOT EXISTS idx_service_config_is_active ON service_account_configurations(is_active);

-- Create external service endpoints table
CREATE TABLE IF NOT EXISTS external_service_endpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_name VARCHAR(100) NOT NULL,
    endpoint_type VARCHAR(50) NOT NULL, -- auth, api, webhook, etc.
    environment VARCHAR(20) NOT NULL, -- sandbox, production
    base_url TEXT NOT NULL,
    endpoint_path TEXT,
    http_method VARCHAR(10) DEFAULT 'GET',
    required_headers JSONB DEFAULT '{}',
    rate_limit_per_minute INTEGER,
    timeout_seconds INTEGER DEFAULT 30,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_service_endpoint UNIQUE (service_name, endpoint_type, environment)
);

-- Create indexes for external service endpoints
CREATE INDEX IF NOT EXISTS idx_service_endpoints_service_name ON external_service_endpoints(service_name);
CREATE INDEX IF NOT EXISTS idx_service_endpoints_environment ON external_service_endpoints(environment);
CREATE INDEX IF NOT EXISTS idx_service_endpoints_is_active ON external_service_endpoints(is_active);

-- Insert default external service endpoints
INSERT INTO external_service_endpoints (service_name, endpoint_type, environment, base_url, endpoint_path, http_method) VALUES
-- Experian endpoints
('experian', 'auth', 'sandbox', 'https://sandbox-api.experian.com', '/oauth2/v1/token', 'POST'),
('experian', 'auth', 'production', 'https://api.experian.com', '/oauth2/v1/token', 'POST'),
('experian', 'credit_profile', 'sandbox', 'https://sandbox-api.experian.com', '/consumerservices/credit-profile/v2/credit-report', 'POST'),
('experian', 'credit_profile', 'production', 'https://api.experian.com', '/consumerservices/credit-profile/v2/credit-report', 'POST'),
('experian', 'identity_verification', 'sandbox', 'https://sandbox-api.experian.com', '/identityservices/precise-id/v3/identity-verification', 'POST'),
('experian', 'identity_verification', 'production', 'https://api.experian.com', '/identityservices/precise-id/v3/identity-verification', 'POST'),

-- Refinitiv endpoints
('refinitiv', 'auth', 'production', 'https://api.refinitiv.com', '/auth/oauth2/v1/token', 'POST'),
('refinitiv', 'market_data', 'production', 'https://api.refinitiv.com', '/data/pricing/snapshots/v1/', 'POST'),
('refinitiv', 'news', 'production', 'https://api.refinitiv.com', '/data/news/v1/', 'GET'),
('refinitiv', 'fundamentals', 'production', 'https://api.refinitiv.com', '/data/fundamentals/v1/', 'GET'),

-- OFAC endpoints (public, no auth required)
('ofac', 'sdn_list', 'production', 'https://www.treasury.gov', '/ofac/downloads/sdn.xml', 'GET'),
('ofac', 'consolidated_list', 'production', 'https://www.treasury.gov', '/ofac/downloads/consolidated/consolidated.xml', 'GET'),
('ofac', 'ssi_list', 'production', 'https://www.treasury.gov', '/ofac/downloads/ssi/ssi.xml', 'GET'),

-- Twilio endpoints
('twilio', 'messages', 'production', 'https://api.twilio.com', '/2010-04-01/Accounts/{AccountSid}/Messages.json', 'POST'),
('twilio', 'verify', 'production', 'https://verify.twilio.com', '/v2/Services/{ServiceSid}/Verifications', 'POST')

ON CONFLICT (service_name, endpoint_type, environment) DO NOTHING;

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_credentials_updated_at 
    BEFORE UPDATE ON credentials 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_rotation_schedule_updated_at 
    BEFORE UPDATE ON credential_rotation_schedule 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_service_config_updated_at 
    BEFORE UPDATE ON service_account_configurations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_service_endpoints_updated_at 
    BEFORE UPDATE ON external_service_endpoints 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create view for credential status overview
CREATE OR REPLACE VIEW credential_status_overview AS
SELECT 
    c.tenant_id,
    c.service_name,
    c.credential_type,
    c.id as credential_id,
    c.created_at,
    c.expires_at,
    CASE 
        WHEN c.expires_at IS NULL THEN 'no_expiration'
        WHEN c.expires_at > NOW() + INTERVAL '30 days' THEN 'valid'
        WHEN c.expires_at > NOW() + INTERVAL '7 days' THEN 'expiring_soon'
        WHEN c.expires_at > NOW() THEN 'expiring_very_soon'
        ELSE 'expired'
    END as status,
    sac.validation_status,
    sac.last_validated_at,
    crs.next_rotation_at,
    crs.auto_rotation_enabled
FROM credentials c
LEFT JOIN service_account_configurations sac ON c.tenant_id = sac.tenant_id AND c.service_name = sac.service_name
LEFT JOIN credential_rotation_schedule crs ON c.tenant_id = crs.tenant_id AND c.service_name = crs.service_name AND c.credential_type = crs.credential_type;

-- Create view for audit log summary
CREATE OR REPLACE VIEW credential_audit_summary AS
SELECT 
    tenant_id,
    service_name,
    action,
    DATE(timestamp) as audit_date,
    COUNT(*) as action_count,
    COUNT(DISTINCT credential_id) as unique_credentials
FROM credential_audit_log
GROUP BY tenant_id, service_name, action, DATE(timestamp)
ORDER BY audit_date DESC, tenant_id, service_name;

-- Add comments for documentation
COMMENT ON TABLE credentials IS 'Encrypted storage for external service credentials';
COMMENT ON TABLE credential_audit_log IS 'Audit log for all credential operations';
COMMENT ON TABLE credential_rotation_schedule IS 'Automated credential rotation scheduling';
COMMENT ON TABLE service_account_configurations IS 'Service account setup and validation status';
COMMENT ON TABLE external_service_endpoints IS 'External service API endpoint configurations';

COMMENT ON COLUMN credentials.encrypted_data IS 'Encrypted JSON containing sensitive credential data';
COMMENT ON COLUMN credentials.metadata IS 'Non-sensitive metadata about the credential';
COMMENT ON COLUMN credential_audit_log.action IS 'Type of action: store, retrieve, rotate, delete';
COMMENT ON COLUMN service_account_configurations.validation_status IS 'Current validation status: pending, valid, invalid, expired';

-- Grant appropriate permissions (adjust based on your user roles)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON credentials TO regulens_app_user;
-- GRANT SELECT, INSERT ON credential_audit_log TO regulens_app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON credential_rotation_schedule TO regulens_app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON service_account_configurations TO regulens_app_user;
-- GRANT SELECT ON external_service_endpoints TO regulens_app_user;
