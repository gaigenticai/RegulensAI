-- RegulateAI Initial Database Schema
-- This migration creates the foundational tables for all RegulateAI services
-- Following PostgreSQL best practices with proper indexing and constraints

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =============================================================================
-- SHARED TABLES (Used across multiple services)
-- =============================================================================

-- Start of table structure: users
-- Purpose: Core user authentication and profile management
-- Service: Authentication & Authorization Framework
-- Relationships: Referenced by user_roles, audit_logs, and all service tables
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                    -- Unique user identifier
    email VARCHAR(255) NOT NULL UNIQUE,                                -- User email address (login credential)
    username VARCHAR(100) NOT NULL UNIQUE,                             -- Unique username (alternative login)
    password_hash VARCHAR(255) NOT NULL,                               -- Argon2 hashed password
    first_name VARCHAR(100) NOT NULL,                                  -- User's first name
    last_name VARCHAR(100) NOT NULL,                                   -- User's last name
    phone VARCHAR(20),                                                 -- Contact phone number
    is_active BOOLEAN NOT NULL DEFAULT true,                           -- Account active status
    is_verified BOOLEAN NOT NULL DEFAULT false,                        -- Email verification status
    last_login_at TIMESTAMPTZ,                                         -- Last successful login timestamp
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,                  -- Failed login counter for lockout
    locked_until TIMESTAMPTZ,                                          -- Account lockout expiration time
    password_changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),            -- Last password change timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),                     -- Record creation timestamp
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),                     -- Record last update timestamp
    created_by UUID,                                                   -- User who created this record
    updated_by UUID,                                                   -- User who last updated this record
    version INTEGER NOT NULL DEFAULT 1,                                -- Optimistic locking version
    metadata JSONB DEFAULT '{}'::jsonb                                 -- Additional user metadata
);
-- End of table structure: users

-- Start of table structure: roles
-- Purpose: Role-based access control (RBAC) role definitions
-- Service: Authentication & Authorization Framework
-- Relationships: Referenced by user_roles, linked to permissions
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                    -- Unique role identifier
    name VARCHAR(100) NOT NULL UNIQUE,                                 -- Role name (e.g., 'admin', 'analyst')
    description TEXT,                                                  -- Human-readable role description
    is_system_role BOOLEAN NOT NULL DEFAULT false,                     -- System-defined vs user-defined role
    permissions JSONB NOT NULL DEFAULT '[]'::jsonb,                             -- Array of permission strings
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),                     -- Record creation timestamp
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),                     -- Record last update timestamp
    created_by UUID,                                                   -- User who created this record
    updated_by UUID,                                                   -- User who last updated this record
    version INTEGER NOT NULL DEFAULT 1                                 -- Optimistic locking version
);
-- End of table structure: roles

-- Start of table structure: user_roles
CREATE TABLE user_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT true,
    UNIQUE(user_id, role_id)
);
-- End of table structure: user_roles

-- Start of table structure: organizations
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    legal_name VARCHAR(255),
    registration_number VARCHAR(100),
    tax_id VARCHAR(100),
    industry VARCHAR(100),
    country_code CHAR(2) NOT NULL,
    address JSONB,
    contact_info JSONB,
    risk_level VARCHAR(20) NOT NULL DEFAULT 'MEDIUM' CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE', 'PENDING', 'SUSPENDED', 'ARCHIVED')),
    onboarding_completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb
);
-- End of table structure: organizations

-- Start of table structure: audit_logs
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,
    old_values JSONB,
    new_values JSONB,
    user_id UUID REFERENCES users(id),
    ip_address INET,
    user_agent TEXT,
    correlation_id VARCHAR(100),
    service_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- End of table structure: audit_logs

-- =============================================================================
-- AML SERVICE TABLES
-- =============================================================================

-- Start of table structure: customers
-- Purpose: Customer master data for AML and compliance services
-- Service: AML Service
-- Relationships: References organizations, referenced by transactions and alerts
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),                    -- Unique customer identifier
    organization_id UUID REFERENCES organizations(id),                 -- Associated organization (if applicable)
    customer_type VARCHAR(20) NOT NULL CHECK (customer_type IN ('INDIVIDUAL', 'BUSINESS')), -- Customer classification
    first_name VARCHAR(100),                                           -- Individual customer first name
    last_name VARCHAR(100),                                            -- Individual customer last name
    date_of_birth DATE,                                                -- Individual customer birth date
    nationality VARCHAR(3),                                            -- ISO 3166-1 alpha-3 country code
    identification_documents JSONB DEFAULT '[]'::jsonb,                -- Array of ID documents (passport, license, etc.)
    address JSONB,                                                     -- Customer address information
    contact_info JSONB,                                                -- Email, phone, and other contact details
    risk_score DECIMAL(5,2) DEFAULT 0.00 CHECK (risk_score >= 0 AND risk_score <= 100), -- Calculated risk score (0-100)
    risk_level VARCHAR(20) NOT NULL DEFAULT 'MEDIUM' CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')), -- Risk classification
    pep_status BOOLEAN NOT NULL DEFAULT false,                         -- Politically Exposed Person status
    sanctions_status BOOLEAN NOT NULL DEFAULT false,                   -- Sanctions list match status
    kyc_status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (kyc_status IN ('PENDING', 'IN_PROGRESS', 'APPROVED', 'REJECTED', 'EXPIRED')), -- KYC verification status
    kyc_completed_at TIMESTAMPTZ,                                      -- KYC completion timestamp
    last_reviewed_at TIMESTAMPTZ,                                      -- Last risk review timestamp
    next_review_due TIMESTAMPTZ,                                       -- Next scheduled risk review date
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),                     -- Record creation timestamp
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),                     -- Record last update timestamp
    created_by UUID REFERENCES users(id),                              -- User who created this record
    updated_by UUID REFERENCES users(id),                              -- User who last updated this record
    version INTEGER NOT NULL DEFAULT 1,                                -- Optimistic locking version
    metadata JSONB DEFAULT '{}'::jsonb                                 -- Additional customer metadata
);
-- End of table structure: customers

-- Start of table structure: transactions
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id),
    transaction_type VARCHAR(50) NOT NULL,
    amount DECIMAL(20,2) NOT NULL CHECK (amount >= 0),
    currency CHAR(3) NOT NULL,
    description TEXT,
    counterparty_name VARCHAR(255),
    counterparty_account VARCHAR(100),
    counterparty_bank VARCHAR(255),
    counterparty_country CHAR(2),
    transaction_date TIMESTAMPTZ NOT NULL,
    value_date DATE,
    reference_number VARCHAR(100),
    channel VARCHAR(50),
    risk_score DECIMAL(5,2) DEFAULT 0.00 CHECK (risk_score >= 0 AND risk_score <= 100),
    risk_factors JSONB DEFAULT '[]'::jsonb,
    is_suspicious BOOLEAN NOT NULL DEFAULT false,
    alert_generated BOOLEAN NOT NULL DEFAULT false,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'UNDER_REVIEW')),
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb
);
-- End of table structure: transactions

-- Start of table structure: sanctions_lists
CREATE TABLE sanctions_lists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    list_name VARCHAR(100) NOT NULL,
    source VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_name VARCHAR(255) NOT NULL,
    aliases JSONB DEFAULT '[]'::jsonb,
    addresses JSONB DEFAULT '[]'::jsonb,
    identifiers JSONB DEFAULT '[]'::jsonb,
    sanctions_type VARCHAR(100),
    listing_date DATE,
    last_updated DATE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- End of table structure: sanctions_lists

-- Start of table structure: aml_alerts
CREATE TABLE aml_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    customer_id UUID REFERENCES customers(id),
    transaction_id UUID REFERENCES transactions(id),
    rule_name VARCHAR(100),
    description TEXT NOT NULL,
    risk_score DECIMAL(5,2) CHECK (risk_score >= 0 AND risk_score <= 100),
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'INVESTIGATING', 'CLOSED', 'FALSE_POSITIVE')),
    assigned_to UUID REFERENCES users(id),
    investigation_notes TEXT,
    resolution TEXT,
    closed_at TIMESTAMPTZ,
    escalated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb
);
-- End of table structure: aml_alerts

-- =============================================================================
-- COMPLIANCE SERVICE TABLES
-- =============================================================================

-- Start of table structure: policies
CREATE TABLE policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    policy_type VARCHAR(50) NOT NULL,
    framework VARCHAR(50),
    content TEXT NOT NULL,
    version_number VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'REVIEW', 'APPROVED', 'ACTIVE', 'ARCHIVED')),
    effective_date DATE,
    expiry_date DATE,
    review_frequency_months INTEGER,
    next_review_date DATE,
    owner_id UUID REFERENCES users(id),
    approver_id UUID REFERENCES users(id),
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb
);
-- End of table structure: policies

-- Start of table structure: controls
CREATE TABLE controls (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    control_id VARCHAR(50) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    control_type VARCHAR(20) NOT NULL CHECK (control_type IN ('PREVENTIVE', 'DETECTIVE', 'CORRECTIVE')),
    control_category VARCHAR(50),
    framework VARCHAR(50),
    policy_id UUID REFERENCES policies(id),
    owner_id UUID REFERENCES users(id),
    frequency VARCHAR(20) CHECK (frequency IN ('CONTINUOUS', 'DAILY', 'WEEKLY', 'MONTHLY', 'QUARTERLY', 'ANNUALLY')),
    automation_level VARCHAR(20) CHECK (automation_level IN ('MANUAL', 'SEMI_AUTOMATED', 'FULLY_AUTOMATED')),
    risk_rating VARCHAR(20) CHECK (risk_rating IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE', 'UNDER_REVIEW')),
    last_tested_at TIMESTAMPTZ,
    next_test_due TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb
);
-- End of table structure: controls

-- Start of table structure: control_tests
CREATE TABLE control_tests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    control_id UUID NOT NULL REFERENCES controls(id),
    test_date DATE NOT NULL,
    tester_id UUID NOT NULL REFERENCES users(id),
    test_procedure TEXT,
    sample_size INTEGER,
    exceptions_found INTEGER DEFAULT 0,
    test_result VARCHAR(20) NOT NULL CHECK (test_result IN ('EFFECTIVE', 'INEFFECTIVE', 'PARTIALLY_EFFECTIVE')),
    findings TEXT,
    recommendations TEXT,
    management_response TEXT,
    remediation_deadline DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'COMPLETED' CHECK (status IN ('PLANNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    version INTEGER NOT NULL DEFAULT 1
);
-- End of table structure: control_tests

-- Create indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_active ON users(is_active);
CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX idx_user_roles_role_id ON user_roles(role_id);
CREATE INDEX idx_organizations_country ON organizations(country_code);
CREATE INDEX idx_organizations_status ON organizations(status);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);
CREATE INDEX idx_customers_org ON customers(organization_id);
CREATE INDEX idx_customers_risk ON customers(risk_level);
CREATE INDEX idx_customers_kyc ON customers(kyc_status);
CREATE INDEX idx_transactions_customer ON transactions(customer_id);
CREATE INDEX idx_transactions_date ON transactions(transaction_date);
CREATE INDEX idx_transactions_amount ON transactions(amount);
CREATE INDEX idx_transactions_suspicious ON transactions(is_suspicious);
CREATE INDEX idx_sanctions_name ON sanctions_lists USING gin(entity_name gin_trgm_ops);
CREATE INDEX idx_sanctions_active ON sanctions_lists(is_active);
CREATE INDEX idx_aml_alerts_customer ON aml_alerts(customer_id);
CREATE INDEX idx_aml_alerts_status ON aml_alerts(status);
CREATE INDEX idx_aml_alerts_severity ON aml_alerts(severity);
CREATE INDEX idx_policies_status ON policies(status);
CREATE INDEX idx_policies_type ON policies(policy_type);
CREATE INDEX idx_controls_owner ON controls(owner_id);
CREATE INDEX idx_controls_status ON controls(status);
CREATE INDEX idx_control_tests_control ON control_tests(control_id);
CREATE INDEX idx_control_tests_date ON control_tests(test_date);

-- Create triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_roles_updated_at BEFORE UPDATE ON roles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON customers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_transactions_updated_at BEFORE UPDATE ON transactions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_sanctions_lists_updated_at BEFORE UPDATE ON sanctions_lists FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_aml_alerts_updated_at BEFORE UPDATE ON aml_alerts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_policies_updated_at BEFORE UPDATE ON policies FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_controls_updated_at BEFORE UPDATE ON controls FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_control_tests_updated_at BEFORE UPDATE ON control_tests FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
