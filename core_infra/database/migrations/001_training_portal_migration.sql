-- ============================================================================
-- TRAINING PORTAL MIGRATION SCRIPT
-- Version: 001
-- Description: Deploy training portal tables and initial data
-- ============================================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create migration tracking table if not exists
CREATE TABLE IF NOT EXISTS migration_history (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    migration_name text NOT NULL UNIQUE,
    applied_at timestamp with time zone DEFAULT now(),
    applied_by text DEFAULT current_user,
    description text,
    rollback_sql text
);

-- Check if migration already applied
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM migration_history WHERE migration_name = '001_training_portal_migration') THEN
        RAISE NOTICE 'Migration 001_training_portal_migration already applied, skipping...';
        RETURN;
    END IF;
END
$$;

-- ============================================================================
-- TRAINING PORTAL TABLES (from schema.sql)
-- ============================================================================

-- Training modules (courses/sections)
CREATE TABLE IF NOT EXISTS public.training_modules (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    module_code text NOT NULL UNIQUE,
    title text NOT NULL,
    description text,
    category text NOT NULL,
    difficulty_level text NOT NULL DEFAULT 'beginner',
    estimated_duration_minutes integer NOT NULL DEFAULT 60,
    prerequisites jsonb DEFAULT '[]',
    learning_objectives jsonb DEFAULT '[]',
    content_type text NOT NULL DEFAULT 'interactive',
    content_url text,
    content_data jsonb DEFAULT '{}',
    is_mandatory boolean DEFAULT false,
    is_active boolean DEFAULT true,
    version text NOT NULL DEFAULT '1.0',
    created_by uuid NOT NULL REFERENCES public.users(id),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

-- Training sections within modules
CREATE TABLE IF NOT EXISTS public.training_sections (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    module_id uuid NOT NULL REFERENCES public.training_modules(id) ON DELETE CASCADE,
    section_code text NOT NULL,
    title text NOT NULL,
    description text,
    content_markdown text,
    content_html text,
    section_order integer NOT NULL DEFAULT 1,
    estimated_duration_minutes integer DEFAULT 15,
    is_interactive boolean DEFAULT false,
    interactive_elements jsonb DEFAULT '{}',
    is_required boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    UNIQUE(module_id, section_code)
);

-- Training assessments (quizzes/tests)
CREATE TABLE IF NOT EXISTS public.training_assessments (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    module_id uuid NOT NULL REFERENCES public.training_modules(id) ON DELETE CASCADE,
    section_id uuid REFERENCES public.training_sections(id) ON DELETE CASCADE,
    assessment_code text NOT NULL,
    title text NOT NULL,
    description text,
    assessment_type text NOT NULL DEFAULT 'quiz',
    passing_score integer NOT NULL DEFAULT 80,
    max_attempts integer DEFAULT 3,
    time_limit_minutes integer DEFAULT 30,
    questions jsonb NOT NULL DEFAULT '[]',
    is_required boolean DEFAULT true,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    UNIQUE(module_id, assessment_code)
);

-- User enrollment in training modules
CREATE TABLE IF NOT EXISTS public.training_enrollments (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    module_id uuid NOT NULL REFERENCES public.training_modules(id) ON DELETE CASCADE,
    enrolled_at timestamp with time zone DEFAULT now() NOT NULL,
    enrolled_by uuid REFERENCES public.users(id),
    target_completion_date timestamp with time zone,
    status text NOT NULL DEFAULT 'enrolled',
    completion_percentage numeric(5,2) DEFAULT 0.0,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    last_accessed_at timestamp with time zone,
    total_time_spent_minutes integer DEFAULT 0,
    notes text,
    UNIQUE(user_id, module_id)
);

-- User progress through training sections
CREATE TABLE IF NOT EXISTS public.training_section_progress (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    enrollment_id uuid NOT NULL REFERENCES public.training_enrollments(id) ON DELETE CASCADE,
    section_id uuid NOT NULL REFERENCES public.training_sections(id) ON DELETE CASCADE,
    status text NOT NULL DEFAULT 'not_started',
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    time_spent_minutes integer DEFAULT 0,
    last_position text,
    notes text,
    interactions jsonb DEFAULT '{}',
    UNIQUE(enrollment_id, section_id)
);

-- Assessment attempts and results
CREATE TABLE IF NOT EXISTS public.training_assessment_attempts (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    enrollment_id uuid NOT NULL REFERENCES public.training_enrollments(id) ON DELETE CASCADE,
    assessment_id uuid NOT NULL REFERENCES public.training_assessments(id) ON DELETE CASCADE,
    attempt_number integer NOT NULL DEFAULT 1,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    time_spent_minutes integer,
    answers jsonb DEFAULT '{}',
    score numeric(5,2),
    passed boolean DEFAULT false,
    feedback jsonb DEFAULT '{}',
    status text NOT NULL DEFAULT 'in_progress',
    ip_address inet,
    user_agent text
);

-- User bookmarks for training content
CREATE TABLE IF NOT EXISTS public.training_bookmarks (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    module_id uuid REFERENCES public.training_modules(id) ON DELETE CASCADE,
    section_id uuid REFERENCES public.training_sections(id) ON DELETE CASCADE,
    bookmark_type text NOT NULL DEFAULT 'section',
    title text NOT NULL,
    description text,
    position_data jsonb DEFAULT '{}',
    tags jsonb DEFAULT '[]',
    is_private boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

-- Training certificates
CREATE TABLE IF NOT EXISTS public.training_certificates (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    module_id uuid NOT NULL REFERENCES public.training_modules(id) ON DELETE CASCADE,
    enrollment_id uuid NOT NULL REFERENCES public.training_enrollments(id) ON DELETE CASCADE,
    certificate_number text NOT NULL UNIQUE,
    certificate_type text NOT NULL DEFAULT 'completion',
    issued_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone,
    final_score numeric(5,2),
    certificate_data jsonb DEFAULT '{}',
    verification_code text NOT NULL UNIQUE,
    is_valid boolean DEFAULT true,
    revoked_at timestamp with time zone,
    revoked_by uuid REFERENCES public.users(id),
    revocation_reason text
);

-- User achievements and badges
CREATE TABLE IF NOT EXISTS public.training_achievements (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    achievement_type text NOT NULL,
    achievement_name text NOT NULL,
    description text,
    icon_url text,
    earned_at timestamp with time zone DEFAULT now() NOT NULL,
    related_module_id uuid REFERENCES public.training_modules(id),
    metadata jsonb DEFAULT '{}'
);

-- Discussion forums for training modules
CREATE TABLE IF NOT EXISTS public.training_discussions (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    module_id uuid NOT NULL REFERENCES public.training_modules(id) ON DELETE CASCADE,
    section_id uuid REFERENCES public.training_sections(id) ON DELETE CASCADE,
    parent_id uuid REFERENCES public.training_discussions(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    title text,
    content text NOT NULL,
    discussion_type text NOT NULL DEFAULT 'question',
    is_pinned boolean DEFAULT false,
    is_resolved boolean DEFAULT false,
    upvotes integer DEFAULT 0,
    downvotes integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

-- Discussion votes
CREATE TABLE IF NOT EXISTS public.training_discussion_votes (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    discussion_id uuid NOT NULL REFERENCES public.training_discussions(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    vote_type text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    UNIQUE(discussion_id, user_id)
);

-- Training analytics events
CREATE TABLE IF NOT EXISTS public.training_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    session_id text NOT NULL,
    event_type text NOT NULL,
    event_data jsonb DEFAULT '{}',
    module_id uuid REFERENCES public.training_modules(id),
    section_id uuid REFERENCES public.training_sections(id),
    timestamp timestamp with time zone DEFAULT now() NOT NULL,
    ip_address inet,
    user_agent text
);

-- Training completion reports
CREATE TABLE IF NOT EXISTS public.training_reports (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    report_type text NOT NULL,
    report_name text NOT NULL,
    parameters jsonb DEFAULT '{}',
    generated_by uuid NOT NULL REFERENCES public.users(id),
    generated_at timestamp with time zone DEFAULT now() NOT NULL,
    report_data jsonb DEFAULT '{}',
    file_path text,
    expires_at timestamp with time zone
);

-- Record migration completion
INSERT INTO migration_history (migration_name, description, rollback_sql) VALUES (
    '001_training_portal_migration',
    'Deploy training portal tables and initial data',
    'DROP TABLE IF EXISTS public.training_reports CASCADE; DROP TABLE IF EXISTS public.training_analytics CASCADE; DROP TABLE IF EXISTS public.training_discussion_votes CASCADE; DROP TABLE IF EXISTS public.training_discussions CASCADE; DROP TABLE IF EXISTS public.training_achievements CASCADE; DROP TABLE IF EXISTS public.training_certificates CASCADE; DROP TABLE IF EXISTS public.training_bookmarks CASCADE; DROP TABLE IF EXISTS public.training_assessment_attempts CASCADE; DROP TABLE IF EXISTS public.training_section_progress CASCADE; DROP TABLE IF EXISTS public.training_enrollments CASCADE; DROP TABLE IF EXISTS public.training_assessments CASCADE; DROP TABLE IF EXISTS public.training_sections CASCADE; DROP TABLE IF EXISTS public.training_modules CASCADE;'
);

COMMIT;
