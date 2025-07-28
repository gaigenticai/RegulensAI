-- ============================================================================
-- REGULENS AI - FINANCIAL COMPLIANCE PLATFORM DATABASE SCHEMA
-- Enterprise-grade schema for financial services compliance
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable Row Level Security
ALTER DATABASE postgres SET "app.jwt_secret" TO 'your-jwt-secret-change-in-production';

-- ============================================================================
-- TENANTS AND USERS
-- ============================================================================

-- Step 1: Create tenants table with primary key
CREATE TABLE IF NOT EXISTS public.tenants (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to tenants
ALTER TABLE public.tenants
    ADD COLUMN IF NOT EXISTS name text NOT NULL;

ALTER TABLE public.tenants
    ADD COLUMN IF NOT EXISTS industry text NOT NULL;

ALTER TABLE public.tenants
    ADD COLUMN IF NOT EXISTS country_code text NOT NULL;

ALTER TABLE public.tenants
    ADD COLUMN IF NOT EXISTS regulatory_jurisdictions jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.tenants
    ADD COLUMN IF NOT EXISTS subscription_tier text NOT NULL DEFAULT 'enterprise';

ALTER TABLE public.tenants
    ADD COLUMN IF NOT EXISTS settings jsonb NOT NULL DEFAULT '{}';

ALTER TABLE public.tenants
    ADD COLUMN IF NOT EXISTS is_active boolean DEFAULT true NOT NULL;

ALTER TABLE public.tenants
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.tenants
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create users table with primary key
CREATE TABLE IF NOT EXISTS public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to users
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS email text UNIQUE NOT NULL;

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS full_name text NOT NULL;

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS role text NOT NULL DEFAULT 'compliance_officer';

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS permissions jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS department text;

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS last_login timestamp with time zone;

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS is_active boolean DEFAULT true NOT NULL;

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- ============================================================================
-- REGULATORY INTELLIGENCE
-- ============================================================================

-- Step 1: Create regulatory_sources table with primary key
CREATE TABLE IF NOT EXISTS public.regulatory_sources (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to regulatory_sources
ALTER TABLE public.regulatory_sources
    ADD COLUMN IF NOT EXISTS name text NOT NULL;

ALTER TABLE public.regulatory_sources
    ADD COLUMN IF NOT EXISTS type text NOT NULL; -- 'regulator', 'government', 'industry_body'

ALTER TABLE public.regulatory_sources
    ADD COLUMN IF NOT EXISTS country_code text NOT NULL;

ALTER TABLE public.regulatory_sources
    ADD COLUMN IF NOT EXISTS jurisdiction text NOT NULL;

ALTER TABLE public.regulatory_sources
    ADD COLUMN IF NOT EXISTS website_url text;

ALTER TABLE public.regulatory_sources
    ADD COLUMN IF NOT EXISTS rss_feed_url text;

ALTER TABLE public.regulatory_sources
    ADD COLUMN IF NOT EXISTS api_endpoint text;

ALTER TABLE public.regulatory_sources
    ADD COLUMN IF NOT EXISTS monitoring_enabled boolean DEFAULT true NOT NULL;

ALTER TABLE public.regulatory_sources
    ADD COLUMN IF NOT EXISTS last_monitored timestamp with time zone;

ALTER TABLE public.regulatory_sources
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create regulatory_documents table with primary key
CREATE TABLE IF NOT EXISTS public.regulatory_documents (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to regulatory_documents
ALTER TABLE public.regulatory_documents
    ADD COLUMN IF NOT EXISTS source_id uuid NOT NULL REFERENCES public.regulatory_sources(id);

ALTER TABLE public.regulatory_documents
    ADD COLUMN IF NOT EXISTS document_number text NOT NULL;

ALTER TABLE public.regulatory_documents
    ADD COLUMN IF NOT EXISTS title text NOT NULL;

ALTER TABLE public.regulatory_documents
    ADD COLUMN IF NOT EXISTS document_type text NOT NULL; -- 'regulation', 'guidance', 'enforcement', 'proposal'

ALTER TABLE public.regulatory_documents
    ADD COLUMN IF NOT EXISTS status text NOT NULL; -- 'draft', 'final', 'effective', 'superseded'

ALTER TABLE public.regulatory_documents
    ADD COLUMN IF NOT EXISTS effective_date date;

ALTER TABLE public.regulatory_documents
    ADD COLUMN IF NOT EXISTS comment_deadline date;

ALTER TABLE public.regulatory_documents
    ADD COLUMN IF NOT EXISTS publication_date date NOT NULL;

ALTER TABLE public.regulatory_documents
    ADD COLUMN IF NOT EXISTS summary text;

ALTER TABLE public.regulatory_documents
    ADD COLUMN IF NOT EXISTS full_text text;

ALTER TABLE public.regulatory_documents
    ADD COLUMN IF NOT EXISTS document_url text;

ALTER TABLE public.regulatory_documents
    ADD COLUMN IF NOT EXISTS topics jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.regulatory_documents
    ADD COLUMN IF NOT EXISTS keywords jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.regulatory_documents
    ADD COLUMN IF NOT EXISTS impact_level text; -- 'high', 'medium', 'low'

ALTER TABLE public.regulatory_documents
    ADD COLUMN IF NOT EXISTS ai_analysis jsonb DEFAULT '{}';

ALTER TABLE public.regulatory_documents
    ADD COLUMN IF NOT EXISTS version_number text DEFAULT '1.0';

ALTER TABLE public.regulatory_documents
    ADD COLUMN IF NOT EXISTS supersedes_document_id uuid REFERENCES public.regulatory_documents(id);

ALTER TABLE public.regulatory_documents
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.regulatory_documents
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create regulatory_obligations table with primary key
CREATE TABLE IF NOT EXISTS public.regulatory_obligations (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to regulatory_obligations
ALTER TABLE public.regulatory_obligations
    ADD COLUMN IF NOT EXISTS document_id uuid NOT NULL REFERENCES public.regulatory_documents(id);

ALTER TABLE public.regulatory_obligations
    ADD COLUMN IF NOT EXISTS obligation_text text NOT NULL;

ALTER TABLE public.regulatory_obligations
    ADD COLUMN IF NOT EXISTS obligation_type text NOT NULL; -- 'mandatory', 'conditional', 'best_practice'

ALTER TABLE public.regulatory_obligations
    ADD COLUMN IF NOT EXISTS compliance_deadline date;

ALTER TABLE public.regulatory_obligations
    ADD COLUMN IF NOT EXISTS penalty_description text;

ALTER TABLE public.regulatory_obligations
    ADD COLUMN IF NOT EXISTS applicable_entities jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.regulatory_obligations
    ADD COLUMN IF NOT EXISTS section_reference text;

ALTER TABLE public.regulatory_obligations
    ADD COLUMN IF NOT EXISTS ai_interpretation jsonb DEFAULT '{}';

ALTER TABLE public.regulatory_obligations
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

-- ============================================================================
-- COMPLIANCE MANAGEMENT
-- ============================================================================

-- Step 1: Create compliance_programs table with primary key
CREATE TABLE IF NOT EXISTS public.compliance_programs (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to compliance_programs
ALTER TABLE public.compliance_programs
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.compliance_programs
    ADD COLUMN IF NOT EXISTS name text NOT NULL;

ALTER TABLE public.compliance_programs
    ADD COLUMN IF NOT EXISTS description text;

ALTER TABLE public.compliance_programs
    ADD COLUMN IF NOT EXISTS program_type text NOT NULL; -- 'aml', 'kyc', 'sox', 'gdpr', 'custom'

ALTER TABLE public.compliance_programs
    ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'active'; -- 'active', 'inactive', 'under_review'

ALTER TABLE public.compliance_programs
    ADD COLUMN IF NOT EXISTS owner_user_id uuid NOT NULL REFERENCES public.users(id);

ALTER TABLE public.compliance_programs
    ADD COLUMN IF NOT EXISTS risk_assessment jsonb DEFAULT '{}';

ALTER TABLE public.compliance_programs
    ADD COLUMN IF NOT EXISTS review_frequency text DEFAULT 'annual'; -- 'monthly', 'quarterly', 'annual'

ALTER TABLE public.compliance_programs
    ADD COLUMN IF NOT EXISTS last_reviewed timestamp with time zone;

ALTER TABLE public.compliance_programs
    ADD COLUMN IF NOT EXISTS next_review_due timestamp with time zone;

ALTER TABLE public.compliance_programs
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.compliance_programs
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create compliance_requirements table with primary key
CREATE TABLE IF NOT EXISTS public.compliance_requirements (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to compliance_requirements
ALTER TABLE public.compliance_requirements
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.compliance_requirements
    ADD COLUMN IF NOT EXISTS program_id uuid NOT NULL REFERENCES public.compliance_programs(id);

ALTER TABLE public.compliance_requirements
    ADD COLUMN IF NOT EXISTS obligation_id uuid REFERENCES public.regulatory_obligations(id);

ALTER TABLE public.compliance_requirements
    ADD COLUMN IF NOT EXISTS requirement_title text NOT NULL;

ALTER TABLE public.compliance_requirements
    ADD COLUMN IF NOT EXISTS requirement_description text NOT NULL;

ALTER TABLE public.compliance_requirements
    ADD COLUMN IF NOT EXISTS control_objective text;

ALTER TABLE public.compliance_requirements
    ADD COLUMN IF NOT EXISTS control_activities jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.compliance_requirements
    ADD COLUMN IF NOT EXISTS risk_level text NOT NULL; -- 'high', 'medium', 'low'

ALTER TABLE public.compliance_requirements
    ADD COLUMN IF NOT EXISTS testing_frequency text DEFAULT 'quarterly';

ALTER TABLE public.compliance_requirements
    ADD COLUMN IF NOT EXISTS responsible_party text;

ALTER TABLE public.compliance_requirements
    ADD COLUMN IF NOT EXISTS evidence_requirements jsonb DEFAULT '[]';

ALTER TABLE public.compliance_requirements
    ADD COLUMN IF NOT EXISTS compliance_status text NOT NULL DEFAULT 'pending'; -- 'compliant', 'non_compliant', 'pending', 'under_review'

ALTER TABLE public.compliance_requirements
    ADD COLUMN IF NOT EXISTS last_tested timestamp with time zone;

ALTER TABLE public.compliance_requirements
    ADD COLUMN IF NOT EXISTS next_test_due timestamp with time zone;

ALTER TABLE public.compliance_requirements
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.compliance_requirements
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- ============================================================================
-- AML/KYC COMPLIANCE
-- ============================================================================

-- Step 1: Create customers table with primary key
CREATE TABLE IF NOT EXISTS public.customers (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to customers
ALTER TABLE public.customers
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.customers
    ADD COLUMN IF NOT EXISTS customer_id text NOT NULL;

ALTER TABLE public.customers
    ADD COLUMN IF NOT EXISTS customer_type text NOT NULL; -- 'individual', 'corporate', 'trust', 'partnership'

ALTER TABLE public.customers
    ADD COLUMN IF NOT EXISTS full_name text NOT NULL;

ALTER TABLE public.customers
    ADD COLUMN IF NOT EXISTS date_of_birth date;

ALTER TABLE public.customers
    ADD COLUMN IF NOT EXISTS country_of_residence text;

ALTER TABLE public.customers
    ADD COLUMN IF NOT EXISTS nationality text;

ALTER TABLE public.customers
    ADD COLUMN IF NOT EXISTS risk_rating text NOT NULL; -- 'low', 'medium', 'high'

ALTER TABLE public.customers
    ADD COLUMN IF NOT EXISTS pep_status boolean DEFAULT false NOT NULL; -- Politically Exposed Person

ALTER TABLE public.customers
    ADD COLUMN IF NOT EXISTS sanctions_check_status text DEFAULT 'pending'; -- 'clear', 'match', 'pending'

ALTER TABLE public.customers
    ADD COLUMN IF NOT EXISTS kyc_status text NOT NULL DEFAULT 'pending'; -- 'verified', 'rejected', 'pending', 'expired'

ALTER TABLE public.customers
    ADD COLUMN IF NOT EXISTS kyc_documents jsonb DEFAULT '[]';

ALTER TABLE public.customers
    ADD COLUMN IF NOT EXISTS due_diligence_date timestamp with time zone;

ALTER TABLE public.customers
    ADD COLUMN IF NOT EXISTS next_review_date timestamp with time zone;

ALTER TABLE public.customers
    ADD COLUMN IF NOT EXISTS source_of_funds text;

ALTER TABLE public.customers
    ADD COLUMN IF NOT EXISTS purpose_of_relationship text;

ALTER TABLE public.customers
    ADD COLUMN IF NOT EXISTS expected_activity jsonb DEFAULT '{}';

ALTER TABLE public.customers
    ADD COLUMN IF NOT EXISTS onboarding_date timestamp with time zone DEFAULT now();

ALTER TABLE public.customers
    ADD COLUMN IF NOT EXISTS is_active boolean DEFAULT true NOT NULL;

ALTER TABLE public.customers
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.customers
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create transactions table with primary key
CREATE TABLE IF NOT EXISTS public.transactions (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to transactions
ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS transaction_id text NOT NULL;

ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS customer_id uuid NOT NULL REFERENCES public.customers(id);

ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS transaction_type text NOT NULL; -- 'deposit', 'withdrawal', 'transfer', 'payment'

ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS amount decimal(15,2) NOT NULL;

ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS currency text NOT NULL DEFAULT 'USD';

ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS transaction_date timestamp with time zone NOT NULL;

ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS originator_info jsonb;

ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS beneficiary_info jsonb;

ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS purpose text;

ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS country_of_origin text;

ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS country_of_destination text;

ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS payment_method text;

ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS suspicious_activity_score decimal(5,2);

ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS aml_status text NOT NULL DEFAULT 'clear'; -- 'clear', 'flagged', 'investigated', 'reported'

ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS monitoring_alerts jsonb DEFAULT '[]';

ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create suspicious_activity_reports table with primary key
CREATE TABLE IF NOT EXISTS public.suspicious_activity_reports (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to suspicious_activity_reports
ALTER TABLE public.suspicious_activity_reports
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.suspicious_activity_reports
    ADD COLUMN IF NOT EXISTS sar_number text NOT NULL;

ALTER TABLE public.suspicious_activity_reports
    ADD COLUMN IF NOT EXISTS customer_id uuid NOT NULL REFERENCES public.customers(id);

ALTER TABLE public.suspicious_activity_reports
    ADD COLUMN IF NOT EXISTS filing_date timestamp with time zone NOT NULL;

ALTER TABLE public.suspicious_activity_reports
    ADD COLUMN IF NOT EXISTS suspicious_activity_type text NOT NULL;

ALTER TABLE public.suspicious_activity_reports
    ADD COLUMN IF NOT EXISTS narrative text NOT NULL;

ALTER TABLE public.suspicious_activity_reports
    ADD COLUMN IF NOT EXISTS total_amount decimal(15,2);

ALTER TABLE public.suspicious_activity_reports
    ADD COLUMN IF NOT EXISTS currency text DEFAULT 'USD';

ALTER TABLE public.suspicious_activity_reports
    ADD COLUMN IF NOT EXISTS related_transactions jsonb DEFAULT '[]';

ALTER TABLE public.suspicious_activity_reports
    ADD COLUMN IF NOT EXISTS filing_institution text NOT NULL;

ALTER TABLE public.suspicious_activity_reports
    ADD COLUMN IF NOT EXISTS regulatory_reference_number text;

ALTER TABLE public.suspicious_activity_reports
    ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'filed'; -- 'draft', 'filed', 'acknowledged'

ALTER TABLE public.suspicious_activity_reports
    ADD COLUMN IF NOT EXISTS filed_by_user_id uuid NOT NULL REFERENCES public.users(id);

ALTER TABLE public.suspicious_activity_reports
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

-- ============================================================================
-- WORKFLOW MANAGEMENT
-- ============================================================================

-- Step 1: Create compliance_tasks table with primary key
CREATE TABLE IF NOT EXISTS public.compliance_tasks (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to compliance_tasks
ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS task_title text NOT NULL;

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS task_description text;

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS task_type text NOT NULL; -- 'review', 'assessment', 'remediation', 'testing'

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS priority text NOT NULL DEFAULT 'medium'; -- 'critical', 'high', 'medium', 'low'

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'assigned'; -- 'assigned', 'in_progress', 'completed', 'overdue', 'cancelled'

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS assigned_to_user_id uuid NOT NULL REFERENCES public.users(id);

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS assigned_by_user_id uuid NOT NULL REFERENCES public.users(id);

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS due_date timestamp with time zone NOT NULL;

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS completed_date timestamp with time zone;

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS related_requirement_id uuid REFERENCES public.compliance_requirements(id);

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS related_document_id uuid REFERENCES public.regulatory_documents(id);

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS evidence_attachments jsonb DEFAULT '[]';

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS completion_notes text;

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS estimated_hours decimal(5,2);

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS actual_hours decimal(5,2);

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create regulatory_impact_assessments table with primary key
CREATE TABLE IF NOT EXISTS public.regulatory_impact_assessments (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to regulatory_impact_assessments
ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS document_id uuid NOT NULL REFERENCES public.regulatory_documents(id);

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS assessment_title text NOT NULL;

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS assessed_by_user_id uuid NOT NULL REFERENCES public.users(id);

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS assessment_date timestamp with time zone NOT NULL;

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS business_impact_level text NOT NULL; -- 'critical', 'high', 'medium', 'low', 'none'

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS customer_impact_level text NOT NULL;

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS cost_impact_estimate decimal(12,2);

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS implementation_effort text; -- 'low', 'medium', 'high', 'significant'

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS implementation_timeline text;

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS affected_business_units jsonb DEFAULT '[]';

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS affected_systems jsonb DEFAULT '[]';

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS required_actions jsonb DEFAULT '[]';

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS dependencies jsonb DEFAULT '[]';

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS risk_mitigation_plan text;

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'draft'; -- 'draft', 'reviewed', 'approved', 'implemented'

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS reviewed_by_user_id uuid REFERENCES public.users(id);

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS approved_by_user_id uuid REFERENCES public.users(id);

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- ============================================================================
-- AUDIT AND REPORTING
-- ============================================================================

-- Step 1: Create audit_logs table with primary key
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to audit_logs
ALTER TABLE public.audit_logs
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.audit_logs
    ADD COLUMN IF NOT EXISTS user_id uuid REFERENCES public.users(id);

ALTER TABLE public.audit_logs
    ADD COLUMN IF NOT EXISTS action text NOT NULL;

ALTER TABLE public.audit_logs
    ADD COLUMN IF NOT EXISTS resource_type text NOT NULL;

ALTER TABLE public.audit_logs
    ADD COLUMN IF NOT EXISTS resource_id uuid;

ALTER TABLE public.audit_logs
    ADD COLUMN IF NOT EXISTS old_values jsonb;

ALTER TABLE public.audit_logs
    ADD COLUMN IF NOT EXISTS new_values jsonb;

ALTER TABLE public.audit_logs
    ADD COLUMN IF NOT EXISTS ip_address inet;

ALTER TABLE public.audit_logs
    ADD COLUMN IF NOT EXISTS user_agent text;

ALTER TABLE public.audit_logs
    ADD COLUMN IF NOT EXISTS session_id text;

ALTER TABLE public.audit_logs
    ADD COLUMN IF NOT EXISTS additional_context jsonb DEFAULT '{}';

ALTER TABLE public.audit_logs
    ADD COLUMN IF NOT EXISTS timestamp timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create compliance_reports table with primary key
CREATE TABLE IF NOT EXISTS public.compliance_reports (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to compliance_reports
ALTER TABLE public.compliance_reports
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.compliance_reports
    ADD COLUMN IF NOT EXISTS report_name text NOT NULL;

ALTER TABLE public.compliance_reports
    ADD COLUMN IF NOT EXISTS report_type text NOT NULL; -- 'compliance_status', 'risk_assessment', 'audit_report', 'regulatory_filing'

ALTER TABLE public.compliance_reports
    ADD COLUMN IF NOT EXISTS reporting_period_start date NOT NULL;

ALTER TABLE public.compliance_reports
    ADD COLUMN IF NOT EXISTS reporting_period_end date NOT NULL;

ALTER TABLE public.compliance_reports
    ADD COLUMN IF NOT EXISTS generated_by_user_id uuid NOT NULL REFERENCES public.users(id);

ALTER TABLE public.compliance_reports
    ADD COLUMN IF NOT EXISTS generation_date timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.compliance_reports
    ADD COLUMN IF NOT EXISTS report_data jsonb NOT NULL DEFAULT '{}';

ALTER TABLE public.compliance_reports
    ADD COLUMN IF NOT EXISTS executive_summary text;

ALTER TABLE public.compliance_reports
    ADD COLUMN IF NOT EXISTS key_findings jsonb DEFAULT '[]';

ALTER TABLE public.compliance_reports
    ADD COLUMN IF NOT EXISTS recommendations jsonb DEFAULT '[]';

ALTER TABLE public.compliance_reports
    ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'draft'; -- 'draft', 'final', 'submitted'

ALTER TABLE public.compliance_reports
    ADD COLUMN IF NOT EXISTS file_path text;

ALTER TABLE public.compliance_reports
    ADD COLUMN IF NOT EXISTS digital_signature text;

ALTER TABLE public.compliance_reports
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

-- ============================================================================
-- AI AND ANALYTICS
-- ============================================================================

-- Step 1: Create ai_model_runs table with primary key
CREATE TABLE IF NOT EXISTS public.ai_model_runs (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to ai_model_runs
ALTER TABLE public.ai_model_runs
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.ai_model_runs
    ADD COLUMN IF NOT EXISTS model_name text NOT NULL;

ALTER TABLE public.ai_model_runs
    ADD COLUMN IF NOT EXISTS model_version text NOT NULL;

ALTER TABLE public.ai_model_runs
    ADD COLUMN IF NOT EXISTS input_data jsonb NOT NULL;

ALTER TABLE public.ai_model_runs
    ADD COLUMN IF NOT EXISTS output_data jsonb;

ALTER TABLE public.ai_model_runs
    ADD COLUMN IF NOT EXISTS confidence_score decimal(5,4);

ALTER TABLE public.ai_model_runs
    ADD COLUMN IF NOT EXISTS processing_time_ms integer;

ALTER TABLE public.ai_model_runs
    ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'pending'; -- 'pending', 'completed', 'failed'

ALTER TABLE public.ai_model_runs
    ADD COLUMN IF NOT EXISTS error_message text;

ALTER TABLE public.ai_model_runs
    ADD COLUMN IF NOT EXISTS triggered_by_user_id uuid REFERENCES public.users(id);

ALTER TABLE public.ai_model_runs
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create regulatory_insights table with primary key
CREATE TABLE IF NOT EXISTS public.regulatory_insights (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to regulatory_insights
ALTER TABLE public.regulatory_insights
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.regulatory_insights
    ADD COLUMN IF NOT EXISTS document_id uuid NOT NULL REFERENCES public.regulatory_documents(id);

ALTER TABLE public.regulatory_insights
    ADD COLUMN IF NOT EXISTS insight_type text NOT NULL; -- 'summary', 'key_changes', 'impact_analysis', 'compliance_guidance'

ALTER TABLE public.regulatory_insights
    ADD COLUMN IF NOT EXISTS insight_text text NOT NULL;

ALTER TABLE public.regulatory_insights
    ADD COLUMN IF NOT EXISTS confidence_level decimal(5,4);

ALTER TABLE public.regulatory_insights
    ADD COLUMN IF NOT EXISTS ai_model_run_id uuid REFERENCES public.ai_model_runs(id);

ALTER TABLE public.regulatory_insights
    ADD COLUMN IF NOT EXISTS validated_by_user_id uuid REFERENCES public.users(id);

ALTER TABLE public.regulatory_insights
    ADD COLUMN IF NOT EXISTS validation_status text DEFAULT 'pending'; -- 'pending', 'validated', 'rejected'

ALTER TABLE public.regulatory_insights
    ADD COLUMN IF NOT EXISTS validation_notes text;

ALTER TABLE public.regulatory_insights
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Core indexes for multi-tenant queries
CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON public.users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_customers_tenant_id ON public.customers(tenant_id);
CREATE INDEX IF NOT EXISTS idx_transactions_tenant_id ON public.transactions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_compliance_tasks_tenant_id ON public.compliance_tasks(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_id ON public.audit_logs(tenant_id);

-- Performance indexes for common queries
CREATE INDEX IF NOT EXISTS idx_regulatory_documents_publication_date ON public.regulatory_documents(publication_date DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON public.transactions(transaction_date DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_customer_id ON public.transactions(customer_id);
CREATE INDEX IF NOT EXISTS idx_compliance_tasks_due_date ON public.compliance_tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_compliance_tasks_assigned_to ON public.compliance_tasks(assigned_to_user_id);
CREATE INDEX IF NOT EXISTS idx_customers_risk_rating ON public.customers(risk_rating);
CREATE INDEX IF NOT EXISTS idx_customers_kyc_status ON public.customers(kyc_status);

-- Compliance monitoring indexes
CREATE INDEX IF NOT EXISTS idx_transactions_aml_status ON public.transactions(aml_status);
CREATE INDEX IF NOT EXISTS idx_compliance_requirements_status ON public.compliance_requirements(compliance_status);
CREATE INDEX IF NOT EXISTS idx_regulatory_documents_impact_level ON public.regulatory_documents(impact_level);

-- ============================================================================
-- ROW LEVEL SECURITY POLICIES
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.compliance_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.compliance_requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.compliance_reports ENABLE ROW LEVEL SECURITY;

-- Basic tenant isolation policies (to be expanded based on authentication system)
CREATE POLICY "tenant_isolation_users" ON public.users
    FOR ALL USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY "tenant_isolation_customers" ON public.customers
    FOR ALL USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY "tenant_isolation_transactions" ON public.transactions
    FOR ALL USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- ============================================================================
-- TRIGGERS FOR AUDIT LOGGING
-- ============================================================================

-- Function to automatically update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers to relevant tables
CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON public.tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON public.customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_compliance_programs_updated_at BEFORE UPDATE ON public.compliance_programs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_compliance_requirements_updated_at BEFORE UPDATE ON public.compliance_requirements
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_compliance_tasks_updated_at BEFORE UPDATE ON public.compliance_tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_regulatory_impact_assessments_updated_at BEFORE UPDATE ON public.regulatory_impact_assessments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SCHEMA VALIDATION AND CONSTRAINTS
-- ============================================================================

-- Add check constraints for data integrity
ALTER TABLE public.users ADD CONSTRAINT chk_user_role 
    CHECK (role IN ('admin', 'compliance_officer', 'analyst', 'auditor', 'manager', 'viewer'));

ALTER TABLE public.customers ADD CONSTRAINT chk_customer_risk_rating 
    CHECK (risk_rating IN ('low', 'medium', 'high'));

ALTER TABLE public.customers ADD CONSTRAINT chk_kyc_status 
    CHECK (kyc_status IN ('verified', 'rejected', 'pending', 'expired'));

ALTER TABLE public.transactions ADD CONSTRAINT chk_aml_status 
    CHECK (aml_status IN ('clear', 'flagged', 'investigated', 'reported'));

ALTER TABLE public.compliance_tasks ADD CONSTRAINT chk_task_priority 
    CHECK (priority IN ('critical', 'high', 'medium', 'low'));

ALTER TABLE public.compliance_tasks ADD CONSTRAINT chk_task_status 
    CHECK (status IN ('assigned', 'in_progress', 'completed', 'overdue', 'cancelled'));

-- ============================================================================
-- SEED DATA FOR REGULATORY SOURCES
-- ============================================================================

-- Insert major regulatory sources
INSERT INTO public.regulatory_sources (name, type, country_code, jurisdiction, website_url, monitoring_enabled) VALUES
    ('Securities and Exchange Commission', 'regulator', 'US', 'Federal', 'https://www.sec.gov', true),
    ('Federal Reserve', 'regulator', 'US', 'Federal', 'https://www.federalreserve.gov', true),
    ('Financial Conduct Authority', 'regulator', 'GB', 'UK', 'https://www.fca.org.uk', true),
    ('European Central Bank', 'regulator', 'EU', 'European Union', 'https://www.ecb.europa.eu', true),
    ('Bank for International Settlements', 'regulator', 'CH', 'International', 'https://www.bis.org', true),
    ('Financial Crimes Enforcement Network', 'regulator', 'US', 'Federal', 'https://www.fincen.gov', true),
    ('Australian Prudential Regulation Authority', 'regulator', 'AU', 'Federal', 'https://www.apra.gov.au', true),
    ('Monetary Authority of Singapore', 'regulator', 'SG', 'National', 'https://www.mas.gov.sg', true)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON SCHEMA public IS 'Regulens AI Financial Compliance Platform - Enterprise Database Schema';

COMMENT ON TABLE public.tenants IS 'Multi-tenant organization management with regulatory jurisdiction configuration';
COMMENT ON TABLE public.users IS 'User management with role-based access control and audit trails';
COMMENT ON TABLE public.regulatory_sources IS 'Global regulatory authorities and monitoring configuration';
COMMENT ON TABLE public.regulatory_documents IS 'Regulatory publications with AI-powered analysis and version tracking';
COMMENT ON TABLE public.regulatory_obligations IS 'Extracted compliance obligations with automatic interpretation';
COMMENT ON TABLE public.compliance_programs IS 'Organizational compliance program management and oversight';
COMMENT ON TABLE public.compliance_requirements IS 'Mapped compliance requirements with testing and evidence tracking';
COMMENT ON TABLE public.customers IS 'Customer database with KYC/AML status and risk profiling';
COMMENT ON TABLE public.transactions IS 'Transaction monitoring with suspicious activity detection';
COMMENT ON TABLE public.suspicious_activity_reports IS 'SAR filing and regulatory reporting management';
COMMENT ON TABLE public.compliance_tasks IS 'Workflow management for compliance activities and assignments';
COMMENT ON TABLE public.regulatory_impact_assessments IS 'Business impact analysis for regulatory changes';
COMMENT ON TABLE public.audit_logs IS 'Comprehensive audit trail for compliance and security monitoring';
COMMENT ON TABLE public.compliance_reports IS 'Automated compliance reporting with digital signatures';
COMMENT ON TABLE public.ai_model_runs IS 'AI/ML model execution tracking for regulatory intelligence';
COMMENT ON TABLE public.regulatory_insights IS 'AI-generated regulatory insights with human validation';

-- ============================================================================
-- PHASE 2: REGULATORY ENGINE TABLES
-- ============================================================================

-- Step 1: Create scheduled_tasks table with primary key
CREATE TABLE IF NOT EXISTS public.scheduled_tasks (
    id text PRIMARY KEY
);

-- Step 2: Add remaining fields to scheduled_tasks
ALTER TABLE public.scheduled_tasks
    ADD COLUMN IF NOT EXISTS name text NOT NULL;

ALTER TABLE public.scheduled_tasks
    ADD COLUMN IF NOT EXISTS task_type text NOT NULL;

ALTER TABLE public.scheduled_tasks
    ADD COLUMN IF NOT EXISTS source_id text;

ALTER TABLE public.scheduled_tasks
    ADD COLUMN IF NOT EXISTS interval_minutes integer NOT NULL;

ALTER TABLE public.scheduled_tasks
    ADD COLUMN IF NOT EXISTS priority text NOT NULL DEFAULT 'normal';

ALTER TABLE public.scheduled_tasks
    ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'scheduled';

ALTER TABLE public.scheduled_tasks
    ADD COLUMN IF NOT EXISTS last_run timestamp with time zone;

ALTER TABLE public.scheduled_tasks
    ADD COLUMN IF NOT EXISTS next_run timestamp with time zone;

ALTER TABLE public.scheduled_tasks
    ADD COLUMN IF NOT EXISTS failure_count integer NOT NULL DEFAULT 0;

ALTER TABLE public.scheduled_tasks
    ADD COLUMN IF NOT EXISTS max_failures integer NOT NULL DEFAULT 3;

ALTER TABLE public.scheduled_tasks
    ADD COLUMN IF NOT EXISTS timeout_seconds integer NOT NULL DEFAULT 300;

ALTER TABLE public.scheduled_tasks
    ADD COLUMN IF NOT EXISTS retry_delay_minutes integer NOT NULL DEFAULT 5;

ALTER TABLE public.scheduled_tasks
    ADD COLUMN IF NOT EXISTS enabled boolean NOT NULL DEFAULT true;

ALTER TABLE public.scheduled_tasks
    ADD COLUMN IF NOT EXISTS task_data text;

ALTER TABLE public.scheduled_tasks
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now();

ALTER TABLE public.scheduled_tasks
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now();

-- Step 1: Create task_executions table with primary key
CREATE TABLE IF NOT EXISTS public.task_executions (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to task_executions
ALTER TABLE public.task_executions
    ADD COLUMN IF NOT EXISTS task_id text NOT NULL;

ALTER TABLE public.task_executions
    ADD COLUMN IF NOT EXISTS status text NOT NULL;

ALTER TABLE public.task_executions
    ADD COLUMN IF NOT EXISTS started_at timestamp with time zone NOT NULL;

ALTER TABLE public.task_executions
    ADD COLUMN IF NOT EXISTS completed_at timestamp with time zone;

ALTER TABLE public.task_executions
    ADD COLUMN IF NOT EXISTS duration_seconds numeric;

ALTER TABLE public.task_executions
    ADD COLUMN IF NOT EXISTS result jsonb;

ALTER TABLE public.task_executions
    ADD COLUMN IF NOT EXISTS error_message text;

ALTER TABLE public.task_executions
    ADD COLUMN IF NOT EXISTS retry_count integer DEFAULT 0;

-- Step 1: Create document_embeddings table with primary key
CREATE TABLE IF NOT EXISTS public.document_embeddings (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to document_embeddings
ALTER TABLE public.document_embeddings
    ADD COLUMN IF NOT EXISTS document_id uuid NOT NULL;

ALTER TABLE public.document_embeddings
    ADD COLUMN IF NOT EXISTS embeddings_vector vector(384);

ALTER TABLE public.document_embeddings
    ADD COLUMN IF NOT EXISTS model_name text NOT NULL;

ALTER TABLE public.document_embeddings
    ADD COLUMN IF NOT EXISTS model_version text NOT NULL;

ALTER TABLE public.document_embeddings
    ADD COLUMN IF NOT EXISTS text_excerpt text;

ALTER TABLE public.document_embeddings
    ADD COLUMN IF NOT EXISTS metadata jsonb DEFAULT '{}';

ALTER TABLE public.document_embeddings
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now();

-- Step 1: Create document_similarity table with primary key
CREATE TABLE IF NOT EXISTS public.document_similarity (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to document_similarity
ALTER TABLE public.document_similarity
    ADD COLUMN IF NOT EXISTS document_a_id uuid NOT NULL;

ALTER TABLE public.document_similarity
    ADD COLUMN IF NOT EXISTS document_b_id uuid NOT NULL;

ALTER TABLE public.document_similarity
    ADD COLUMN IF NOT EXISTS similarity_score numeric(5,4) NOT NULL;

ALTER TABLE public.document_similarity
    ADD COLUMN IF NOT EXISTS calculation_method text NOT NULL DEFAULT 'cosine';

ALTER TABLE public.document_similarity
    ADD COLUMN IF NOT EXISTS calculated_at timestamp with time zone DEFAULT now();

-- Step 1: Create regulatory_changes table with primary key
CREATE TABLE IF NOT EXISTS public.regulatory_changes (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to regulatory_changes
ALTER TABLE public.regulatory_changes
    ADD COLUMN IF NOT EXISTS document_id uuid NOT NULL;

ALTER TABLE public.regulatory_changes
    ADD COLUMN IF NOT EXISTS change_type text NOT NULL;

ALTER TABLE public.regulatory_changes
    ADD COLUMN IF NOT EXISTS change_description text NOT NULL;

ALTER TABLE public.regulatory_changes
    ADD COLUMN IF NOT EXISTS impact_level text NOT NULL DEFAULT 'medium';

ALTER TABLE public.regulatory_changes
    ADD COLUMN IF NOT EXISTS effective_date timestamp with time zone;

ALTER TABLE public.regulatory_changes
    ADD COLUMN IF NOT EXISTS compliance_deadline timestamp with time zone;

ALTER TABLE public.regulatory_changes
    ADD COLUMN IF NOT EXISTS affected_entities jsonb DEFAULT '[]';

ALTER TABLE public.regulatory_changes
    ADD COLUMN IF NOT EXISTS implementation_guidance text;

ALTER TABLE public.regulatory_changes
    ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'active';

ALTER TABLE public.regulatory_changes
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now();

ALTER TABLE public.regulatory_changes
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now();

-- Step 1: Create monitoring_alerts table with primary key
CREATE TABLE IF NOT EXISTS public.monitoring_alerts (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to monitoring_alerts
ALTER TABLE public.monitoring_alerts
    ADD COLUMN IF NOT EXISTS alert_type text NOT NULL;

ALTER TABLE public.monitoring_alerts
    ADD COLUMN IF NOT EXISTS severity text NOT NULL;

ALTER TABLE public.monitoring_alerts
    ADD COLUMN IF NOT EXISTS title text NOT NULL;

ALTER TABLE public.monitoring_alerts
    ADD COLUMN IF NOT EXISTS description text NOT NULL;

ALTER TABLE public.monitoring_alerts
    ADD COLUMN IF NOT EXISTS source_id uuid;

ALTER TABLE public.monitoring_alerts
    ADD COLUMN IF NOT EXISTS document_id uuid;

ALTER TABLE public.monitoring_alerts
    ADD COLUMN IF NOT EXISTS alert_data jsonb DEFAULT '{}';

ALTER TABLE public.monitoring_alerts
    ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'active';

ALTER TABLE public.monitoring_alerts
    ADD COLUMN IF NOT EXISTS acknowledged_at timestamp with time zone;

ALTER TABLE public.monitoring_alerts
    ADD COLUMN IF NOT EXISTS acknowledged_by uuid;

ALTER TABLE public.monitoring_alerts
    ADD COLUMN IF NOT EXISTS resolved_at timestamp with time zone;

ALTER TABLE public.monitoring_alerts
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now();

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_next_run ON public.scheduled_tasks(next_run);
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_status ON public.scheduled_tasks(status);
CREATE INDEX IF NOT EXISTS idx_task_executions_task_id ON public.task_executions(task_id);
CREATE INDEX IF NOT EXISTS idx_document_embeddings_document_id ON public.document_embeddings(document_id);
CREATE INDEX IF NOT EXISTS idx_document_similarity_doc_a ON public.document_similarity(document_a_id);
CREATE INDEX IF NOT EXISTS idx_document_similarity_doc_b ON public.document_similarity(document_b_id);
CREATE INDEX IF NOT EXISTS idx_regulatory_changes_document_id ON public.regulatory_changes(document_id);
CREATE INDEX IF NOT EXISTS idx_regulatory_changes_effective_date ON public.regulatory_changes(effective_date);
CREATE INDEX IF NOT EXISTS idx_monitoring_alerts_status ON public.monitoring_alerts(status);
CREATE INDEX IF NOT EXISTS idx_monitoring_alerts_created_at ON public.monitoring_alerts(created_at);

-- Foreign key constraints
ALTER TABLE public.task_executions 
    ADD CONSTRAINT fk_task_executions_task_id 
    FOREIGN KEY (task_id) REFERENCES public.scheduled_tasks(id) ON DELETE CASCADE;

ALTER TABLE public.document_embeddings 
    ADD CONSTRAINT fk_document_embeddings_document_id 
    FOREIGN KEY (document_id) REFERENCES public.regulatory_documents(id) ON DELETE CASCADE;

ALTER TABLE public.document_similarity 
    ADD CONSTRAINT fk_document_similarity_doc_a 
    FOREIGN KEY (document_a_id) REFERENCES public.regulatory_documents(id) ON DELETE CASCADE;

ALTER TABLE public.document_similarity 
    ADD CONSTRAINT fk_document_similarity_doc_b 
    FOREIGN KEY (document_b_id) REFERENCES public.regulatory_documents(id) ON DELETE CASCADE;

ALTER TABLE public.regulatory_changes 
    ADD CONSTRAINT fk_regulatory_changes_document_id 
    FOREIGN KEY (document_id) REFERENCES public.regulatory_documents(id) ON DELETE CASCADE;

ALTER TABLE public.monitoring_alerts 
    ADD CONSTRAINT fk_monitoring_alerts_source_id 
    FOREIGN KEY (source_id) REFERENCES public.regulatory_sources(id) ON DELETE SET NULL;

ALTER TABLE public.monitoring_alerts 
    ADD CONSTRAINT fk_monitoring_alerts_document_id 
    FOREIGN KEY (document_id) REFERENCES public.regulatory_documents(id) ON DELETE SET NULL;

ALTER TABLE public.monitoring_alerts 
    ADD CONSTRAINT fk_monitoring_alerts_acknowledged_by 
    FOREIGN KEY (acknowledged_by) REFERENCES public.users(id) ON DELETE SET NULL;

-- Add check constraints
ALTER TABLE public.scheduled_tasks ADD CONSTRAINT chk_task_priority 
    CHECK (priority IN ('critical', 'high', 'normal', 'low'));

ALTER TABLE public.scheduled_tasks ADD CONSTRAINT chk_task_status 
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'scheduled'));

ALTER TABLE public.task_executions ADD CONSTRAINT chk_execution_status 
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled'));

ALTER TABLE public.regulatory_changes ADD CONSTRAINT chk_change_impact_level 
    CHECK (impact_level IN ('critical', 'high', 'medium', 'low', 'none'));

ALTER TABLE public.regulatory_changes ADD CONSTRAINT chk_change_status 
    CHECK (status IN ('active', 'superseded', 'withdrawn', 'pending'));

ALTER TABLE public.monitoring_alerts ADD CONSTRAINT chk_alert_severity 
    CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info'));

ALTER TABLE public.monitoring_alerts ADD CONSTRAINT chk_alert_status 
    CHECK (status IN ('active', 'acknowledged', 'resolved', 'dismissed'));

-- Update regulatory_sources table to add RSS feed URL field
ALTER TABLE public.regulatory_sources
    ADD COLUMN IF NOT EXISTS rss_feed_url text;

ALTER TABLE public.regulatory_sources
    ADD COLUMN IF NOT EXISTS api_endpoint text;

ALTER TABLE public.regulatory_sources
    ADD COLUMN IF NOT EXISTS last_monitored timestamp with time zone;

-- Update regulatory_documents table to add AI analysis field
ALTER TABLE public.regulatory_documents
    ADD COLUMN IF NOT EXISTS ai_analysis jsonb DEFAULT '{}';

ALTER TABLE public.regulatory_documents
    ADD COLUMN IF NOT EXISTS processing_status text DEFAULT 'pending';

-- Add check constraint for processing status
ALTER TABLE public.regulatory_documents ADD CONSTRAINT chk_processing_status 
    CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed'));

-- Update ai_model_runs table for tracking embeddings and analysis
ALTER TABLE public.ai_model_runs
    ADD COLUMN IF NOT EXISTS processing_time_ms integer;

ALTER TABLE public.ai_model_runs
    ADD COLUMN IF NOT EXISTS token_count integer;

ALTER TABLE public.ai_model_runs
    ADD COLUMN IF NOT EXISTS cost_estimate numeric(10,4);

-- Comments for Phase 2 tables
COMMENT ON TABLE public.scheduled_tasks IS 'Background task scheduling and execution management for regulatory monitoring';
COMMENT ON TABLE public.task_executions IS 'Individual task execution records with performance metrics and error tracking';
COMMENT ON TABLE public.document_embeddings IS 'Vector embeddings for regulatory documents enabling semantic search and similarity';
COMMENT ON TABLE public.document_similarity IS 'Pre-calculated similarity scores between regulatory documents for fast retrieval';
COMMENT ON TABLE public.regulatory_changes IS 'Tracked regulatory changes with impact assessment and implementation guidance';
COMMENT ON TABLE public.monitoring_alerts IS 'Real-time alerts for regulatory changes requiring immediate attention';

-- ============================================================================
-- PHASE 3: COMPLIANCE WORKFLOWS TABLES
-- ============================================================================

-- Step 1: Create workflow_definitions table with primary key
CREATE TABLE IF NOT EXISTS public.workflow_definitions (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to workflow_definitions
ALTER TABLE public.workflow_definitions
    ADD COLUMN IF NOT EXISTS name text NOT NULL;

ALTER TABLE public.workflow_definitions
    ADD COLUMN IF NOT EXISTS description text NOT NULL DEFAULT '';

ALTER TABLE public.workflow_definitions
    ADD COLUMN IF NOT EXISTS version text NOT NULL DEFAULT '1.0';

ALTER TABLE public.workflow_definitions
    ADD COLUMN IF NOT EXISTS category text NOT NULL DEFAULT 'general';

ALTER TABLE public.workflow_definitions
    ADD COLUMN IF NOT EXISTS tasks_definition jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.workflow_definitions
    ADD COLUMN IF NOT EXISTS triggers jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.workflow_definitions
    ADD COLUMN IF NOT EXISTS flow_logic jsonb NOT NULL DEFAULT '{}';

ALTER TABLE public.workflow_definitions
    ADD COLUMN IF NOT EXISTS default_variables jsonb NOT NULL DEFAULT '{}';

ALTER TABLE public.workflow_definitions
    ADD COLUMN IF NOT EXISTS settings jsonb NOT NULL DEFAULT '{}';

ALTER TABLE public.workflow_definitions
    ADD COLUMN IF NOT EXISTS is_active boolean NOT NULL DEFAULT true;

ALTER TABLE public.workflow_definitions
    ADD COLUMN IF NOT EXISTS created_by text NOT NULL DEFAULT 'system';

ALTER TABLE public.workflow_definitions
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.workflow_definitions
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create workflow_executions table with primary key
CREATE TABLE IF NOT EXISTS public.workflow_executions (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to workflow_executions
ALTER TABLE public.workflow_executions
    ADD COLUMN IF NOT EXISTS definition_id uuid NOT NULL;

ALTER TABLE public.workflow_executions
    ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'active';

ALTER TABLE public.workflow_executions
    ADD COLUMN IF NOT EXISTS current_tasks jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.workflow_executions
    ADD COLUMN IF NOT EXISTS completed_tasks jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.workflow_executions
    ADD COLUMN IF NOT EXISTS failed_tasks jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.workflow_executions
    ADD COLUMN IF NOT EXISTS context_data jsonb NOT NULL DEFAULT '{}';

ALTER TABLE public.workflow_executions
    ADD COLUMN IF NOT EXISTS started_at timestamp with time zone NOT NULL;

ALTER TABLE public.workflow_executions
    ADD COLUMN IF NOT EXISTS completed_at timestamp with time zone;

ALTER TABLE public.workflow_executions
    ADD COLUMN IF NOT EXISTS last_activity_at timestamp with time zone;

ALTER TABLE public.workflow_executions
    ADD COLUMN IF NOT EXISTS progress_percentage numeric(5,2) DEFAULT 0.0;

ALTER TABLE public.workflow_executions
    ADD COLUMN IF NOT EXISTS error_message text;

-- Step 1: Create workflow_triggers table with primary key
CREATE TABLE IF NOT EXISTS public.workflow_triggers (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to workflow_triggers
ALTER TABLE public.workflow_triggers
    ADD COLUMN IF NOT EXISTS name text NOT NULL;

ALTER TABLE public.workflow_triggers
    ADD COLUMN IF NOT EXISTS trigger_type text NOT NULL;

ALTER TABLE public.workflow_triggers
    ADD COLUMN IF NOT EXISTS workflow_definition_id uuid NOT NULL;

ALTER TABLE public.workflow_triggers
    ADD COLUMN IF NOT EXISTS conditions jsonb NOT NULL DEFAULT '{}';

ALTER TABLE public.workflow_triggers
    ADD COLUMN IF NOT EXISTS enabled boolean NOT NULL DEFAULT true;

ALTER TABLE public.workflow_triggers
    ADD COLUMN IF NOT EXISTS priority integer NOT NULL DEFAULT 1;

ALTER TABLE public.workflow_triggers
    ADD COLUMN IF NOT EXISTS cooldown_minutes integer NOT NULL DEFAULT 0;

ALTER TABLE public.workflow_triggers
    ADD COLUMN IF NOT EXISTS last_triggered timestamp with time zone;

ALTER TABLE public.workflow_triggers
    ADD COLUMN IF NOT EXISTS metadata jsonb DEFAULT '{}';

ALTER TABLE public.workflow_triggers
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.workflow_triggers
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create workflow_tasks table with primary key
CREATE TABLE IF NOT EXISTS public.workflow_tasks (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to workflow_tasks
ALTER TABLE public.workflow_tasks
    ADD COLUMN IF NOT EXISTS workflow_id uuid NOT NULL;

ALTER TABLE public.workflow_tasks
    ADD COLUMN IF NOT EXISTS name text NOT NULL;

ALTER TABLE public.workflow_tasks
    ADD COLUMN IF NOT EXISTS type text NOT NULL;

ALTER TABLE public.workflow_tasks
    ADD COLUMN IF NOT EXISTS description text NOT NULL DEFAULT '';

ALTER TABLE public.workflow_tasks
    ADD COLUMN IF NOT EXISTS priority text NOT NULL DEFAULT 'medium';

ALTER TABLE public.workflow_tasks
    ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'pending';

ALTER TABLE public.workflow_tasks
    ADD COLUMN IF NOT EXISTS assignee_role text;

ALTER TABLE public.workflow_tasks
    ADD COLUMN IF NOT EXISTS assignee_user_id uuid;

ALTER TABLE public.workflow_tasks
    ADD COLUMN IF NOT EXISTS due_date timestamp with time zone;

ALTER TABLE public.workflow_tasks
    ADD COLUMN IF NOT EXISTS estimated_duration_hours numeric(8,2);

ALTER TABLE public.workflow_tasks
    ADD COLUMN IF NOT EXISTS actual_duration_hours numeric(8,2);

ALTER TABLE public.workflow_tasks
    ADD COLUMN IF NOT EXISTS requires_approval boolean DEFAULT false;

ALTER TABLE public.workflow_tasks
    ADD COLUMN IF NOT EXISTS task_config jsonb DEFAULT '{}';

ALTER TABLE public.workflow_tasks
    ADD COLUMN IF NOT EXISTS result_data jsonb DEFAULT '{}';

ALTER TABLE public.workflow_tasks
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.workflow_tasks
    ADD COLUMN IF NOT EXISTS started_at timestamp with time zone;

ALTER TABLE public.workflow_tasks
    ADD COLUMN IF NOT EXISTS completed_at timestamp with time zone;

ALTER TABLE public.workflow_tasks
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create regulatory_impact_assessments table with primary key
CREATE TABLE IF NOT EXISTS public.regulatory_impact_assessments (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to regulatory_impact_assessments
ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS regulation_id uuid NOT NULL;

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS regulation_title text NOT NULL;

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS impact_level text NOT NULL DEFAULT 'medium';

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS impact_categories jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS affected_business_units jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS affected_systems jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS affected_processes jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS implementation_effort text NOT NULL DEFAULT 'medium';

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS estimated_cost numeric(12,2);

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS estimated_timeline text;

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS compliance_deadline timestamp with time zone;

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS required_actions jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS risk_factors jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS mitigation_strategies jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS dependencies jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS confidence_score numeric(3,2) NOT NULL DEFAULT 0.5;

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS assessment_rationale text NOT NULL DEFAULT '';

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS similar_regulations jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS created_by text NOT NULL DEFAULT 'system';

ALTER TABLE public.regulatory_impact_assessments
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Update compliance_tasks table to match new workflow system
ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS workflow_id uuid;

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS parent_task_id uuid;

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS subtasks jsonb DEFAULT '[]';

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS assignment_data jsonb;

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS progress_percentage numeric(5,2) DEFAULT 0.0;

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS estimated_effort_hours numeric(8,2);

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS actual_effort_hours numeric(8,2);

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS requirements jsonb DEFAULT '[]';

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS acceptance_criteria jsonb DEFAULT '[]';

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS required_approvals jsonb DEFAULT '[]';

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS required_evidence jsonb DEFAULT '[]';

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS regulatory_reference text;

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS business_justification text DEFAULT '';

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS dependencies jsonb DEFAULT '[]';

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS evidence jsonb DEFAULT '[]';

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS comments jsonb DEFAULT '[]';

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS tags jsonb DEFAULT '[]';

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS metadata jsonb DEFAULT '{}';

ALTER TABLE public.compliance_tasks
    ADD COLUMN IF NOT EXISTS started_at timestamp with time zone;

-- Add indexes for Phase 3 tables
CREATE INDEX IF NOT EXISTS idx_workflow_definitions_category ON public.workflow_definitions(category);
CREATE INDEX IF NOT EXISTS idx_workflow_definitions_active ON public.workflow_definitions(is_active);

CREATE INDEX IF NOT EXISTS idx_workflow_executions_definition ON public.workflow_executions(definition_id);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_status ON public.workflow_executions(status);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_started ON public.workflow_executions(started_at);

CREATE INDEX IF NOT EXISTS idx_workflow_triggers_type ON public.workflow_triggers(trigger_type);
CREATE INDEX IF NOT EXISTS idx_workflow_triggers_enabled ON public.workflow_triggers(enabled);
CREATE INDEX IF NOT EXISTS idx_workflow_triggers_definition ON public.workflow_triggers(workflow_definition_id);

CREATE INDEX IF NOT EXISTS idx_workflow_tasks_workflow ON public.workflow_tasks(workflow_id);
CREATE INDEX IF NOT EXISTS idx_workflow_tasks_status ON public.workflow_tasks(status);
CREATE INDEX IF NOT EXISTS idx_workflow_tasks_assignee ON public.workflow_tasks(assignee_user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_tasks_due_date ON public.workflow_tasks(due_date);

CREATE INDEX IF NOT EXISTS idx_impact_assessments_regulation ON public.regulatory_impact_assessments(regulation_id);
CREATE INDEX IF NOT EXISTS idx_impact_assessments_level ON public.regulatory_impact_assessments(impact_level);
CREATE INDEX IF NOT EXISTS idx_impact_assessments_created ON public.regulatory_impact_assessments(created_at);

CREATE INDEX IF NOT EXISTS idx_compliance_tasks_workflow ON public.compliance_tasks(workflow_id);
CREATE INDEX IF NOT EXISTS idx_compliance_tasks_parent ON public.compliance_tasks(parent_task_id);
CREATE INDEX IF NOT EXISTS idx_compliance_tasks_regulatory_ref ON public.compliance_tasks(regulatory_reference);

-- Foreign key constraints for Phase 3
ALTER TABLE public.workflow_executions 
    ADD CONSTRAINT fk_workflow_executions_definition 
    FOREIGN KEY (definition_id) REFERENCES public.workflow_definitions(id) ON DELETE CASCADE;

ALTER TABLE public.workflow_triggers 
    ADD CONSTRAINT fk_workflow_triggers_definition 
    FOREIGN KEY (workflow_definition_id) REFERENCES public.workflow_definitions(id) ON DELETE CASCADE;

ALTER TABLE public.workflow_tasks 
    ADD CONSTRAINT fk_workflow_tasks_execution 
    FOREIGN KEY (workflow_id) REFERENCES public.workflow_executions(id) ON DELETE CASCADE;

ALTER TABLE public.workflow_tasks 
    ADD CONSTRAINT fk_workflow_tasks_assignee 
    FOREIGN KEY (assignee_user_id) REFERENCES public.users(id) ON DELETE SET NULL;

ALTER TABLE public.regulatory_impact_assessments 
    ADD CONSTRAINT fk_impact_assessments_regulation 
    FOREIGN KEY (regulation_id) REFERENCES public.regulatory_documents(id) ON DELETE CASCADE;

ALTER TABLE public.compliance_tasks 
    ADD CONSTRAINT fk_compliance_tasks_workflow 
    FOREIGN KEY (workflow_id) REFERENCES public.workflow_executions(id) ON DELETE SET NULL;

ALTER TABLE public.compliance_tasks 
    ADD CONSTRAINT fk_compliance_tasks_parent 
    FOREIGN KEY (parent_task_id) REFERENCES public.compliance_tasks(id) ON DELETE SET NULL;

-- Add check constraints for Phase 3
ALTER TABLE public.workflow_executions ADD CONSTRAINT chk_workflow_status 
    CHECK (status IN ('draft', 'active', 'paused', 'completed', 'failed', 'cancelled', 'expired'));

ALTER TABLE public.workflow_triggers ADD CONSTRAINT chk_trigger_type 
    CHECK (trigger_type IN ('regulatory_change', 'scheduled', 'manual', 'threshold_breach', 
                           'deadline_approaching', 'task_completion', 'approval_required', 
                           'compliance_violation', 'system_event'));

ALTER TABLE public.workflow_tasks ADD CONSTRAINT chk_workflow_task_priority 
    CHECK (priority IN ('critical', 'high', 'medium', 'low'));

ALTER TABLE public.workflow_tasks ADD CONSTRAINT chk_workflow_task_status 
    CHECK (status IN ('pending', 'assigned', 'in_progress', 'waiting_review', 
                     'waiting_approval', 'completed', 'overdue', 'cancelled', 'failed'));

ALTER TABLE public.regulatory_impact_assessments ADD CONSTRAINT chk_impact_level 
    CHECK (impact_level IN ('critical', 'high', 'medium', 'low', 'none'));

ALTER TABLE public.regulatory_impact_assessments ADD CONSTRAINT chk_implementation_effort 
    CHECK (implementation_effort IN ('low', 'medium', 'high', 'significant'));

-- Update compliance_tasks check constraints
ALTER TABLE public.compliance_tasks DROP CONSTRAINT IF EXISTS chk_task_status;
ALTER TABLE public.compliance_tasks ADD CONSTRAINT chk_task_status 
    CHECK (status IN ('draft', 'assigned', 'in_progress', 'waiting_review', 
                     'waiting_approval', 'completed', 'overdue', 'cancelled', 'failed'));

-- Comments for Phase 3 tables
COMMENT ON TABLE public.workflow_definitions IS 'Workflow definition templates with task flows and business logic';
COMMENT ON TABLE public.workflow_executions IS 'Active workflow execution instances with state and progress tracking';
COMMENT ON TABLE public.workflow_triggers IS 'Event-based triggers that automatically start workflows';
COMMENT ON TABLE public.workflow_tasks IS 'Individual workflow tasks with assignments and lifecycle management';
COMMENT ON TABLE public.regulatory_impact_assessments IS 'AI-powered impact assessments for regulatory changes';

-- ============================================================================
-- PHASE 4: ADVANCED ANALYTICS & INTELLIGENCE TABLES
-- ============================================================================

-- Step 1: Create risk_scoring_models table with primary key
CREATE TABLE IF NOT EXISTS public.risk_scoring_models (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to risk_scoring_models
ALTER TABLE public.risk_scoring_models
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.risk_scoring_models
    ADD COLUMN IF NOT EXISTS model_name text NOT NULL;

ALTER TABLE public.risk_scoring_models
    ADD COLUMN IF NOT EXISTS model_type text NOT NULL; -- 'credit_risk', 'operational_risk', 'market_risk', 'compliance_risk', 'fraud_risk'

ALTER TABLE public.risk_scoring_models
    ADD COLUMN IF NOT EXISTS model_version text NOT NULL DEFAULT '1.0';

ALTER TABLE public.risk_scoring_models
    ADD COLUMN IF NOT EXISTS algorithm_type text NOT NULL; -- 'logistic_regression', 'random_forest', 'neural_network', 'rule_based', 'ensemble'

ALTER TABLE public.risk_scoring_models
    ADD COLUMN IF NOT EXISTS model_parameters jsonb NOT NULL DEFAULT '{}';

ALTER TABLE public.risk_scoring_models
    ADD COLUMN IF NOT EXISTS feature_definitions jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.risk_scoring_models
    ADD COLUMN IF NOT EXISTS training_data_metadata jsonb NOT NULL DEFAULT '{}';

ALTER TABLE public.risk_scoring_models
    ADD COLUMN IF NOT EXISTS performance_metrics jsonb NOT NULL DEFAULT '{}';

ALTER TABLE public.risk_scoring_models
    ADD COLUMN IF NOT EXISTS validation_results jsonb NOT NULL DEFAULT '{}';

ALTER TABLE public.risk_scoring_models
    ADD COLUMN IF NOT EXISTS model_status text NOT NULL DEFAULT 'training'; -- 'training', 'testing', 'production', 'deprecated', 'failed'

ALTER TABLE public.risk_scoring_models
    ADD COLUMN IF NOT EXISTS deployment_date timestamp with time zone;

ALTER TABLE public.risk_scoring_models
    ADD COLUMN IF NOT EXISTS last_retrain_date timestamp with time zone;

ALTER TABLE public.risk_scoring_models
    ADD COLUMN IF NOT EXISTS next_review_date timestamp with time zone;

ALTER TABLE public.risk_scoring_models
    ADD COLUMN IF NOT EXISTS accuracy_threshold numeric(5,4) NOT NULL DEFAULT 0.8000;

ALTER TABLE public.risk_scoring_models
    ADD COLUMN IF NOT EXISTS current_accuracy numeric(5,4);

ALTER TABLE public.risk_scoring_models
    ADD COLUMN IF NOT EXISTS model_drift_score numeric(5,4) DEFAULT 0.0000;

ALTER TABLE public.risk_scoring_models
    ADD COLUMN IF NOT EXISTS created_by uuid NOT NULL REFERENCES public.users(id);

ALTER TABLE public.risk_scoring_models
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.risk_scoring_models
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create customer_risk_scores table with primary key
CREATE TABLE IF NOT EXISTS public.customer_risk_scores (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to customer_risk_scores
ALTER TABLE public.customer_risk_scores
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.customer_risk_scores
    ADD COLUMN IF NOT EXISTS customer_id uuid NOT NULL REFERENCES public.customers(id);

ALTER TABLE public.customer_risk_scores
    ADD COLUMN IF NOT EXISTS model_id uuid NOT NULL REFERENCES public.risk_scoring_models(id);

ALTER TABLE public.customer_risk_scores
    ADD COLUMN IF NOT EXISTS overall_risk_score numeric(5,2) NOT NULL;

ALTER TABLE public.customer_risk_scores
    ADD COLUMN IF NOT EXISTS credit_risk_score numeric(5,2);

ALTER TABLE public.customer_risk_scores
    ADD COLUMN IF NOT EXISTS fraud_risk_score numeric(5,2);

ALTER TABLE public.customer_risk_scores
    ADD COLUMN IF NOT EXISTS aml_risk_score numeric(5,2);

ALTER TABLE public.customer_risk_scores
    ADD COLUMN IF NOT EXISTS operational_risk_score numeric(5,2);

ALTER TABLE public.customer_risk_scores
    ADD COLUMN IF NOT EXISTS risk_grade text NOT NULL; -- 'AAA', 'AA', 'A', 'BBB', 'BB', 'B', 'CCC', 'CC', 'C', 'D'

ALTER TABLE public.customer_risk_scores
    ADD COLUMN IF NOT EXISTS risk_category text NOT NULL; -- 'low', 'medium', 'high', 'critical'

ALTER TABLE public.customer_risk_scores
    ADD COLUMN IF NOT EXISTS contributing_factors jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.customer_risk_scores
    ADD COLUMN IF NOT EXISTS risk_indicators jsonb NOT NULL DEFAULT '{}';

ALTER TABLE public.customer_risk_scores
    ADD COLUMN IF NOT EXISTS confidence_interval jsonb NOT NULL DEFAULT '{}';

ALTER TABLE public.customer_risk_scores
    ADD COLUMN IF NOT EXISTS probability_of_default numeric(5,4);

ALTER TABLE public.customer_risk_scores
    ADD COLUMN IF NOT EXISTS expected_loss numeric(12,2);

ALTER TABLE public.customer_risk_scores
    ADD COLUMN IF NOT EXISTS score_explanation text;

ALTER TABLE public.customer_risk_scores
    ADD COLUMN IF NOT EXISTS alerts_generated jsonb DEFAULT '[]';

ALTER TABLE public.customer_risk_scores
    ADD COLUMN IF NOT EXISTS review_required boolean DEFAULT false;

ALTER TABLE public.customer_risk_scores
    ADD COLUMN IF NOT EXISTS score_date timestamp with time zone NOT NULL;

ALTER TABLE public.customer_risk_scores
    ADD COLUMN IF NOT EXISTS expiry_date timestamp with time zone;

ALTER TABLE public.customer_risk_scores
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create transaction_risk_scores table with primary key
CREATE TABLE IF NOT EXISTS public.transaction_risk_scores (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to transaction_risk_scores
ALTER TABLE public.transaction_risk_scores
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.transaction_risk_scores
    ADD COLUMN IF NOT EXISTS transaction_id uuid NOT NULL REFERENCES public.transactions(id);

ALTER TABLE public.transaction_risk_scores
    ADD COLUMN IF NOT EXISTS model_id uuid NOT NULL REFERENCES public.risk_scoring_models(id);

ALTER TABLE public.transaction_risk_scores
    ADD COLUMN IF NOT EXISTS fraud_score numeric(5,2) NOT NULL;

ALTER TABLE public.transaction_risk_scores
    ADD COLUMN IF NOT EXISTS aml_score numeric(5,2) NOT NULL;

ALTER TABLE public.transaction_risk_scores
    ADD COLUMN IF NOT EXISTS sanctions_score numeric(5,2);

ALTER TABLE public.transaction_risk_scores
    ADD COLUMN IF NOT EXISTS pep_score numeric(5,2);

ALTER TABLE public.transaction_risk_scores
    ADD COLUMN IF NOT EXISTS behavioral_score numeric(5,2);

ALTER TABLE public.transaction_risk_scores
    ADD COLUMN IF NOT EXISTS velocity_score numeric(5,2);

ALTER TABLE public.transaction_risk_scores
    ADD COLUMN IF NOT EXISTS geographic_score numeric(5,2);

ALTER TABLE public.transaction_risk_scores
    ADD COLUMN IF NOT EXISTS overall_risk_score numeric(5,2) NOT NULL;

ALTER TABLE public.transaction_risk_scores
    ADD COLUMN IF NOT EXISTS risk_level text NOT NULL; -- 'low', 'medium', 'high', 'critical'

ALTER TABLE public.transaction_risk_scores
    ADD COLUMN IF NOT EXISTS risk_factors jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.transaction_risk_scores
    ADD COLUMN IF NOT EXISTS anomaly_indicators jsonb NOT NULL DEFAULT '{}';

ALTER TABLE public.transaction_risk_scores
    ADD COLUMN IF NOT EXISTS pattern_matches jsonb DEFAULT '[]';

ALTER TABLE public.transaction_risk_scores
    ADD COLUMN IF NOT EXISTS false_positive_probability numeric(5,4);

ALTER TABLE public.transaction_risk_scores
    ADD COLUMN IF NOT EXISTS investigation_priority integer DEFAULT 0;

ALTER TABLE public.transaction_risk_scores
    ADD COLUMN IF NOT EXISTS auto_decision text; -- 'approve', 'decline', 'review', 'escalate'

ALTER TABLE public.transaction_risk_scores
    ADD COLUMN IF NOT EXISTS score_explanation text;

ALTER TABLE public.transaction_risk_scores
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create compliance_metrics table with primary key
CREATE TABLE IF NOT EXISTS public.compliance_metrics (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to compliance_metrics
ALTER TABLE public.compliance_metrics
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.compliance_metrics
    ADD COLUMN IF NOT EXISTS metric_name text NOT NULL;

ALTER TABLE public.compliance_metrics
    ADD COLUMN IF NOT EXISTS metric_category text NOT NULL; -- 'aml', 'kyc', 'fraud', 'operational', 'regulatory', 'audit'

ALTER TABLE public.compliance_metrics
    ADD COLUMN IF NOT EXISTS metric_type text NOT NULL; -- 'kpi', 'threshold', 'ratio', 'count', 'percentage', 'score'

ALTER TABLE public.compliance_metrics
    ADD COLUMN IF NOT EXISTS calculation_method text NOT NULL;

ALTER TABLE public.compliance_metrics
    ADD COLUMN IF NOT EXISTS current_value numeric(15,4) NOT NULL;

ALTER TABLE public.compliance_metrics
    ADD COLUMN IF NOT EXISTS target_value numeric(15,4);

ALTER TABLE public.compliance_metrics
    ADD COLUMN IF NOT EXISTS threshold_warning numeric(15,4);

ALTER TABLE public.compliance_metrics
    ADD COLUMN IF NOT EXISTS threshold_critical numeric(15,4);

ALTER TABLE public.compliance_metrics
    ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'normal'; -- 'normal', 'warning', 'critical', 'breach'

ALTER TABLE public.compliance_metrics
    ADD COLUMN IF NOT EXISTS trend_direction text; -- 'improving', 'stable', 'deteriorating', 'volatile'

ALTER TABLE public.compliance_metrics
    ADD COLUMN IF NOT EXISTS measurement_period text NOT NULL; -- 'daily', 'weekly', 'monthly', 'quarterly', 'annual'

ALTER TABLE public.compliance_metrics
    ADD COLUMN IF NOT EXISTS reporting_frequency text NOT NULL DEFAULT 'daily';

ALTER TABLE public.compliance_metrics
    ADD COLUMN IF NOT EXISTS data_sources jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.compliance_metrics
    ADD COLUMN IF NOT EXISTS calculation_details jsonb DEFAULT '{}';

ALTER TABLE public.compliance_metrics
    ADD COLUMN IF NOT EXISTS business_impact text;

ALTER TABLE public.compliance_metrics
    ADD COLUMN IF NOT EXISTS remediation_actions jsonb DEFAULT '[]';

ALTER TABLE public.compliance_metrics
    ADD COLUMN IF NOT EXISTS stakeholders jsonb DEFAULT '[]';

ALTER TABLE public.compliance_metrics
    ADD COLUMN IF NOT EXISTS last_calculated timestamp with time zone NOT NULL;

ALTER TABLE public.compliance_metrics
    ADD COLUMN IF NOT EXISTS next_calculation timestamp with time zone;

ALTER TABLE public.compliance_metrics
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.compliance_metrics
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create analytics_dashboards table with primary key
CREATE TABLE IF NOT EXISTS public.analytics_dashboards (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to analytics_dashboards
ALTER TABLE public.analytics_dashboards
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.analytics_dashboards
    ADD COLUMN IF NOT EXISTS dashboard_name text NOT NULL;

ALTER TABLE public.analytics_dashboards
    ADD COLUMN IF NOT EXISTS dashboard_type text NOT NULL; -- 'executive', 'operational', 'risk', 'compliance', 'audit', 'custom'

ALTER TABLE public.analytics_dashboards
    ADD COLUMN IF NOT EXISTS description text;

ALTER TABLE public.analytics_dashboards
    ADD COLUMN IF NOT EXISTS layout_config jsonb NOT NULL DEFAULT '{}';

ALTER TABLE public.analytics_dashboards
    ADD COLUMN IF NOT EXISTS widget_definitions jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.analytics_dashboards
    ADD COLUMN IF NOT EXISTS data_sources jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.analytics_dashboards
    ADD COLUMN IF NOT EXISTS refresh_frequency text NOT NULL DEFAULT 'hourly'; -- 'realtime', 'hourly', 'daily', 'weekly'

ALTER TABLE public.analytics_dashboards
    ADD COLUMN IF NOT EXISTS access_permissions jsonb NOT NULL DEFAULT '{}';

ALTER TABLE public.analytics_dashboards
    ADD COLUMN IF NOT EXISTS filters_config jsonb DEFAULT '{}';

ALTER TABLE public.analytics_dashboards
    ADD COLUMN IF NOT EXISTS drill_down_config jsonb DEFAULT '{}';

ALTER TABLE public.analytics_dashboards
    ADD COLUMN IF NOT EXISTS export_settings jsonb DEFAULT '{}';

ALTER TABLE public.analytics_dashboards
    ADD COLUMN IF NOT EXISTS personalization_settings jsonb DEFAULT '{}';

ALTER TABLE public.analytics_dashboards
    ADD COLUMN IF NOT EXISTS is_public boolean DEFAULT false;

ALTER TABLE public.analytics_dashboards
    ADD COLUMN IF NOT EXISTS is_active boolean DEFAULT true;

ALTER TABLE public.analytics_dashboards
    ADD COLUMN IF NOT EXISTS last_accessed timestamp with time zone;

ALTER TABLE public.analytics_dashboards
    ADD COLUMN IF NOT EXISTS access_count integer DEFAULT 0;

ALTER TABLE public.analytics_dashboards
    ADD COLUMN IF NOT EXISTS created_by uuid NOT NULL REFERENCES public.users(id);

ALTER TABLE public.analytics_dashboards
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.analytics_dashboards
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create predictive_models table with primary key
CREATE TABLE IF NOT EXISTS public.predictive_models (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to predictive_models
ALTER TABLE public.predictive_models
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.predictive_models
    ADD COLUMN IF NOT EXISTS model_name text NOT NULL;

ALTER TABLE public.predictive_models
    ADD COLUMN IF NOT EXISTS model_purpose text NOT NULL; -- 'compliance_forecasting', 'risk_prediction', 'regulatory_impact', 'customer_behavior', 'market_analysis'

ALTER TABLE public.predictive_models
    ADD COLUMN IF NOT EXISTS model_type text NOT NULL; -- 'time_series', 'classification', 'regression', 'clustering', 'anomaly_detection'

ALTER TABLE public.predictive_models
    ADD COLUMN IF NOT EXISTS algorithm text NOT NULL;

ALTER TABLE public.predictive_models
    ADD COLUMN IF NOT EXISTS prediction_horizon text NOT NULL; -- '1_day', '1_week', '1_month', '3_months', '6_months', '1_year'

ALTER TABLE public.predictive_models
    ADD COLUMN IF NOT EXISTS input_features jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.predictive_models
    ADD COLUMN IF NOT EXISTS target_variables jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.predictive_models
    ADD COLUMN IF NOT EXISTS training_config jsonb NOT NULL DEFAULT '{}';

ALTER TABLE public.predictive_models
    ADD COLUMN IF NOT EXISTS hyperparameters jsonb DEFAULT '{}';

ALTER TABLE public.predictive_models
    ADD COLUMN IF NOT EXISTS performance_metrics jsonb DEFAULT '{}';

ALTER TABLE public.predictive_models
    ADD COLUMN IF NOT EXISTS backtesting_results jsonb DEFAULT '{}';

ALTER TABLE public.predictive_models
    ADD COLUMN IF NOT EXISTS feature_importance jsonb DEFAULT '{}';

ALTER TABLE public.predictive_models
    ADD COLUMN IF NOT EXISTS model_explainability jsonb DEFAULT '{}';

ALTER TABLE public.predictive_models
    ADD COLUMN IF NOT EXISTS training_data_period text;

ALTER TABLE public.predictive_models
    ADD COLUMN IF NOT EXISTS model_status text NOT NULL DEFAULT 'development'; -- 'development', 'testing', 'production', 'retired', 'failed'

ALTER TABLE public.predictive_models
    ADD COLUMN IF NOT EXISTS accuracy_metrics jsonb DEFAULT '{}';

ALTER TABLE public.predictive_models
    ADD COLUMN IF NOT EXISTS deployment_date timestamp with time zone;

ALTER TABLE public.predictive_models
    ADD COLUMN IF NOT EXISTS last_training_date timestamp with time zone;

ALTER TABLE public.predictive_models
    ADD COLUMN IF NOT EXISTS next_retrain_date timestamp with time zone;

ALTER TABLE public.predictive_models
    ADD COLUMN IF NOT EXISTS model_version text NOT NULL DEFAULT '1.0';

ALTER TABLE public.predictive_models
    ADD COLUMN IF NOT EXISTS created_by uuid NOT NULL REFERENCES public.users(id);

ALTER TABLE public.predictive_models
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.predictive_models
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create model_predictions table with primary key
CREATE TABLE IF NOT EXISTS public.model_predictions (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to model_predictions
ALTER TABLE public.model_predictions
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.model_predictions
    ADD COLUMN IF NOT EXISTS model_id uuid NOT NULL REFERENCES public.predictive_models(id);

ALTER TABLE public.model_predictions
    ADD COLUMN IF NOT EXISTS prediction_type text NOT NULL;

ALTER TABLE public.model_predictions
    ADD COLUMN IF NOT EXISTS input_data jsonb NOT NULL;

ALTER TABLE public.model_predictions
    ADD COLUMN IF NOT EXISTS predicted_values jsonb NOT NULL;

ALTER TABLE public.model_predictions
    ADD COLUMN IF NOT EXISTS confidence_scores jsonb DEFAULT '{}';

ALTER TABLE public.model_predictions
    ADD COLUMN IF NOT EXISTS prediction_intervals jsonb DEFAULT '{}';

ALTER TABLE public.model_predictions
    ADD COLUMN IF NOT EXISTS feature_contributions jsonb DEFAULT '{}';

ALTER TABLE public.model_predictions
    ADD COLUMN IF NOT EXISTS prediction_explanation text;

ALTER TABLE public.model_predictions
    ADD COLUMN IF NOT EXISTS actual_values jsonb;

ALTER TABLE public.model_predictions
    ADD COLUMN IF NOT EXISTS prediction_error numeric(10,4);

ALTER TABLE public.model_predictions
    ADD COLUMN IF NOT EXISTS prediction_date timestamp with time zone NOT NULL;

ALTER TABLE public.model_predictions
    ADD COLUMN IF NOT EXISTS target_date timestamp with time zone NOT NULL;

ALTER TABLE public.model_predictions
    ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'pending'; -- 'pending', 'confirmed', 'rejected', 'outdated'

ALTER TABLE public.model_predictions
    ADD COLUMN IF NOT EXISTS business_impact text;

ALTER TABLE public.model_predictions
    ADD COLUMN IF NOT EXISTS recommended_actions jsonb DEFAULT '[]';

ALTER TABLE public.model_predictions
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create regulatory_intelligence table with primary key
CREATE TABLE IF NOT EXISTS public.regulatory_intelligence (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to regulatory_intelligence
ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS intelligence_type text NOT NULL; -- 'trend_analysis', 'impact_forecast', 'regulatory_radar', 'compliance_gap', 'peer_benchmarking'

ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS title text NOT NULL;

ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS summary text NOT NULL;

ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS detailed_analysis text;

ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS data_sources jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS analysis_methodology text;

ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS key_findings jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS insights jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS recommendations jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS risk_implications jsonb DEFAULT '[]';

ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS business_implications jsonb DEFAULT '[]';

ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS confidence_level numeric(3,2) NOT NULL DEFAULT 0.70;

ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS accuracy_score numeric(3,2);

ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS validation_status text DEFAULT 'pending'; -- 'pending', 'validated', 'rejected', 'under_review'

ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS regulatory_domains jsonb DEFAULT '[]';

ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS geographic_scope jsonb DEFAULT '[]';

ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS timeframe text; -- 'immediate', '1_month', '3_months', '6_months', '1_year', 'long_term'

ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS priority_level text NOT NULL DEFAULT 'medium'; -- 'critical', 'high', 'medium', 'low'

ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS tags jsonb DEFAULT '[]';

ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS related_documents jsonb DEFAULT '[]';

ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS generated_by text NOT NULL; -- 'ai_analysis', 'human_expert', 'hybrid'

ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS reviewed_by uuid REFERENCES public.users(id);

ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS published_at timestamp with time zone;

ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS expires_at timestamp with time zone;

ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.regulatory_intelligence
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create performance_benchmarks table with primary key
CREATE TABLE IF NOT EXISTS public.performance_benchmarks (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to performance_benchmarks
ALTER TABLE public.performance_benchmarks
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.performance_benchmarks
    ADD COLUMN IF NOT EXISTS benchmark_name text NOT NULL;

ALTER TABLE public.performance_benchmarks
    ADD COLUMN IF NOT EXISTS benchmark_category text NOT NULL; -- 'compliance_efficiency', 'risk_management', 'operational_performance', 'regulatory_readiness'

ALTER TABLE public.performance_benchmarks
    ADD COLUMN IF NOT EXISTS industry_sector text NOT NULL;

ALTER TABLE public.performance_benchmarks
    ADD COLUMN IF NOT EXISTS institution_size text NOT NULL; -- 'small', 'medium', 'large', 'enterprise'

ALTER TABLE public.performance_benchmarks
    ADD COLUMN IF NOT EXISTS metric_definition text NOT NULL;

ALTER TABLE public.performance_benchmarks
    ADD COLUMN IF NOT EXISTS calculation_methodology text NOT NULL;

ALTER TABLE public.performance_benchmarks
    ADD COLUMN IF NOT EXISTS industry_average numeric(15,4);

ALTER TABLE public.performance_benchmarks
    ADD COLUMN IF NOT EXISTS industry_median numeric(15,4);

ALTER TABLE public.performance_benchmarks
    ADD COLUMN IF NOT EXISTS top_quartile numeric(15,4);

ALTER TABLE public.performance_benchmarks
    ADD COLUMN IF NOT EXISTS bottom_quartile numeric(15,4);

ALTER TABLE public.performance_benchmarks
    ADD COLUMN IF NOT EXISTS best_in_class numeric(15,4);

ALTER TABLE public.performance_benchmarks
    ADD COLUMN IF NOT EXISTS organization_value numeric(15,4);

ALTER TABLE public.performance_benchmarks
    ADD COLUMN IF NOT EXISTS percentile_rank numeric(5,2);

ALTER TABLE public.performance_benchmarks
    ADD COLUMN IF NOT EXISTS performance_grade text; -- 'A+', 'A', 'B+', 'B', 'C+', 'C', 'D', 'F'

ALTER TABLE public.performance_benchmarks
    ADD COLUMN IF NOT EXISTS gap_analysis jsonb DEFAULT '{}';

ALTER TABLE public.performance_benchmarks
    ADD COLUMN IF NOT EXISTS improvement_opportunities jsonb DEFAULT '[]';

ALTER TABLE public.performance_benchmarks
    ADD COLUMN IF NOT EXISTS trend_analysis jsonb DEFAULT '{}';

ALTER TABLE public.performance_benchmarks
    ADD COLUMN IF NOT EXISTS data_source text NOT NULL;

ALTER TABLE public.performance_benchmarks
    ADD COLUMN IF NOT EXISTS sample_size integer;

ALTER TABLE public.performance_benchmarks
    ADD COLUMN IF NOT EXISTS confidence_interval numeric(5,4);

ALTER TABLE public.performance_benchmarks
    ADD COLUMN IF NOT EXISTS benchmark_date date NOT NULL;

ALTER TABLE public.performance_benchmarks
    ADD COLUMN IF NOT EXISTS next_update_date date;

ALTER TABLE public.performance_benchmarks
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.performance_benchmarks
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Add indexes for Phase 4 analytics performance
CREATE INDEX IF NOT EXISTS idx_risk_scoring_models_tenant ON public.risk_scoring_models(tenant_id);
CREATE INDEX IF NOT EXISTS idx_risk_scoring_models_type ON public.risk_scoring_models(model_type);
CREATE INDEX IF NOT EXISTS idx_risk_scoring_models_status ON public.risk_scoring_models(model_status);

CREATE INDEX IF NOT EXISTS idx_customer_risk_scores_tenant ON public.customer_risk_scores(tenant_id);
CREATE INDEX IF NOT EXISTS idx_customer_risk_scores_customer ON public.customer_risk_scores(customer_id);
CREATE INDEX IF NOT EXISTS idx_customer_risk_scores_grade ON public.customer_risk_scores(risk_grade);
CREATE INDEX IF NOT EXISTS idx_customer_risk_scores_category ON public.customer_risk_scores(risk_category);
CREATE INDEX IF NOT EXISTS idx_customer_risk_scores_date ON public.customer_risk_scores(score_date);

CREATE INDEX IF NOT EXISTS idx_transaction_risk_scores_tenant ON public.transaction_risk_scores(tenant_id);
CREATE INDEX IF NOT EXISTS idx_transaction_risk_scores_transaction ON public.transaction_risk_scores(transaction_id);
CREATE INDEX IF NOT EXISTS idx_transaction_risk_scores_level ON public.transaction_risk_scores(risk_level);
CREATE INDEX IF NOT EXISTS idx_transaction_risk_scores_overall ON public.transaction_risk_scores(overall_risk_score);

CREATE INDEX IF NOT EXISTS idx_compliance_metrics_tenant ON public.compliance_metrics(tenant_id);
CREATE INDEX IF NOT EXISTS idx_compliance_metrics_category ON public.compliance_metrics(metric_category);
CREATE INDEX IF NOT EXISTS idx_compliance_metrics_status ON public.compliance_metrics(status);
CREATE INDEX IF NOT EXISTS idx_compliance_metrics_calculated ON public.compliance_metrics(last_calculated);

CREATE INDEX IF NOT EXISTS idx_analytics_dashboards_tenant ON public.analytics_dashboards(tenant_id);
CREATE INDEX IF NOT EXISTS idx_analytics_dashboards_type ON public.analytics_dashboards(dashboard_type);
CREATE INDEX IF NOT EXISTS idx_analytics_dashboards_active ON public.analytics_dashboards(is_active);

CREATE INDEX IF NOT EXISTS idx_predictive_models_tenant ON public.predictive_models(tenant_id);
CREATE INDEX IF NOT EXISTS idx_predictive_models_purpose ON public.predictive_models(model_purpose);
CREATE INDEX IF NOT EXISTS idx_predictive_models_status ON public.predictive_models(model_status);

CREATE INDEX IF NOT EXISTS idx_model_predictions_tenant ON public.model_predictions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_model_predictions_model ON public.model_predictions(model_id);
CREATE INDEX IF NOT EXISTS idx_model_predictions_date ON public.model_predictions(prediction_date);
CREATE INDEX IF NOT EXISTS idx_model_predictions_target ON public.model_predictions(target_date);

CREATE INDEX IF NOT EXISTS idx_regulatory_intelligence_tenant ON public.regulatory_intelligence(tenant_id);
CREATE INDEX IF NOT EXISTS idx_regulatory_intelligence_type ON public.regulatory_intelligence(intelligence_type);
CREATE INDEX IF NOT EXISTS idx_regulatory_intelligence_priority ON public.regulatory_intelligence(priority_level);
CREATE INDEX IF NOT EXISTS idx_regulatory_intelligence_status ON public.regulatory_intelligence(validation_status);

CREATE INDEX IF NOT EXISTS idx_performance_benchmarks_tenant ON public.performance_benchmarks(tenant_id);
CREATE INDEX IF NOT EXISTS idx_performance_benchmarks_category ON public.performance_benchmarks(benchmark_category);
CREATE INDEX IF NOT EXISTS idx_performance_benchmarks_sector ON public.performance_benchmarks(industry_sector);
CREATE INDEX IF NOT EXISTS idx_performance_benchmarks_date ON public.performance_benchmarks(benchmark_date);

-- Foreign key constraints for Phase 4
ALTER TABLE public.customer_risk_scores 
    ADD CONSTRAINT fk_customer_risk_scores_model 
    FOREIGN KEY (model_id) REFERENCES public.risk_scoring_models(id) ON DELETE RESTRICT;

ALTER TABLE public.transaction_risk_scores 
    ADD CONSTRAINT fk_transaction_risk_scores_model 
    FOREIGN KEY (model_id) REFERENCES public.risk_scoring_models(id) ON DELETE RESTRICT;

ALTER TABLE public.model_predictions 
    ADD CONSTRAINT fk_model_predictions_model 
    FOREIGN KEY (model_id) REFERENCES public.predictive_models(id) ON DELETE CASCADE;

-- Add check constraints for Phase 4
ALTER TABLE public.risk_scoring_models ADD CONSTRAINT chk_risk_model_type 
    CHECK (model_type IN ('credit_risk', 'operational_risk', 'market_risk', 'compliance_risk', 'fraud_risk', 'liquidity_risk'));

ALTER TABLE public.risk_scoring_models ADD CONSTRAINT chk_risk_model_status 
    CHECK (model_status IN ('training', 'testing', 'production', 'deprecated', 'failed'));

ALTER TABLE public.customer_risk_scores ADD CONSTRAINT chk_customer_risk_grade 
    CHECK (risk_grade IN ('AAA', 'AA+', 'AA', 'AA-', 'A+', 'A', 'A-', 'BBB+', 'BBB', 'BBB-', 'BB+', 'BB', 'BB-', 'B+', 'B', 'B-', 'CCC+', 'CCC', 'CCC-', 'CC', 'C', 'D'));

ALTER TABLE public.customer_risk_scores ADD CONSTRAINT chk_customer_risk_category 
    CHECK (risk_category IN ('low', 'medium', 'high', 'critical'));

ALTER TABLE public.transaction_risk_scores ADD CONSTRAINT chk_transaction_risk_level 
    CHECK (risk_level IN ('low', 'medium', 'high', 'critical'));

ALTER TABLE public.transaction_risk_scores ADD CONSTRAINT chk_auto_decision 
    CHECK (auto_decision IN ('approve', 'decline', 'review', 'escalate', 'manual'));

ALTER TABLE public.compliance_metrics ADD CONSTRAINT chk_metric_category 
    CHECK (metric_category IN ('aml', 'kyc', 'fraud', 'operational', 'regulatory', 'audit', 'credit', 'market', 'liquidity'));

ALTER TABLE public.compliance_metrics ADD CONSTRAINT chk_metric_status 
    CHECK (status IN ('normal', 'warning', 'critical', 'breach', 'unknown'));

ALTER TABLE public.analytics_dashboards ADD CONSTRAINT chk_dashboard_type 
    CHECK (dashboard_type IN ('executive', 'operational', 'risk', 'compliance', 'audit', 'custom', 'regulatory'));

ALTER TABLE public.predictive_models ADD CONSTRAINT chk_predictive_model_purpose 
    CHECK (model_purpose IN ('compliance_forecasting', 'risk_prediction', 'regulatory_impact', 'customer_behavior', 'market_analysis', 'fraud_detection'));

ALTER TABLE public.predictive_models ADD CONSTRAINT chk_predictive_model_status 
    CHECK (model_status IN ('development', 'testing', 'production', 'retired', 'failed'));

ALTER TABLE public.model_predictions ADD CONSTRAINT chk_prediction_status 
    CHECK (status IN ('pending', 'confirmed', 'rejected', 'outdated', 'under_review'));

ALTER TABLE public.regulatory_intelligence ADD CONSTRAINT chk_intelligence_type 
    CHECK (intelligence_type IN ('trend_analysis', 'impact_forecast', 'regulatory_radar', 'compliance_gap', 'peer_benchmarking', 'regulatory_calendar'));

ALTER TABLE public.regulatory_intelligence ADD CONSTRAINT chk_intelligence_priority 
    CHECK (priority_level IN ('critical', 'high', 'medium', 'low'));

ALTER TABLE public.regulatory_intelligence ADD CONSTRAINT chk_validation_status 
    CHECK (validation_status IN ('pending', 'validated', 'rejected', 'under_review'));

ALTER TABLE public.performance_benchmarks ADD CONSTRAINT chk_benchmark_category 
    CHECK (benchmark_category IN ('compliance_efficiency', 'risk_management', 'operational_performance', 'regulatory_readiness', 'financial_performance'));

ALTER TABLE public.performance_benchmarks ADD CONSTRAINT chk_institution_size 
    CHECK (institution_size IN ('small', 'medium', 'large', 'enterprise', 'multinational'));

-- Comments for Phase 4 tables
COMMENT ON TABLE public.risk_scoring_models IS 'ML models for comprehensive risk assessment across multiple risk types';
COMMENT ON TABLE public.customer_risk_scores IS 'Customer risk scores with detailed breakdown and explanations';
COMMENT ON TABLE public.transaction_risk_scores IS 'Real-time transaction risk scoring for fraud and AML detection';
COMMENT ON TABLE public.compliance_metrics IS 'Key performance indicators and metrics for compliance monitoring';
COMMENT ON TABLE public.analytics_dashboards IS 'Configurable dashboards for business intelligence and reporting';
COMMENT ON TABLE public.predictive_models IS 'Predictive analytics models for forecasting and trend analysis';
COMMENT ON TABLE public.model_predictions IS 'Predictions generated by ML models with confidence intervals';
COMMENT ON TABLE public.regulatory_intelligence IS 'AI-generated regulatory insights and intelligence reports';
COMMENT ON TABLE public.performance_benchmarks IS 'Industry benchmarking data for performance comparison';

-- ============================================================================
-- PHASE 5: ENTERPRISE INTEGRATIONS TABLES
-- ============================================================================

-- Step 1: Create integration_systems table with primary key
CREATE TABLE IF NOT EXISTS public.integration_systems (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to integration_systems
ALTER TABLE public.integration_systems
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.integration_systems
    ADD COLUMN IF NOT EXISTS system_name text NOT NULL;

ALTER TABLE public.integration_systems
    ADD COLUMN IF NOT EXISTS system_type text NOT NULL; -- 'grc', 'core_banking', 'external_data', 'document_management', 'risk_system'

ALTER TABLE public.integration_systems
    ADD COLUMN IF NOT EXISTS vendor text NOT NULL; -- 'archer', 'metricstream', 'servicenow', 'temenos', 'finacle', 'sharepoint', 'box', 'ofac'

ALTER TABLE public.integration_systems
    ADD COLUMN IF NOT EXISTS version text;

ALTER TABLE public.integration_systems
    ADD COLUMN IF NOT EXISTS base_url text NOT NULL;

ALTER TABLE public.integration_systems
    ADD COLUMN IF NOT EXISTS authentication_type text NOT NULL; -- 'oauth2', 'api_key', 'basic_auth', 'certificate', 'saml'

ALTER TABLE public.integration_systems
    ADD COLUMN IF NOT EXISTS authentication_config jsonb NOT NULL DEFAULT '{}';

ALTER TABLE public.integration_systems
    ADD COLUMN IF NOT EXISTS api_endpoints jsonb NOT NULL DEFAULT '{}';

ALTER TABLE public.integration_systems
    ADD COLUMN IF NOT EXISTS rate_limits jsonb DEFAULT '{}';

ALTER TABLE public.integration_systems
    ADD COLUMN IF NOT EXISTS timeout_seconds integer DEFAULT 30;

ALTER TABLE public.integration_systems
    ADD COLUMN IF NOT EXISTS retry_policy jsonb DEFAULT '{"max_retries": 3, "backoff_factor": 2}';

ALTER TABLE public.integration_systems
    ADD COLUMN IF NOT EXISTS data_mapping_config jsonb DEFAULT '{}';

ALTER TABLE public.integration_systems
    ADD COLUMN IF NOT EXISTS sync_frequency text DEFAULT 'hourly'; -- 'realtime', 'hourly', 'daily', 'weekly', 'manual'

ALTER TABLE public.integration_systems
    ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'active'; -- 'active', 'inactive', 'error', 'maintenance'

ALTER TABLE public.integration_systems
    ADD COLUMN IF NOT EXISTS last_sync_at timestamp with time zone;

ALTER TABLE public.integration_systems
    ADD COLUMN IF NOT EXISTS next_sync_at timestamp with time zone;

ALTER TABLE public.integration_systems
    ADD COLUMN IF NOT EXISTS error_count integer DEFAULT 0;

ALTER TABLE public.integration_systems
    ADD COLUMN IF NOT EXISTS last_error text;

ALTER TABLE public.integration_systems
    ADD COLUMN IF NOT EXISTS health_check_url text;

ALTER TABLE public.integration_systems
    ADD COLUMN IF NOT EXISTS monitoring_enabled boolean DEFAULT true;

ALTER TABLE public.integration_systems
    ADD COLUMN IF NOT EXISTS created_by uuid NOT NULL REFERENCES public.users(id);

ALTER TABLE public.integration_systems
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.integration_systems
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create integration_logs table with primary key
CREATE TABLE IF NOT EXISTS public.integration_logs (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to integration_logs
ALTER TABLE public.integration_logs
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.integration_logs
    ADD COLUMN IF NOT EXISTS integration_system_id uuid NOT NULL REFERENCES public.integration_systems(id);

ALTER TABLE public.integration_logs
    ADD COLUMN IF NOT EXISTS operation_type text NOT NULL; -- 'sync', 'push', 'pull', 'health_check', 'authentication'

ALTER TABLE public.integration_logs
    ADD COLUMN IF NOT EXISTS operation_name text NOT NULL;

ALTER TABLE public.integration_logs
    ADD COLUMN IF NOT EXISTS status text NOT NULL; -- 'success', 'error', 'warning', 'timeout', 'cancelled'

ALTER TABLE public.integration_logs
    ADD COLUMN IF NOT EXISTS request_id text;

ALTER TABLE public.integration_logs
    ADD COLUMN IF NOT EXISTS http_method text;

ALTER TABLE public.integration_logs
    ADD COLUMN IF NOT EXISTS endpoint_url text;

ALTER TABLE public.integration_logs
    ADD COLUMN IF NOT EXISTS request_headers jsonb DEFAULT '{}';

ALTER TABLE public.integration_logs
    ADD COLUMN IF NOT EXISTS request_body jsonb;

ALTER TABLE public.integration_logs
    ADD COLUMN IF NOT EXISTS response_status_code integer;

ALTER TABLE public.integration_logs
    ADD COLUMN IF NOT EXISTS response_headers jsonb DEFAULT '{}';

ALTER TABLE public.integration_logs
    ADD COLUMN IF NOT EXISTS response_body jsonb;

ALTER TABLE public.integration_logs
    ADD COLUMN IF NOT EXISTS response_time_ms integer;

ALTER TABLE public.integration_logs
    ADD COLUMN IF NOT EXISTS error_message text;

ALTER TABLE public.integration_logs
    ADD COLUMN IF NOT EXISTS error_code text;

ALTER TABLE public.integration_logs
    ADD COLUMN IF NOT EXISTS records_processed integer DEFAULT 0;

ALTER TABLE public.integration_logs
    ADD COLUMN IF NOT EXISTS records_successful integer DEFAULT 0;

ALTER TABLE public.integration_logs
    ADD COLUMN IF NOT EXISTS records_failed integer DEFAULT 0;

ALTER TABLE public.integration_logs
    ADD COLUMN IF NOT EXISTS data_volume_bytes bigint DEFAULT 0;

ALTER TABLE public.integration_logs
    ADD COLUMN IF NOT EXISTS business_context jsonb DEFAULT '{}';

ALTER TABLE public.integration_logs
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create grc_risk_registers table with primary key
CREATE TABLE IF NOT EXISTS public.grc_risk_registers (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to grc_risk_registers
ALTER TABLE public.grc_risk_registers
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.grc_risk_registers
    ADD COLUMN IF NOT EXISTS integration_system_id uuid NOT NULL REFERENCES public.integration_systems(id);

ALTER TABLE public.grc_risk_registers
    ADD COLUMN IF NOT EXISTS external_risk_id text NOT NULL;

ALTER TABLE public.grc_risk_registers
    ADD COLUMN IF NOT EXISTS risk_title text NOT NULL;

ALTER TABLE public.grc_risk_registers
    ADD COLUMN IF NOT EXISTS risk_description text;

ALTER TABLE public.grc_risk_registers
    ADD COLUMN IF NOT EXISTS risk_category text NOT NULL; -- 'operational', 'credit', 'market', 'liquidity', 'compliance', 'strategic'

ALTER TABLE public.grc_risk_registers
    ADD COLUMN IF NOT EXISTS risk_subcategory text;

ALTER TABLE public.grc_risk_registers
    ADD COLUMN IF NOT EXISTS inherent_risk_rating text; -- 'critical', 'high', 'medium', 'low'

ALTER TABLE public.grc_risk_registers
    ADD COLUMN IF NOT EXISTS residual_risk_rating text;

ALTER TABLE public.grc_risk_registers
    ADD COLUMN IF NOT EXISTS risk_appetite text; -- 'high', 'medium', 'low', 'zero'

ALTER TABLE public.grc_risk_registers
    ADD COLUMN IF NOT EXISTS risk_tolerance numeric(5,2);

ALTER TABLE public.grc_risk_registers
    ADD COLUMN IF NOT EXISTS business_unit text;

ALTER TABLE public.grc_risk_registers
    ADD COLUMN IF NOT EXISTS risk_owner text;

ALTER TABLE public.grc_risk_registers
    ADD COLUMN IF NOT EXISTS control_effectiveness text; -- 'effective', 'partially_effective', 'ineffective', 'not_assessed'

ALTER TABLE public.grc_risk_registers
    ADD COLUMN IF NOT EXISTS mitigation_strategies jsonb DEFAULT '[]';

ALTER TABLE public.grc_risk_registers
    ADD COLUMN IF NOT EXISTS key_controls jsonb DEFAULT '[]';

ALTER TABLE public.grc_risk_registers
    ADD COLUMN IF NOT EXISTS risk_indicators jsonb DEFAULT '[]';

ALTER TABLE public.grc_risk_registers
    ADD COLUMN IF NOT EXISTS regulatory_references jsonb DEFAULT '[]';

ALTER TABLE public.grc_risk_registers
    ADD COLUMN IF NOT EXISTS last_assessment_date timestamp with time zone;

ALTER TABLE public.grc_risk_registers
    ADD COLUMN IF NOT EXISTS next_review_date timestamp with time zone;

ALTER TABLE public.grc_risk_registers
    ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'active'; -- 'active', 'closed', 'transferred', 'accepted'

ALTER TABLE public.grc_risk_registers
    ADD COLUMN IF NOT EXISTS external_data jsonb DEFAULT '{}';

ALTER TABLE public.grc_risk_registers
    ADD COLUMN IF NOT EXISTS sync_status text DEFAULT 'synced'; -- 'synced', 'pending', 'conflict', 'error'

ALTER TABLE public.grc_risk_registers
    ADD COLUMN IF NOT EXISTS last_synced_at timestamp with time zone;

ALTER TABLE public.grc_risk_registers
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.grc_risk_registers
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create external_data_sources table with primary key
CREATE TABLE IF NOT EXISTS public.external_data_sources (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to external_data_sources
ALTER TABLE public.external_data_sources
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.external_data_sources
    ADD COLUMN IF NOT EXISTS source_name text NOT NULL;

ALTER TABLE public.external_data_sources
    ADD COLUMN IF NOT EXISTS source_type text NOT NULL; -- 'sanctions', 'pep', 'credit_bureau', 'market_data', 'regulatory_database'

ALTER TABLE public.external_data_sources
    ADD COLUMN IF NOT EXISTS provider text NOT NULL; -- 'ofac', 'eu_sanctions', 'world_bank', 'refinitiv', 'dowjones', 'experian'

ALTER TABLE public.external_data_sources
    ADD COLUMN IF NOT EXISTS data_format text NOT NULL; -- 'xml', 'json', 'csv', 'pdf', 'api'

ALTER TABLE public.external_data_sources
    ADD COLUMN IF NOT EXISTS access_method text NOT NULL; -- 'ftp', 'sftp', 'api', 'webhook', 'email', 'download'

ALTER TABLE public.external_data_sources
    ADD COLUMN IF NOT EXISTS endpoint_url text;

ALTER TABLE public.external_data_sources
    ADD COLUMN IF NOT EXISTS authentication_method text; -- 'api_key', 'oauth2', 'basic_auth', 'certificate'

ALTER TABLE public.external_data_sources
    ADD COLUMN IF NOT EXISTS authentication_config jsonb DEFAULT '{}';

ALTER TABLE public.external_data_sources
    ADD COLUMN IF NOT EXISTS update_frequency text NOT NULL; -- 'realtime', 'hourly', 'daily', 'weekly', 'monthly'

ALTER TABLE public.external_data_sources
    ADD COLUMN IF NOT EXISTS data_retention_days integer DEFAULT 365;

ALTER TABLE public.external_data_sources
    ADD COLUMN IF NOT EXISTS processing_rules jsonb DEFAULT '{}';

ALTER TABLE public.external_data_sources
    ADD COLUMN IF NOT EXISTS quality_checks jsonb DEFAULT '[]';

ALTER TABLE public.external_data_sources
    ADD COLUMN IF NOT EXISTS cost_per_query numeric(10,4);

ALTER TABLE public.external_data_sources
    ADD COLUMN IF NOT EXISTS monthly_query_limit integer;

ALTER TABLE public.external_data_sources
    ADD COLUMN IF NOT EXISTS current_month_queries integer DEFAULT 0;

ALTER TABLE public.external_data_sources
    ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'active'; -- 'active', 'inactive', 'suspended', 'error'

ALTER TABLE public.external_data_sources
    ADD COLUMN IF NOT EXISTS last_update_check timestamp with time zone;

ALTER TABLE public.external_data_sources
    ADD COLUMN IF NOT EXISTS next_update_check timestamp with time zone;

ALTER TABLE public.external_data_sources
    ADD COLUMN IF NOT EXISTS data_version text;

ALTER TABLE public.external_data_sources
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.external_data_sources
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create sanctions_screening_results table with primary key
CREATE TABLE IF NOT EXISTS public.sanctions_screening_results (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to sanctions_screening_results
ALTER TABLE public.sanctions_screening_results
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.sanctions_screening_results
    ADD COLUMN IF NOT EXISTS data_source_id uuid NOT NULL REFERENCES public.external_data_sources(id);

ALTER TABLE public.sanctions_screening_results
    ADD COLUMN IF NOT EXISTS customer_id uuid REFERENCES public.customers(id);

ALTER TABLE public.sanctions_screening_results
    ADD COLUMN IF NOT EXISTS transaction_id uuid REFERENCES public.transactions(id);

ALTER TABLE public.sanctions_screening_results
    ADD COLUMN IF NOT EXISTS screening_type text NOT NULL; -- 'customer_onboarding', 'ongoing_monitoring', 'transaction_screening', 'batch_screening'

ALTER TABLE public.sanctions_screening_results
    ADD COLUMN IF NOT EXISTS search_criteria jsonb NOT NULL;

ALTER TABLE public.sanctions_screening_results
    ADD COLUMN IF NOT EXISTS match_status text NOT NULL; -- 'no_match', 'possible_match', 'confirmed_match', 'false_positive'

ALTER TABLE public.sanctions_screening_results
    ADD COLUMN IF NOT EXISTS match_score numeric(5,4);

ALTER TABLE public.sanctions_screening_results
    ADD COLUMN IF NOT EXISTS matches_found jsonb DEFAULT '[]';

ALTER TABLE public.sanctions_screening_results
    ADD COLUMN IF NOT EXISTS sanctions_lists jsonb DEFAULT '[]'; -- OFAC, EU, UN, etc.

ALTER TABLE public.sanctions_screening_results
    ADD COLUMN IF NOT EXISTS screening_date timestamp with time zone NOT NULL;

ALTER TABLE public.sanctions_screening_results
    ADD COLUMN IF NOT EXISTS review_status text DEFAULT 'pending'; -- 'pending', 'reviewed', 'cleared', 'escalated'

ALTER TABLE public.sanctions_screening_results
    ADD COLUMN IF NOT EXISTS reviewed_by uuid REFERENCES public.users(id);

ALTER TABLE public.sanctions_screening_results
    ADD COLUMN IF NOT EXISTS review_date timestamp with time zone;

ALTER TABLE public.sanctions_screening_results
    ADD COLUMN IF NOT EXISTS review_notes text;

ALTER TABLE public.sanctions_screening_results
    ADD COLUMN IF NOT EXISTS auto_cleared boolean DEFAULT false;

ALTER TABLE public.sanctions_screening_results
    ADD COLUMN IF NOT EXISTS alert_generated boolean DEFAULT false;

ALTER TABLE public.sanctions_screening_results
    ADD COLUMN IF NOT EXISTS response_time_ms integer;

ALTER TABLE public.sanctions_screening_results
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create document_repositories table with primary key
CREATE TABLE IF NOT EXISTS public.document_repositories (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to document_repositories
ALTER TABLE public.document_repositories
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.document_repositories
    ADD COLUMN IF NOT EXISTS repository_name text NOT NULL;

ALTER TABLE public.document_repositories
    ADD COLUMN IF NOT EXISTS repository_type text NOT NULL; -- 'sharepoint', 'box', 'google_drive', 'dropbox', 'aws_s3', 'azure_blob'

ALTER TABLE public.document_repositories
    ADD COLUMN IF NOT EXISTS base_url text NOT NULL;

ALTER TABLE public.document_repositories
    ADD COLUMN IF NOT EXISTS authentication_config jsonb NOT NULL;

ALTER TABLE public.document_repositories
    ADD COLUMN IF NOT EXISTS sync_enabled boolean DEFAULT true;

ALTER TABLE public.document_repositories
    ADD COLUMN IF NOT EXISTS sync_frequency text DEFAULT 'hourly'; -- 'realtime', 'hourly', 'daily', 'weekly'

ALTER TABLE public.document_repositories
    ADD COLUMN IF NOT EXISTS folder_structure jsonb DEFAULT '{}';

ALTER TABLE public.document_repositories
    ADD COLUMN IF NOT EXISTS access_permissions jsonb DEFAULT '{}';

ALTER TABLE public.document_repositories
    ADD COLUMN IF NOT EXISTS file_type_filters jsonb DEFAULT '[]';

ALTER TABLE public.document_repositories
    ADD COLUMN IF NOT EXISTS max_file_size_mb integer DEFAULT 100;

ALTER TABLE public.document_repositories
    ADD COLUMN IF NOT EXISTS retention_policy jsonb DEFAULT '{}';

ALTER TABLE public.document_repositories
    ADD COLUMN IF NOT EXISTS versioning_enabled boolean DEFAULT true;

ALTER TABLE public.document_repositories
    ADD COLUMN IF NOT EXISTS metadata_extraction_enabled boolean DEFAULT true;

ALTER TABLE public.document_repositories
    ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'active'; -- 'active', 'inactive', 'error', 'syncing'

ALTER TABLE public.document_repositories
    ADD COLUMN IF NOT EXISTS last_sync_at timestamp with time zone;

ALTER TABLE public.document_repositories
    ADD COLUMN IF NOT EXISTS next_sync_at timestamp with time zone;

ALTER TABLE public.document_repositories
    ADD COLUMN IF NOT EXISTS total_documents integer DEFAULT 0;

ALTER TABLE public.document_repositories
    ADD COLUMN IF NOT EXISTS storage_used_gb numeric(10,2) DEFAULT 0.0;

ALTER TABLE public.document_repositories
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.document_repositories
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create document_lifecycle table with primary key
CREATE TABLE IF NOT EXISTS public.document_lifecycle (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to document_lifecycle
ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS repository_id uuid NOT NULL REFERENCES public.document_repositories(id);

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS external_document_id text NOT NULL;

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS document_name text NOT NULL;

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS document_path text NOT NULL;

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS document_type text; -- 'policy', 'procedure', 'contract', 'report', 'regulation', 'evidence'

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS document_category text; -- 'compliance', 'risk', 'audit', 'legal', 'operational'

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS file_extension text;

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS file_size_bytes bigint;

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS mime_type text;

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS version text DEFAULT '1.0';

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'active'; -- 'draft', 'active', 'archived', 'deleted', 'under_review'

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS lifecycle_stage text NOT NULL; -- 'creation', 'review', 'approval', 'publication', 'maintenance', 'retirement'

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS owner_user_id uuid REFERENCES public.users(id);

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS author_name text;

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS reviewer_user_id uuid REFERENCES public.users(id);

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS approver_user_id uuid REFERENCES public.users(id);

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS approval_status text DEFAULT 'pending'; -- 'pending', 'approved', 'rejected', 'requires_revision'

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS review_due_date timestamp with time zone;

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS retention_period_years integer;

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS deletion_date timestamp with time zone;

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS compliance_tags jsonb DEFAULT '[]';

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS metadata_extracted jsonb DEFAULT '{}';

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS content_hash text;

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS download_url text;

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS external_created_at timestamp with time zone;

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS external_modified_at timestamp with time zone;

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS last_accessed_at timestamp with time zone;

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS sync_status text DEFAULT 'synced'; -- 'synced', 'pending', 'conflict', 'error'

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.document_lifecycle
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create core_banking_transactions table with primary key
CREATE TABLE IF NOT EXISTS public.core_banking_transactions (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to core_banking_transactions
ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS integration_system_id uuid NOT NULL REFERENCES public.integration_systems(id);

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS external_transaction_id text NOT NULL;

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS internal_transaction_id uuid REFERENCES public.transactions(id);

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS account_number text NOT NULL;

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS customer_cif text;

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS transaction_type text NOT NULL;

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS transaction_subtype text;

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS amount numeric(15,2) NOT NULL;

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS currency text NOT NULL;

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS exchange_rate numeric(10,6);

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS base_amount numeric(15,2);

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS transaction_date timestamp with time zone NOT NULL;

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS value_date timestamp with time zone;

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS processing_date timestamp with time zone;

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS branch_code text;

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS channel text; -- 'atm', 'online', 'mobile', 'branch', 'wire', 'ach'

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS counterparty_account text;

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS counterparty_bank text;

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS counterparty_name text;

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS transaction_description text;

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS reference_number text;

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS status text NOT NULL; -- 'pending', 'completed', 'failed', 'cancelled', 'reversed'

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS fees_amount numeric(15,2) DEFAULT 0.0;

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS running_balance numeric(15,2);

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS risk_flags jsonb DEFAULT '[]';

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS monitoring_status text DEFAULT 'clear'; -- 'clear', 'flagged', 'under_review', 'reported'

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS external_data jsonb DEFAULT '{}';

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS sync_status text DEFAULT 'synced'; -- 'synced', 'pending', 'conflict', 'error'

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.core_banking_transactions
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Add indexes for Phase 5 enterprise integrations performance
CREATE INDEX IF NOT EXISTS idx_integration_systems_tenant ON public.integration_systems(tenant_id);
CREATE INDEX IF NOT EXISTS idx_integration_systems_type ON public.integration_systems(system_type);
CREATE INDEX IF NOT EXISTS idx_integration_systems_status ON public.integration_systems(status);
CREATE INDEX IF NOT EXISTS idx_integration_systems_next_sync ON public.integration_systems(next_sync_at);

CREATE INDEX IF NOT EXISTS idx_integration_logs_system ON public.integration_logs(integration_system_id);
CREATE INDEX IF NOT EXISTS idx_integration_logs_status ON public.integration_logs(status);
CREATE INDEX IF NOT EXISTS idx_integration_logs_created ON public.integration_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_integration_logs_operation ON public.integration_logs(operation_type);

CREATE INDEX IF NOT EXISTS idx_grc_risk_registers_tenant ON public.grc_risk_registers(tenant_id);
CREATE INDEX IF NOT EXISTS idx_grc_risk_registers_system ON public.grc_risk_registers(integration_system_id);
CREATE INDEX IF NOT EXISTS idx_grc_risk_registers_external ON public.grc_risk_registers(external_risk_id);
CREATE INDEX IF NOT EXISTS idx_grc_risk_registers_category ON public.grc_risk_registers(risk_category);

CREATE INDEX IF NOT EXISTS idx_external_data_sources_tenant ON public.external_data_sources(tenant_id);
CREATE INDEX IF NOT EXISTS idx_external_data_sources_type ON public.external_data_sources(source_type);
CREATE INDEX IF NOT EXISTS idx_external_data_sources_provider ON public.external_data_sources(provider);
CREATE INDEX IF NOT EXISTS idx_external_data_sources_next_check ON public.external_data_sources(next_update_check);

CREATE INDEX IF NOT EXISTS idx_sanctions_screening_tenant ON public.sanctions_screening_results(tenant_id);
CREATE INDEX IF NOT EXISTS idx_sanctions_screening_customer ON public.sanctions_screening_results(customer_id);
CREATE INDEX IF NOT EXISTS idx_sanctions_screening_transaction ON public.sanctions_screening_results(transaction_id);
CREATE INDEX IF NOT EXISTS idx_sanctions_screening_status ON public.sanctions_screening_results(match_status);
CREATE INDEX IF NOT EXISTS idx_sanctions_screening_date ON public.sanctions_screening_results(screening_date);

CREATE INDEX IF NOT EXISTS idx_document_repositories_tenant ON public.document_repositories(tenant_id);
CREATE INDEX IF NOT EXISTS idx_document_repositories_type ON public.document_repositories(repository_type);
CREATE INDEX IF NOT EXISTS idx_document_repositories_status ON public.document_repositories(status);

CREATE INDEX IF NOT EXISTS idx_document_lifecycle_tenant ON public.document_lifecycle(tenant_id);
CREATE INDEX IF NOT EXISTS idx_document_lifecycle_repository ON public.document_lifecycle(repository_id);
CREATE INDEX IF NOT EXISTS idx_document_lifecycle_type ON public.document_lifecycle(document_type);
CREATE INDEX IF NOT EXISTS idx_document_lifecycle_status ON public.document_lifecycle(status);
CREATE INDEX IF NOT EXISTS idx_document_lifecycle_stage ON public.document_lifecycle(lifecycle_stage);

CREATE INDEX IF NOT EXISTS idx_core_banking_transactions_tenant ON public.core_banking_transactions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_core_banking_transactions_system ON public.core_banking_transactions(integration_system_id);
CREATE INDEX IF NOT EXISTS idx_core_banking_transactions_external ON public.core_banking_transactions(external_transaction_id);
CREATE INDEX IF NOT EXISTS idx_core_banking_transactions_account ON public.core_banking_transactions(account_number);
CREATE INDEX IF NOT EXISTS idx_core_banking_transactions_date ON public.core_banking_transactions(transaction_date);

-- Foreign key constraints for Phase 5
ALTER TABLE public.grc_risk_registers 
    ADD CONSTRAINT fk_grc_risk_registers_system 
    FOREIGN KEY (integration_system_id) REFERENCES public.integration_systems(id) ON DELETE CASCADE;

ALTER TABLE public.sanctions_screening_results 
    ADD CONSTRAINT fk_sanctions_screening_source 
    FOREIGN KEY (data_source_id) REFERENCES public.external_data_sources(id) ON DELETE RESTRICT;

ALTER TABLE public.document_lifecycle 
    ADD CONSTRAINT fk_document_lifecycle_repository 
    FOREIGN KEY (repository_id) REFERENCES public.document_repositories(id) ON DELETE CASCADE;

ALTER TABLE public.core_banking_transactions 
    ADD CONSTRAINT fk_core_banking_transactions_system 
    FOREIGN KEY (integration_system_id) REFERENCES public.integration_systems(id) ON DELETE CASCADE;

-- Add check constraints for Phase 5
ALTER TABLE public.integration_systems ADD CONSTRAINT chk_system_type 
    CHECK (system_type IN ('grc', 'core_banking', 'external_data', 'document_management', 'risk_system', 'reporting_system'));

ALTER TABLE public.integration_systems ADD CONSTRAINT chk_authentication_type 
    CHECK (authentication_type IN ('oauth2', 'api_key', 'basic_auth', 'certificate', 'saml', 'jwt'));

ALTER TABLE public.integration_systems ADD CONSTRAINT chk_integration_status 
    CHECK (status IN ('active', 'inactive', 'error', 'maintenance', 'testing'));

ALTER TABLE public.integration_logs ADD CONSTRAINT chk_integration_operation_type 
    CHECK (operation_type IN ('sync', 'push', 'pull', 'health_check', 'authentication', 'batch_import', 'real_time_feed'));

ALTER TABLE public.integration_logs ADD CONSTRAINT chk_integration_log_status 
    CHECK (status IN ('success', 'error', 'warning', 'timeout', 'cancelled', 'partial_success'));

ALTER TABLE public.grc_risk_registers ADD CONSTRAINT chk_grc_risk_category 
    CHECK (risk_category IN ('operational', 'credit', 'market', 'liquidity', 'compliance', 'strategic', 'reputational', 'technology'));

ALTER TABLE public.grc_risk_registers ADD CONSTRAINT chk_grc_risk_rating 
    CHECK (inherent_risk_rating IN ('critical', 'high', 'medium', 'low') AND residual_risk_rating IN ('critical', 'high', 'medium', 'low'));

ALTER TABLE public.external_data_sources ADD CONSTRAINT chk_external_source_type 
    CHECK (source_type IN ('sanctions', 'pep', 'credit_bureau', 'market_data', 'regulatory_database', 'watchlist', 'news_media'));

ALTER TABLE public.external_data_sources ADD CONSTRAINT chk_external_data_format 
    CHECK (data_format IN ('xml', 'json', 'csv', 'pdf', 'api', 'excel', 'fixed_width'));

ALTER TABLE public.sanctions_screening_results ADD CONSTRAINT chk_sanctions_match_status 
    CHECK (match_status IN ('no_match', 'possible_match', 'confirmed_match', 'false_positive', 'under_investigation'));

ALTER TABLE public.sanctions_screening_results ADD CONSTRAINT chk_sanctions_review_status 
    CHECK (review_status IN ('pending', 'reviewed', 'cleared', 'escalated', 'requires_investigation'));

ALTER TABLE public.document_repositories ADD CONSTRAINT chk_document_repository_type 
    CHECK (repository_type IN ('sharepoint', 'box', 'google_drive', 'dropbox', 'aws_s3', 'azure_blob', 'onedrive'));

ALTER TABLE public.document_lifecycle ADD CONSTRAINT chk_document_lifecycle_stage 
    CHECK (lifecycle_stage IN ('creation', 'review', 'approval', 'publication', 'maintenance', 'retirement', 'archived'));

ALTER TABLE public.document_lifecycle ADD CONSTRAINT chk_document_approval_status 
    CHECK (approval_status IN ('pending', 'approved', 'rejected', 'requires_revision', 'under_review'));

ALTER TABLE public.core_banking_transactions ADD CONSTRAINT chk_core_banking_status 
    CHECK (status IN ('pending', 'completed', 'failed', 'cancelled', 'reversed', 'processing'));

ALTER TABLE public.core_banking_transactions ADD CONSTRAINT chk_core_banking_monitoring 
    CHECK (monitoring_status IN ('clear', 'flagged', 'under_review', 'reported', 'exempted'));

-- Comments for Phase 5 tables
COMMENT ON TABLE public.integration_systems IS 'Configuration and management of external system integrations (GRC, Core Banking, Document Management)';
COMMENT ON TABLE public.integration_logs IS 'Comprehensive logging of all integration operations with performance metrics and error tracking';
COMMENT ON TABLE public.grc_risk_registers IS 'Synchronized risk register data from GRC systems with bidirectional updates';
COMMENT ON TABLE public.external_data_sources IS 'Configuration for external data providers (OFAC, credit bureaus, market data)';
COMMENT ON TABLE public.sanctions_screening_results IS 'Results from sanctions and watchlist screening with review workflow';
COMMENT ON TABLE public.document_repositories IS 'Document management system integrations with sync and lifecycle management';
COMMENT ON TABLE public.document_lifecycle IS 'Document lifecycle tracking with approval workflows and compliance metadata';
COMMENT ON TABLE public.core_banking_transactions IS 'Real-time transaction data synchronized from core banking systems';

-- ============================================================================
-- PHASE 6: ADVANCED AI & AUTOMATION TABLES
-- ============================================================================

-- Step 1: Create nlp_models table with primary key
CREATE TABLE IF NOT EXISTS public.nlp_models (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to nlp_models
ALTER TABLE public.nlp_models
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.nlp_models
    ADD COLUMN IF NOT EXISTS model_name text NOT NULL;

ALTER TABLE public.nlp_models
    ADD COLUMN IF NOT EXISTS model_type text NOT NULL; -- 'policy_interpretation', 'contract_analysis', 'qa_chatbot', 'entity_extraction', 'sentiment_analysis'

ALTER TABLE public.nlp_models
    ADD COLUMN IF NOT EXISTS model_provider text NOT NULL; -- 'openai', 'claude', 'huggingface', 'spacy', 'custom'

ALTER TABLE public.nlp_models
    ADD COLUMN IF NOT EXISTS model_version text NOT NULL DEFAULT '1.0';

ALTER TABLE public.nlp_models
    ADD COLUMN IF NOT EXISTS language_support jsonb NOT NULL DEFAULT '["en"]';

ALTER TABLE public.nlp_models
    ADD COLUMN IF NOT EXISTS capabilities jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.nlp_models
    ADD COLUMN IF NOT EXISTS model_config jsonb NOT NULL DEFAULT '{}';

ALTER TABLE public.nlp_models
    ADD COLUMN IF NOT EXISTS training_data_info jsonb DEFAULT '{}';

ALTER TABLE public.nlp_models
    ADD COLUMN IF NOT EXISTS performance_metrics jsonb DEFAULT '{}';

ALTER TABLE public.nlp_models
    ADD COLUMN IF NOT EXISTS accuracy_score numeric(5,4);

ALTER TABLE public.nlp_models
    ADD COLUMN IF NOT EXISTS model_status text NOT NULL DEFAULT 'training'; -- 'training', 'testing', 'production', 'deprecated', 'failed'

ALTER TABLE public.nlp_models
    ADD COLUMN IF NOT EXISTS deployment_date timestamp with time zone;

ALTER TABLE public.nlp_models
    ADD COLUMN IF NOT EXISTS last_updated timestamp with time zone;

ALTER TABLE public.nlp_models
    ADD COLUMN IF NOT EXISTS usage_count integer DEFAULT 0;

ALTER TABLE public.nlp_models
    ADD COLUMN IF NOT EXISTS average_response_time_ms integer;

ALTER TABLE public.nlp_models
    ADD COLUMN IF NOT EXISTS created_by uuid NOT NULL REFERENCES public.users(id);

ALTER TABLE public.nlp_models
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.nlp_models
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create nlp_processing_results table with primary key
CREATE TABLE IF NOT EXISTS public.nlp_processing_results (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to nlp_processing_results
ALTER TABLE public.nlp_processing_results
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.nlp_processing_results
    ADD COLUMN IF NOT EXISTS model_id uuid NOT NULL REFERENCES public.nlp_models(id);

ALTER TABLE public.nlp_processing_results
    ADD COLUMN IF NOT EXISTS processing_type text NOT NULL; -- 'policy_analysis', 'contract_extraction', 'qa_response', 'entity_recognition', 'classification'

ALTER TABLE public.nlp_processing_results
    ADD COLUMN IF NOT EXISTS input_text text NOT NULL;

ALTER TABLE public.nlp_processing_results
    ADD COLUMN IF NOT EXISTS input_metadata jsonb DEFAULT '{}';

ALTER TABLE public.nlp_processing_results
    ADD COLUMN IF NOT EXISTS processed_output jsonb NOT NULL;

ALTER TABLE public.nlp_processing_results
    ADD COLUMN IF NOT EXISTS extracted_entities jsonb DEFAULT '[]';

ALTER TABLE public.nlp_processing_results
    ADD COLUMN IF NOT EXISTS key_phrases jsonb DEFAULT '[]';

ALTER TABLE public.nlp_processing_results
    ADD COLUMN IF NOT EXISTS sentiment_score numeric(5,4);

ALTER TABLE public.nlp_processing_results
    ADD COLUMN IF NOT EXISTS confidence_score numeric(5,4) NOT NULL;

ALTER TABLE public.nlp_processing_results
    ADD COLUMN IF NOT EXISTS processing_time_ms integer;

ALTER TABLE public.nlp_processing_results
    ADD COLUMN IF NOT EXISTS token_count integer;

ALTER TABLE public.nlp_processing_results
    ADD COLUMN IF NOT EXISTS cost_estimate numeric(10,4);

ALTER TABLE public.nlp_processing_results
    ADD COLUMN IF NOT EXISTS validation_status text DEFAULT 'pending'; -- 'pending', 'validated', 'rejected', 'requires_review'

ALTER TABLE public.nlp_processing_results
    ADD COLUMN IF NOT EXISTS validated_by uuid REFERENCES public.users(id);

ALTER TABLE public.nlp_processing_results
    ADD COLUMN IF NOT EXISTS validation_notes text;

ALTER TABLE public.nlp_processing_results
    ADD COLUMN IF NOT EXISTS related_document_id uuid REFERENCES public.regulatory_documents(id);

ALTER TABLE public.nlp_processing_results
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create computer_vision_models table with primary key
CREATE TABLE IF NOT EXISTS public.computer_vision_models (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to computer_vision_models
ALTER TABLE public.computer_vision_models
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.computer_vision_models
    ADD COLUMN IF NOT EXISTS model_name text NOT NULL;

ALTER TABLE public.computer_vision_models
    ADD COLUMN IF NOT EXISTS model_type text NOT NULL; -- 'document_classification', 'kyc_verification', 'signature_recognition', 'ocr', 'form_extraction'

ALTER TABLE public.computer_vision_models
    ADD COLUMN IF NOT EXISTS model_provider text NOT NULL; -- 'aws_textract', 'azure_form_recognizer', 'google_vision', 'custom_model'

ALTER TABLE public.computer_vision_models
    ADD COLUMN IF NOT EXISTS model_version text NOT NULL DEFAULT '1.0';

ALTER TABLE public.computer_vision_models
    ADD COLUMN IF NOT EXISTS supported_formats jsonb NOT NULL DEFAULT '["pdf", "jpg", "png"]';

ALTER TABLE public.computer_vision_models
    ADD COLUMN IF NOT EXISTS model_architecture text; -- 'cnn', 'transformer', 'rcnn', 'yolo', 'custom'

ALTER TABLE public.computer_vision_models
    ADD COLUMN IF NOT EXISTS model_config jsonb NOT NULL DEFAULT '{}';

ALTER TABLE public.computer_vision_models
    ADD COLUMN IF NOT EXISTS training_dataset_info jsonb DEFAULT '{}';

ALTER TABLE public.computer_vision_models
    ADD COLUMN IF NOT EXISTS performance_metrics jsonb DEFAULT '{}';

ALTER TABLE public.computer_vision_models
    ADD COLUMN IF NOT EXISTS accuracy_percentage numeric(5,2);

ALTER TABLE public.computer_vision_models
    ADD COLUMN IF NOT EXISTS precision_score numeric(5,4);

ALTER TABLE public.computer_vision_models
    ADD COLUMN IF NOT EXISTS recall_score numeric(5,4);

ALTER TABLE public.computer_vision_models
    ADD COLUMN IF NOT EXISTS f1_score numeric(5,4);

ALTER TABLE public.computer_vision_models
    ADD COLUMN IF NOT EXISTS model_status text NOT NULL DEFAULT 'training'; -- 'training', 'testing', 'production', 'deprecated', 'failed'

ALTER TABLE public.computer_vision_models
    ADD COLUMN IF NOT EXISTS deployment_date timestamp with time zone;

ALTER TABLE public.computer_vision_models
    ADD COLUMN IF NOT EXISTS usage_count integer DEFAULT 0;

ALTER TABLE public.computer_vision_models
    ADD COLUMN IF NOT EXISTS average_processing_time_ms integer;

ALTER TABLE public.computer_vision_models
    ADD COLUMN IF NOT EXISTS created_by uuid NOT NULL REFERENCES public.users(id);

ALTER TABLE public.computer_vision_models
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.computer_vision_models
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create document_processing_results table with primary key
CREATE TABLE IF NOT EXISTS public.document_processing_results (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to document_processing_results
ALTER TABLE public.document_processing_results
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.document_processing_results
    ADD COLUMN IF NOT EXISTS model_id uuid NOT NULL REFERENCES public.computer_vision_models(id);

ALTER TABLE public.document_processing_results
    ADD COLUMN IF NOT EXISTS document_id uuid REFERENCES public.regulatory_documents(id);

ALTER TABLE public.document_processing_results
    ADD COLUMN IF NOT EXISTS processing_type text NOT NULL; -- 'classification', 'kyc_verification', 'signature_detection', 'ocr_extraction', 'form_parsing'

ALTER TABLE public.document_processing_results
    ADD COLUMN IF NOT EXISTS file_path text NOT NULL;

ALTER TABLE public.document_processing_results
    ADD COLUMN IF NOT EXISTS file_type text NOT NULL;

ALTER TABLE public.document_processing_results
    ADD COLUMN IF NOT EXISTS file_size_bytes bigint;

ALTER TABLE public.document_processing_results
    ADD COLUMN IF NOT EXISTS document_classification jsonb DEFAULT '{}';

ALTER TABLE public.document_processing_results
    ADD COLUMN IF NOT EXISTS extracted_text text;

ALTER TABLE public.document_processing_results
    ADD COLUMN IF NOT EXISTS extracted_fields jsonb DEFAULT '{}';

ALTER TABLE public.document_processing_results
    ADD COLUMN IF NOT EXISTS detected_signatures jsonb DEFAULT '[]';

ALTER TABLE public.document_processing_results
    ADD COLUMN IF NOT EXISTS verification_results jsonb DEFAULT '{}';

ALTER TABLE public.document_processing_results
    ADD COLUMN IF NOT EXISTS confidence_scores jsonb DEFAULT '{}';

ALTER TABLE public.document_processing_results
    ADD COLUMN IF NOT EXISTS quality_score numeric(5,4);

ALTER TABLE public.document_processing_results
    ADD COLUMN IF NOT EXISTS processing_time_ms integer;

ALTER TABLE public.document_processing_results
    ADD COLUMN IF NOT EXISTS processing_cost numeric(10,4);

ALTER TABLE public.document_processing_results
    ADD COLUMN IF NOT EXISTS validation_status text DEFAULT 'pending'; -- 'pending', 'validated', 'rejected', 'requires_manual_review'

ALTER TABLE public.document_processing_results
    ADD COLUMN IF NOT EXISTS validated_by uuid REFERENCES public.users(id);

ALTER TABLE public.document_processing_results
    ADD COLUMN IF NOT EXISTS validation_notes text;

ALTER TABLE public.document_processing_results
    ADD COLUMN IF NOT EXISTS error_message text;

ALTER TABLE public.document_processing_results
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create ml_experiments table with primary key
CREATE TABLE IF NOT EXISTS public.ml_experiments (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to ml_experiments
ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS experiment_name text NOT NULL;

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS experiment_type text NOT NULL; -- 'deep_learning', 'reinforcement_learning', 'automl', 'ensemble', 'transfer_learning'

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS objective text NOT NULL; -- 'classification', 'regression', 'clustering', 'anomaly_detection', 'optimization'

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS algorithm_framework text NOT NULL; -- 'tensorflow', 'pytorch', 'scikit_learn', 'xgboost', 'auto_sklearn'

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS model_architecture jsonb DEFAULT '{}';

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS hyperparameters jsonb DEFAULT '{}';

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS dataset_info jsonb NOT NULL;

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS feature_engineering jsonb DEFAULT '{}';

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS training_config jsonb DEFAULT '{}';

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS validation_strategy text NOT NULL; -- 'k_fold', 'time_series_split', 'stratified', 'holdout'

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS experiment_status text NOT NULL DEFAULT 'pending'; -- 'pending', 'running', 'completed', 'failed', 'cancelled'

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS training_metrics jsonb DEFAULT '{}';

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS validation_metrics jsonb DEFAULT '{}';

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS test_metrics jsonb DEFAULT '{}';

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS feature_importance jsonb DEFAULT '{}';

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS model_interpretability jsonb DEFAULT '{}';

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS training_duration_seconds integer;

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS resource_usage jsonb DEFAULT '{}';

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS model_artifacts_path text;

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS deployment_ready boolean DEFAULT false;

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS tags jsonb DEFAULT '[]';

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS notes text;

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS created_by uuid NOT NULL REFERENCES public.users(id);

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS started_at timestamp with time zone;

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS completed_at timestamp with time zone;

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.ml_experiments
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create automl_pipelines table with primary key
CREATE TABLE IF NOT EXISTS public.automl_pipelines (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to automl_pipelines
ALTER TABLE public.automl_pipelines
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.automl_pipelines
    ADD COLUMN IF NOT EXISTS pipeline_name text NOT NULL;

ALTER TABLE public.automl_pipelines
    ADD COLUMN IF NOT EXISTS pipeline_type text NOT NULL; -- 'automated_feature_engineering', 'hyperparameter_optimization', 'neural_architecture_search', 'full_automl'

ALTER TABLE public.automl_pipelines
    ADD COLUMN IF NOT EXISTS target_metric text NOT NULL; -- 'accuracy', 'precision', 'recall', 'f1_score', 'auc_roc', 'mse', 'mae'

ALTER TABLE public.automl_pipelines
    ADD COLUMN IF NOT EXISTS search_space jsonb NOT NULL DEFAULT '{}';

ALTER TABLE public.automl_pipelines
    ADD COLUMN IF NOT EXISTS optimization_strategy text NOT NULL; -- 'random_search', 'grid_search', 'bayesian_optimization', 'genetic_algorithm'

ALTER TABLE public.automl_pipelines
    ADD COLUMN IF NOT EXISTS max_iterations integer DEFAULT 100;

ALTER TABLE public.automl_pipelines
    ADD COLUMN IF NOT EXISTS time_budget_minutes integer DEFAULT 60;

ALTER TABLE public.automl_pipelines
    ADD COLUMN IF NOT EXISTS early_stopping_config jsonb DEFAULT '{}';

ALTER TABLE public.automl_pipelines
    ADD COLUMN IF NOT EXISTS best_model_config jsonb DEFAULT '{}';

ALTER TABLE public.automl_pipelines
    ADD COLUMN IF NOT EXISTS best_score numeric(10,6);

ALTER TABLE public.automl_pipelines
    ADD COLUMN IF NOT EXISTS trials_completed integer DEFAULT 0;

ALTER TABLE public.automl_pipelines
    ADD COLUMN IF NOT EXISTS pipeline_status text NOT NULL DEFAULT 'pending'; -- 'pending', 'running', 'completed', 'failed', 'stopped'

ALTER TABLE public.automl_pipelines
    ADD COLUMN IF NOT EXISTS optimization_history jsonb DEFAULT '[]';

ALTER TABLE public.automl_pipelines
    ADD COLUMN IF NOT EXISTS feature_selection_results jsonb DEFAULT '{}';

ALTER TABLE public.automl_pipelines
    ADD COLUMN IF NOT EXISTS ensemble_config jsonb DEFAULT '{}';

ALTER TABLE public.automl_pipelines
    ADD COLUMN IF NOT EXISTS created_by uuid NOT NULL REFERENCES public.users(id);

ALTER TABLE public.automl_pipelines
    ADD COLUMN IF NOT EXISTS started_at timestamp with time zone;

ALTER TABLE public.automl_pipelines
    ADD COLUMN IF NOT EXISTS completed_at timestamp with time zone;

ALTER TABLE public.automl_pipelines
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.automl_pipelines
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create automation_workflows table with primary key
CREATE TABLE IF NOT EXISTS public.automation_workflows (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to automation_workflows
ALTER TABLE public.automation_workflows
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.automation_workflows
    ADD COLUMN IF NOT EXISTS workflow_name text NOT NULL;

ALTER TABLE public.automation_workflows
    ADD COLUMN IF NOT EXISTS workflow_type text NOT NULL; -- 'rpa_integration', 'document_processing', 'data_extraction', 'compliance_monitoring', 'report_generation'

ALTER TABLE public.automation_workflows
    ADD COLUMN IF NOT EXISTS automation_level text NOT NULL; -- 'fully_automated', 'human_in_loop', 'supervised', 'semi_automated'

ALTER TABLE public.automation_workflows
    ADD COLUMN IF NOT EXISTS trigger_conditions jsonb NOT NULL DEFAULT '{}';

ALTER TABLE public.automation_workflows
    ADD COLUMN IF NOT EXISTS process_steps jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.automation_workflows
    ADD COLUMN IF NOT EXISTS decision_logic jsonb DEFAULT '{}';

ALTER TABLE public.automation_workflows
    ADD COLUMN IF NOT EXISTS integration_configs jsonb DEFAULT '{}';

ALTER TABLE public.automation_workflows
    ADD COLUMN IF NOT EXISTS rpa_tool_config jsonb DEFAULT '{}'; -- UiPath, Blue Prism, Automation Anywhere configs

ALTER TABLE public.automation_workflows
    ADD COLUMN IF NOT EXISTS quality_controls jsonb DEFAULT '[]';

ALTER TABLE public.automation_workflows
    ADD COLUMN IF NOT EXISTS error_handling jsonb DEFAULT '{}';

ALTER TABLE public.automation_workflows
    ADD COLUMN IF NOT EXISTS escalation_rules jsonb DEFAULT '[]';

ALTER TABLE public.automation_workflows
    ADD COLUMN IF NOT EXISTS sla_config jsonb DEFAULT '{}';

ALTER TABLE public.automation_workflows
    ADD COLUMN IF NOT EXISTS success_rate numeric(5,2) DEFAULT 0.0;

ALTER TABLE public.automation_workflows
    ADD COLUMN IF NOT EXISTS average_processing_time_minutes integer;

ALTER TABLE public.automation_workflows
    ADD COLUMN IF NOT EXISTS cost_per_execution numeric(10,4);

ALTER TABLE public.automation_workflows
    ADD COLUMN IF NOT EXISTS workflow_status text NOT NULL DEFAULT 'draft'; -- 'draft', 'testing', 'active', 'paused', 'deprecated'

ALTER TABLE public.automation_workflows
    ADD COLUMN IF NOT EXISTS last_execution_at timestamp with time zone;

ALTER TABLE public.automation_workflows
    ADD COLUMN IF NOT EXISTS total_executions integer DEFAULT 0;

ALTER TABLE public.automation_workflows
    ADD COLUMN IF NOT EXISTS successful_executions integer DEFAULT 0;

ALTER TABLE public.automation_workflows
    ADD COLUMN IF NOT EXISTS created_by uuid NOT NULL REFERENCES public.users(id);

ALTER TABLE public.automation_workflows
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.automation_workflows
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create automation_executions table with primary key
CREATE TABLE IF NOT EXISTS public.automation_executions (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to automation_executions
ALTER TABLE public.automation_executions
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.automation_executions
    ADD COLUMN IF NOT EXISTS workflow_id uuid NOT NULL REFERENCES public.automation_workflows(id);

ALTER TABLE public.automation_executions
    ADD COLUMN IF NOT EXISTS execution_trigger text NOT NULL; -- 'scheduled', 'manual', 'event_driven', 'api_request'

ALTER TABLE public.automation_executions
    ADD COLUMN IF NOT EXISTS input_data jsonb DEFAULT '{}';

ALTER TABLE public.automation_executions
    ADD COLUMN IF NOT EXISTS execution_status text NOT NULL; -- 'pending', 'running', 'completed', 'failed', 'partially_completed', 'cancelled'

ALTER TABLE public.automation_executions
    ADD COLUMN IF NOT EXISTS steps_completed jsonb DEFAULT '[]';

ALTER TABLE public.automation_executions
    ADD COLUMN IF NOT EXISTS current_step text;

ALTER TABLE public.automation_executions
    ADD COLUMN IF NOT EXISTS output_data jsonb DEFAULT '{}';

ALTER TABLE public.automation_executions
    ADD COLUMN IF NOT EXISTS quality_score numeric(5,2);

ALTER TABLE public.automation_executions
    ADD COLUMN IF NOT EXISTS human_interventions integer DEFAULT 0;

ALTER TABLE public.automation_executions
    ADD COLUMN IF NOT EXISTS error_messages jsonb DEFAULT '[]';

ALTER TABLE public.automation_executions
    ADD COLUMN IF NOT EXISTS performance_metrics jsonb DEFAULT '{}';

ALTER TABLE public.automation_executions
    ADD COLUMN IF NOT EXISTS cost_incurred numeric(10,4);

ALTER TABLE public.automation_executions
    ADD COLUMN IF NOT EXISTS time_saved_minutes integer;

ALTER TABLE public.automation_executions
    ADD COLUMN IF NOT EXISTS compliance_validated boolean DEFAULT false;

ALTER TABLE public.automation_executions
    ADD COLUMN IF NOT EXISTS audit_trail jsonb DEFAULT '[]';

ALTER TABLE public.automation_executions
    ADD COLUMN IF NOT EXISTS triggered_by uuid REFERENCES public.users(id);

ALTER TABLE public.automation_executions
    ADD COLUMN IF NOT EXISTS started_at timestamp with time zone NOT NULL;

ALTER TABLE public.automation_executions
    ADD COLUMN IF NOT EXISTS completed_at timestamp with time zone;

ALTER TABLE public.automation_executions
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create intelligent_document_processing table with primary key
CREATE TABLE IF NOT EXISTS public.intelligent_document_processing (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to intelligent_document_processing
ALTER TABLE public.intelligent_document_processing
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.intelligent_document_processing
    ADD COLUMN IF NOT EXISTS document_id uuid REFERENCES public.regulatory_documents(id);

ALTER TABLE public.intelligent_document_processing
    ADD COLUMN IF NOT EXISTS processing_pipeline text NOT NULL; -- 'ocr_nlp_classification', 'form_extraction', 'contract_analysis', 'compliance_check'

ALTER TABLE public.intelligent_document_processing
    ADD COLUMN IF NOT EXISTS file_path text NOT NULL;

ALTER TABLE public.intelligent_document_processing
    ADD COLUMN IF NOT EXISTS file_metadata jsonb DEFAULT '{}';

ALTER TABLE public.intelligent_document_processing
    ADD COLUMN IF NOT EXISTS ocr_results jsonb DEFAULT '{}';

ALTER TABLE public.intelligent_document_processing
    ADD COLUMN IF NOT EXISTS nlp_analysis jsonb DEFAULT '{}';

ALTER TABLE public.intelligent_document_processing
    ADD COLUMN IF NOT EXISTS classification_results jsonb DEFAULT '{}';

ALTER TABLE public.intelligent_document_processing
    ADD COLUMN IF NOT EXISTS extracted_data jsonb DEFAULT '{}';

ALTER TABLE public.intelligent_document_processing
    ADD COLUMN IF NOT EXISTS compliance_findings jsonb DEFAULT '[]';

ALTER TABLE public.intelligent_document_processing
    ADD COLUMN IF NOT EXISTS risk_indicators jsonb DEFAULT '[]';

ALTER TABLE public.intelligent_document_processing
    ADD COLUMN IF NOT EXISTS automation_decisions jsonb DEFAULT '{}';

ALTER TABLE public.intelligent_document_processing
    ADD COLUMN IF NOT EXISTS human_review_required boolean DEFAULT false;

ALTER TABLE public.intelligent_document_processing
    ADD COLUMN IF NOT EXISTS confidence_aggregate numeric(5,4);

ALTER TABLE public.intelligent_document_processing
    ADD COLUMN IF NOT EXISTS processing_time_ms integer;

ALTER TABLE public.intelligent_document_processing
    ADD COLUMN IF NOT EXISTS total_cost numeric(10,4);

ALTER TABLE public.intelligent_document_processing
    ADD COLUMN IF NOT EXISTS processing_status text NOT NULL; -- 'pending', 'processing', 'completed', 'failed', 'requires_review'

ALTER TABLE public.intelligent_document_processing
    ADD COLUMN IF NOT EXISTS error_details text;

ALTER TABLE public.intelligent_document_processing
    ADD COLUMN IF NOT EXISTS reviewed_by uuid REFERENCES public.users(id);

ALTER TABLE public.intelligent_document_processing
    ADD COLUMN IF NOT EXISTS review_notes text;

ALTER TABLE public.intelligent_document_processing
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.intelligent_document_processing
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create chatbot_conversations table with primary key
CREATE TABLE IF NOT EXISTS public.chatbot_conversations (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to chatbot_conversations
ALTER TABLE public.chatbot_conversations
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL REFERENCES public.tenants(id);

ALTER TABLE public.chatbot_conversations
    ADD COLUMN IF NOT EXISTS user_id uuid REFERENCES public.users(id);

ALTER TABLE public.chatbot_conversations
    ADD COLUMN IF NOT EXISTS session_id text NOT NULL;

ALTER TABLE public.chatbot_conversations
    ADD COLUMN IF NOT EXISTS chatbot_type text NOT NULL; -- 'regulatory_qa', 'compliance_assistant', 'risk_advisor', 'general_support'

ALTER TABLE public.chatbot_conversations
    ADD COLUMN IF NOT EXISTS conversation_title text;

ALTER TABLE public.chatbot_conversations
    ADD COLUMN IF NOT EXISTS conversation_context jsonb DEFAULT '{}';

ALTER TABLE public.chatbot_conversations
    ADD COLUMN IF NOT EXISTS message_history jsonb NOT NULL DEFAULT '[]';

ALTER TABLE public.chatbot_conversations
    ADD COLUMN IF NOT EXISTS user_satisfaction_score integer; -- 1-5 rating

ALTER TABLE public.chatbot_conversations
    ADD COLUMN IF NOT EXISTS resolution_status text DEFAULT 'ongoing'; -- 'ongoing', 'resolved', 'escalated', 'abandoned'

ALTER TABLE public.chatbot_conversations
    ADD COLUMN IF NOT EXISTS escalated_to_human boolean DEFAULT false;

ALTER TABLE public.chatbot_conversations
    ADD COLUMN IF NOT EXISTS escalated_to_user_id uuid REFERENCES public.users(id);

ALTER TABLE public.chatbot_conversations
    ADD COLUMN IF NOT EXISTS total_messages integer DEFAULT 0;

ALTER TABLE public.chatbot_conversations
    ADD COLUMN IF NOT EXISTS conversation_duration_minutes integer;

ALTER TABLE public.chatbot_conversations
    ADD COLUMN IF NOT EXISTS topics_discussed jsonb DEFAULT '[]';

ALTER TABLE public.chatbot_conversations
    ADD COLUMN IF NOT EXISTS documents_referenced jsonb DEFAULT '[]';

ALTER TABLE public.chatbot_conversations
    ADD COLUMN IF NOT EXISTS actions_taken jsonb DEFAULT '[]';

ALTER TABLE public.chatbot_conversations
    ADD COLUMN IF NOT EXISTS feedback_provided text;

ALTER TABLE public.chatbot_conversations
    ADD COLUMN IF NOT EXISTS started_at timestamp with time zone NOT NULL;

ALTER TABLE public.chatbot_conversations
    ADD COLUMN IF NOT EXISTS ended_at timestamp with time zone;

ALTER TABLE public.chatbot_conversations
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.chatbot_conversations
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL;

-- Add indexes for Phase 6 performance optimization
CREATE INDEX IF NOT EXISTS idx_nlp_models_tenant ON public.nlp_models(tenant_id);
CREATE INDEX IF NOT EXISTS idx_nlp_models_type ON public.nlp_models(model_type);
CREATE INDEX IF NOT EXISTS idx_nlp_models_status ON public.nlp_models(model_status);

CREATE INDEX IF NOT EXISTS idx_nlp_processing_tenant ON public.nlp_processing_results(tenant_id);
CREATE INDEX IF NOT EXISTS idx_nlp_processing_model ON public.nlp_processing_results(model_id);
CREATE INDEX IF NOT EXISTS idx_nlp_processing_type ON public.nlp_processing_results(processing_type);
CREATE INDEX IF NOT EXISTS idx_nlp_processing_created ON public.nlp_processing_results(created_at);

CREATE INDEX IF NOT EXISTS idx_cv_models_tenant ON public.computer_vision_models(tenant_id);
CREATE INDEX IF NOT EXISTS idx_cv_models_type ON public.computer_vision_models(model_type);
CREATE INDEX IF NOT EXISTS idx_cv_models_status ON public.computer_vision_models(model_status);

CREATE INDEX IF NOT EXISTS idx_doc_processing_tenant ON public.document_processing_results(tenant_id);
CREATE INDEX IF NOT EXISTS idx_doc_processing_model ON public.document_processing_results(model_id);
CREATE INDEX IF NOT EXISTS idx_doc_processing_type ON public.document_processing_results(processing_type);
CREATE INDEX IF NOT EXISTS idx_doc_processing_created ON public.document_processing_results(created_at);

CREATE INDEX IF NOT EXISTS idx_ml_experiments_tenant ON public.ml_experiments(tenant_id);
CREATE INDEX IF NOT EXISTS idx_ml_experiments_type ON public.ml_experiments(experiment_type);
CREATE INDEX IF NOT EXISTS idx_ml_experiments_status ON public.ml_experiments(experiment_status);
CREATE INDEX IF NOT EXISTS idx_ml_experiments_created ON public.ml_experiments(created_at);

CREATE INDEX IF NOT EXISTS idx_automl_pipelines_tenant ON public.automl_pipelines(tenant_id);
CREATE INDEX IF NOT EXISTS idx_automl_pipelines_type ON public.automl_pipelines(pipeline_type);
CREATE INDEX IF NOT EXISTS idx_automl_pipelines_status ON public.automl_pipelines(pipeline_status);

CREATE INDEX IF NOT EXISTS idx_automation_workflows_tenant ON public.automation_workflows(tenant_id);
CREATE INDEX IF NOT EXISTS idx_automation_workflows_type ON public.automation_workflows(workflow_type);
CREATE INDEX IF NOT EXISTS idx_automation_workflows_status ON public.automation_workflows(workflow_status);

CREATE INDEX IF NOT EXISTS idx_automation_executions_tenant ON public.automation_executions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_automation_executions_workflow ON public.automation_executions(workflow_id);
CREATE INDEX IF NOT EXISTS idx_automation_executions_status ON public.automation_executions(execution_status);
CREATE INDEX IF NOT EXISTS idx_automation_executions_started ON public.automation_executions(started_at);

CREATE INDEX IF NOT EXISTS idx_intelligent_doc_processing_tenant ON public.intelligent_document_processing(tenant_id);
CREATE INDEX IF NOT EXISTS idx_intelligent_doc_processing_document ON public.intelligent_document_processing(document_id);
CREATE INDEX IF NOT EXISTS idx_intelligent_doc_processing_pipeline ON public.intelligent_document_processing(processing_pipeline);
CREATE INDEX IF NOT EXISTS idx_intelligent_doc_processing_status ON public.intelligent_document_processing(processing_status);

CREATE INDEX IF NOT EXISTS idx_chatbot_conversations_tenant ON public.chatbot_conversations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_chatbot_conversations_user ON public.chatbot_conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_chatbot_conversations_session ON public.chatbot_conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_chatbot_conversations_type ON public.chatbot_conversations(chatbot_type);
CREATE INDEX IF NOT EXISTS idx_chatbot_conversations_started ON public.chatbot_conversations(started_at);

-- Foreign key constraints for Phase 6
ALTER TABLE public.nlp_processing_results 
    ADD CONSTRAINT fk_nlp_processing_model 
    FOREIGN KEY (model_id) REFERENCES public.nlp_models(id) ON DELETE CASCADE;

ALTER TABLE public.document_processing_results 
    ADD CONSTRAINT fk_doc_processing_model 
    FOREIGN KEY (model_id) REFERENCES public.computer_vision_models(id) ON DELETE CASCADE;

ALTER TABLE public.automation_executions 
    ADD CONSTRAINT fk_automation_executions_workflow 
    FOREIGN KEY (workflow_id) REFERENCES public.automation_workflows(id) ON DELETE CASCADE;

-- Add check constraints for Phase 6
ALTER TABLE public.nlp_models ADD CONSTRAINT chk_nlp_model_type 
    CHECK (model_type IN ('policy_interpretation', 'contract_analysis', 'qa_chatbot', 'entity_extraction', 'sentiment_analysis', 'text_classification', 'summarization'));

ALTER TABLE public.nlp_models ADD CONSTRAINT chk_nlp_model_status 
    CHECK (model_status IN ('training', 'testing', 'production', 'deprecated', 'failed'));

ALTER TABLE public.nlp_processing_results ADD CONSTRAINT chk_nlp_processing_type 
    CHECK (processing_type IN ('policy_analysis', 'contract_extraction', 'qa_response', 'entity_recognition', 'classification', 'summarization', 'sentiment_analysis'));

ALTER TABLE public.nlp_processing_results ADD CONSTRAINT chk_nlp_validation_status 
    CHECK (validation_status IN ('pending', 'validated', 'rejected', 'requires_review'));

ALTER TABLE public.computer_vision_models ADD CONSTRAINT chk_cv_model_type 
    CHECK (model_type IN ('document_classification', 'kyc_verification', 'signature_recognition', 'ocr', 'form_extraction', 'table_extraction'));

ALTER TABLE public.computer_vision_models ADD CONSTRAINT chk_cv_model_status 
    CHECK (model_status IN ('training', 'testing', 'production', 'deprecated', 'failed'));

ALTER TABLE public.document_processing_results ADD CONSTRAINT chk_doc_processing_type 
    CHECK (processing_type IN ('classification', 'kyc_verification', 'signature_detection', 'ocr_extraction', 'form_parsing', 'table_extraction'));

ALTER TABLE public.document_processing_results ADD CONSTRAINT chk_doc_validation_status 
    CHECK (validation_status IN ('pending', 'validated', 'rejected', 'requires_manual_review'));

ALTER TABLE public.ml_experiments ADD CONSTRAINT chk_ml_experiment_type 
    CHECK (experiment_type IN ('deep_learning', 'reinforcement_learning', 'automl', 'ensemble', 'transfer_learning', 'federated_learning'));

ALTER TABLE public.ml_experiments ADD CONSTRAINT chk_ml_experiment_status 
    CHECK (experiment_status IN ('pending', 'running', 'completed', 'failed', 'cancelled'));

ALTER TABLE public.automl_pipelines ADD CONSTRAINT chk_automl_pipeline_type 
    CHECK (pipeline_type IN ('automated_feature_engineering', 'hyperparameter_optimization', 'neural_architecture_search', 'full_automl'));

ALTER TABLE public.automl_pipelines ADD CONSTRAINT chk_automl_pipeline_status 
    CHECK (pipeline_status IN ('pending', 'running', 'completed', 'failed', 'stopped'));

ALTER TABLE public.automation_workflows ADD CONSTRAINT chk_automation_workflow_type 
    CHECK (workflow_type IN ('rpa_integration', 'document_processing', 'data_extraction', 'compliance_monitoring', 'report_generation', 'task_automation'));

ALTER TABLE public.automation_workflows ADD CONSTRAINT chk_automation_level 
    CHECK (automation_level IN ('fully_automated', 'human_in_loop', 'supervised', 'semi_automated'));

ALTER TABLE public.automation_workflows ADD CONSTRAINT chk_automation_workflow_status 
    CHECK (workflow_status IN ('draft', 'testing', 'active', 'paused', 'deprecated'));

ALTER TABLE public.automation_executions ADD CONSTRAINT chk_automation_execution_status 
    CHECK (execution_status IN ('pending', 'running', 'completed', 'failed', 'partially_completed', 'cancelled'));

ALTER TABLE public.intelligent_document_processing ADD CONSTRAINT chk_idp_pipeline 
    CHECK (processing_pipeline IN ('ocr_nlp_classification', 'form_extraction', 'contract_analysis', 'compliance_check', 'risk_assessment'));

ALTER TABLE public.intelligent_document_processing ADD CONSTRAINT chk_idp_status 
    CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed', 'requires_review'));

ALTER TABLE public.chatbot_conversations ADD CONSTRAINT chk_chatbot_type 
    CHECK (chatbot_type IN ('regulatory_qa', 'compliance_assistant', 'risk_advisor', 'general_support', 'document_assistant'));

ALTER TABLE public.chatbot_conversations ADD CONSTRAINT chk_resolution_status 
    CHECK (resolution_status IN ('ongoing', 'resolved', 'escalated', 'abandoned'));

-- Comments for Phase 6 tables
COMMENT ON TABLE public.nlp_models IS 'Natural Language Processing models for policy interpretation, contract analysis, and regulatory Q&A';
COMMENT ON TABLE public.nlp_processing_results IS 'Results from NLP processing with extracted entities, sentiment analysis, and validation';
COMMENT ON TABLE public.computer_vision_models IS 'Computer Vision models for document classification, KYC verification, and signature recognition';
COMMENT ON TABLE public.document_processing_results IS 'Results from computer vision document processing with confidence scores and validation';
COMMENT ON TABLE public.ml_experiments IS 'Advanced ML experiments including deep learning, reinforcement learning, and AutoML';
COMMENT ON TABLE public.automl_pipelines IS 'Automated machine learning pipelines for model optimization and feature engineering';
COMMENT ON TABLE public.automation_workflows IS 'Intelligent automation workflows with RPA integration and process orchestration';
COMMENT ON TABLE public.automation_executions IS 'Execution records for automation workflows with performance metrics and audit trails';
COMMENT ON TABLE public.intelligent_document_processing IS 'End-to-end intelligent document processing combining OCR, NLP, and classification';
COMMENT ON TABLE public.chatbot_conversations IS 'Regulatory Q&A chatbot conversations with context tracking and satisfaction scoring';

-- ============================================================================
-- UI PORTALS TABLES
-- ============================================================================

-- Step 1: Create ui_portal_sessions table with primary key
CREATE TABLE IF NOT EXISTS public.ui_portal_sessions (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to ui_portal_sessions
ALTER TABLE public.ui_portal_sessions
    ADD COLUMN IF NOT EXISTS session_id text NOT NULL;

ALTER TABLE public.ui_portal_sessions
    ADD COLUMN IF NOT EXISTS portal_type text NOT NULL;

ALTER TABLE public.ui_portal_sessions
    ADD COLUMN IF NOT EXISTS user_id uuid;

ALTER TABLE public.ui_portal_sessions
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL;

ALTER TABLE public.ui_portal_sessions
    ADD COLUMN IF NOT EXISTS ip_address inet;

ALTER TABLE public.ui_portal_sessions
    ADD COLUMN IF NOT EXISTS user_agent text;

ALTER TABLE public.ui_portal_sessions
    ADD COLUMN IF NOT EXISTS started_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.ui_portal_sessions
    ADD COLUMN IF NOT EXISTS last_activity_at timestamp with time zone DEFAULT now() NOT NULL;

ALTER TABLE public.ui_portal_sessions
    ADD COLUMN IF NOT EXISTS expires_at timestamp with time zone;

ALTER TABLE public.ui_portal_sessions
    ADD COLUMN IF NOT EXISTS is_active boolean DEFAULT true NOT NULL;

ALTER TABLE public.ui_portal_sessions
    ADD COLUMN IF NOT EXISTS session_data jsonb DEFAULT '{}'::jsonb;

-- Step 1: Create ui_search_logs table with primary key
CREATE TABLE IF NOT EXISTS public.ui_search_logs (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to ui_search_logs
ALTER TABLE public.ui_search_logs
    ADD COLUMN IF NOT EXISTS session_id uuid;

ALTER TABLE public.ui_search_logs
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL;

ALTER TABLE public.ui_search_logs
    ADD COLUMN IF NOT EXISTS search_query text NOT NULL;

ALTER TABLE public.ui_search_logs
    ADD COLUMN IF NOT EXISTS search_type text NOT NULL;

ALTER TABLE public.ui_search_logs
    ADD COLUMN IF NOT EXISTS results_count integer DEFAULT 0;

ALTER TABLE public.ui_search_logs
    ADD COLUMN IF NOT EXISTS search_filters jsonb DEFAULT '{}'::jsonb;

ALTER TABLE public.ui_search_logs
    ADD COLUMN IF NOT EXISTS execution_time_ms integer;

ALTER TABLE public.ui_search_logs
    ADD COLUMN IF NOT EXISTS clicked_result text;

ALTER TABLE public.ui_search_logs
    ADD COLUMN IF NOT EXISTS user_satisfaction integer;

ALTER TABLE public.ui_search_logs
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create ui_test_executions table with primary key
CREATE TABLE IF NOT EXISTS public.ui_test_executions (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to ui_test_executions
ALTER TABLE public.ui_test_executions
    ADD COLUMN IF NOT EXISTS session_id uuid;

ALTER TABLE public.ui_test_executions
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL;

ALTER TABLE public.ui_test_executions
    ADD COLUMN IF NOT EXISTS test_type text NOT NULL;

ALTER TABLE public.ui_test_executions
    ADD COLUMN IF NOT EXISTS service_name text NOT NULL;

ALTER TABLE public.ui_test_executions
    ADD COLUMN IF NOT EXISTS endpoint_path text NOT NULL;

ALTER TABLE public.ui_test_executions
    ADD COLUMN IF NOT EXISTS http_method text NOT NULL;

ALTER TABLE public.ui_test_executions
    ADD COLUMN IF NOT EXISTS request_data jsonb DEFAULT '{}'::jsonb;

ALTER TABLE public.ui_test_executions
    ADD COLUMN IF NOT EXISTS response_status_code integer;

ALTER TABLE public.ui_test_executions
    ADD COLUMN IF NOT EXISTS response_data jsonb DEFAULT '{}'::jsonb;

ALTER TABLE public.ui_test_executions
    ADD COLUMN IF NOT EXISTS response_time_ms integer;

ALTER TABLE public.ui_test_executions
    ADD COLUMN IF NOT EXISTS success boolean NOT NULL;

ALTER TABLE public.ui_test_executions
    ADD COLUMN IF NOT EXISTS error_message text;

ALTER TABLE public.ui_test_executions
    ADD COLUMN IF NOT EXISTS executed_at timestamp with time zone DEFAULT now() NOT NULL;

-- Step 1: Create ui_portal_analytics table with primary key
CREATE TABLE IF NOT EXISTS public.ui_portal_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY
);

-- Step 2: Add remaining fields to ui_portal_analytics
ALTER TABLE public.ui_portal_analytics
    ADD COLUMN IF NOT EXISTS tenant_id uuid NOT NULL;

ALTER TABLE public.ui_portal_analytics
    ADD COLUMN IF NOT EXISTS portal_type text NOT NULL;

ALTER TABLE public.ui_portal_analytics
    ADD COLUMN IF NOT EXISTS event_type text NOT NULL;

ALTER TABLE public.ui_portal_analytics
    ADD COLUMN IF NOT EXISTS event_data jsonb DEFAULT '{}'::jsonb;

ALTER TABLE public.ui_portal_analytics
    ADD COLUMN IF NOT EXISTS session_id uuid;

ALTER TABLE public.ui_portal_analytics
    ADD COLUMN IF NOT EXISTS user_id uuid;

ALTER TABLE public.ui_portal_analytics
    ADD COLUMN IF NOT EXISTS page_path text;

ALTER TABLE public.ui_portal_analytics
    ADD COLUMN IF NOT EXISTS duration_ms integer;

ALTER TABLE public.ui_portal_analytics
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT now() NOT NULL;

-- Create indexes for UI portal tables
CREATE INDEX IF NOT EXISTS idx_ui_portal_sessions_tenant ON public.ui_portal_sessions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_ui_portal_sessions_type ON public.ui_portal_sessions(portal_type);
CREATE INDEX IF NOT EXISTS idx_ui_portal_sessions_active ON public.ui_portal_sessions(is_active);
CREATE INDEX IF NOT EXISTS idx_ui_portal_sessions_expires ON public.ui_portal_sessions(expires_at);

CREATE INDEX IF NOT EXISTS idx_ui_search_logs_tenant ON public.ui_search_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_ui_search_logs_session ON public.ui_search_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_ui_search_logs_created ON public.ui_search_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_ui_search_logs_query ON public.ui_search_logs(search_query);

CREATE INDEX IF NOT EXISTS idx_ui_test_executions_tenant ON public.ui_test_executions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_ui_test_executions_session ON public.ui_test_executions(session_id);
CREATE INDEX IF NOT EXISTS idx_ui_test_executions_service ON public.ui_test_executions(service_name);
CREATE INDEX IF NOT EXISTS idx_ui_test_executions_executed ON public.ui_test_executions(executed_at);
CREATE INDEX IF NOT EXISTS idx_ui_test_executions_success ON public.ui_test_executions(success);

CREATE INDEX IF NOT EXISTS idx_ui_portal_analytics_tenant ON public.ui_portal_analytics(tenant_id);
CREATE INDEX IF NOT EXISTS idx_ui_portal_analytics_portal ON public.ui_portal_analytics(portal_type);
CREATE INDEX IF NOT EXISTS idx_ui_portal_analytics_event ON public.ui_portal_analytics(event_type);
CREATE INDEX IF NOT EXISTS idx_ui_portal_analytics_created ON public.ui_portal_analytics(created_at);

-- Add comments for UI portal tables
COMMENT ON TABLE public.ui_portal_sessions IS 'UI portal user sessions tracking for documentation and testing portals';
COMMENT ON TABLE public.ui_search_logs IS 'Search query logs and analytics for documentation portal';
COMMENT ON TABLE public.ui_test_executions IS 'Test execution history and results from testing portal';
COMMENT ON TABLE public.ui_portal_analytics IS 'General analytics and usage tracking for UI portals';

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================ 