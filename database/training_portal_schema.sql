-- ============================================================================
-- TRAINING PORTAL DATABASE SCHEMA
-- ============================================================================
-- This schema extends the existing RegulensAI database with training portal
-- functionality including progress tracking, assessments, and certificates.

-- ============================================================================
-- TRAINING MODULES AND CONTENT
-- ============================================================================

-- Training modules (courses/sections)
CREATE TABLE IF NOT EXISTS public.training_modules (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    module_code text NOT NULL UNIQUE,
    title text NOT NULL,
    description text,
    category text NOT NULL, -- 'notification_management', 'external_data', 'operational_procedures', 'api_usage'
    difficulty_level text NOT NULL DEFAULT 'beginner', -- 'beginner', 'intermediate', 'advanced', 'expert'
    estimated_duration_minutes integer NOT NULL DEFAULT 60,
    prerequisites jsonb DEFAULT '[]', -- Array of prerequisite module codes
    learning_objectives jsonb DEFAULT '[]', -- Array of learning objectives
    content_type text NOT NULL DEFAULT 'interactive', -- 'interactive', 'video', 'document', 'hands_on'
    content_url text, -- URL to content or null for embedded content
    content_data jsonb DEFAULT '{}', -- Embedded content data
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
    content_markdown text, -- Markdown content
    content_html text, -- Rendered HTML content
    section_order integer NOT NULL DEFAULT 1,
    estimated_duration_minutes integer DEFAULT 15,
    is_interactive boolean DEFAULT false,
    interactive_elements jsonb DEFAULT '{}', -- Code examples, exercises, etc.
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
    assessment_type text NOT NULL DEFAULT 'quiz', -- 'quiz', 'practical', 'essay', 'hands_on'
    passing_score integer NOT NULL DEFAULT 80, -- Percentage
    max_attempts integer DEFAULT 3,
    time_limit_minutes integer DEFAULT 30,
    questions jsonb NOT NULL DEFAULT '[]', -- Array of question objects
    is_required boolean DEFAULT true,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    UNIQUE(module_id, assessment_code)
);

-- ============================================================================
-- USER PROGRESS AND TRACKING
-- ============================================================================

-- User enrollment in training modules
CREATE TABLE IF NOT EXISTS public.training_enrollments (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    module_id uuid NOT NULL REFERENCES public.training_modules(id) ON DELETE CASCADE,
    enrolled_at timestamp with time zone DEFAULT now() NOT NULL,
    enrolled_by uuid REFERENCES public.users(id), -- Who enrolled the user (admin/manager)
    target_completion_date timestamp with time zone,
    status text NOT NULL DEFAULT 'enrolled', -- 'enrolled', 'in_progress', 'completed', 'failed', 'expired'
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
    status text NOT NULL DEFAULT 'not_started', -- 'not_started', 'in_progress', 'completed', 'skipped'
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    time_spent_minutes integer DEFAULT 0,
    last_position text, -- Last scroll position or bookmark
    notes text,
    interactions jsonb DEFAULT '{}', -- User interactions with interactive elements
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
    answers jsonb DEFAULT '{}', -- User answers
    score numeric(5,2), -- Percentage score
    passed boolean DEFAULT false,
    feedback jsonb DEFAULT '{}', -- Detailed feedback per question
    status text NOT NULL DEFAULT 'in_progress', -- 'in_progress', 'completed', 'abandoned', 'expired'
    ip_address inet,
    user_agent text
);

-- ============================================================================
-- BOOKMARKS AND FAVORITES
-- ============================================================================

-- User bookmarks for training content
CREATE TABLE IF NOT EXISTS public.training_bookmarks (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    module_id uuid REFERENCES public.training_modules(id) ON DELETE CASCADE,
    section_id uuid REFERENCES public.training_sections(id) ON DELETE CASCADE,
    bookmark_type text NOT NULL DEFAULT 'section', -- 'module', 'section', 'position'
    title text NOT NULL,
    description text,
    position_data jsonb DEFAULT '{}', -- Scroll position, page number, etc.
    tags jsonb DEFAULT '[]', -- User-defined tags
    is_private boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

-- ============================================================================
-- CERTIFICATES AND ACHIEVEMENTS
-- ============================================================================

-- Training certificates
CREATE TABLE IF NOT EXISTS public.training_certificates (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    module_id uuid NOT NULL REFERENCES public.training_modules(id) ON DELETE CASCADE,
    enrollment_id uuid NOT NULL REFERENCES public.training_enrollments(id) ON DELETE CASCADE,
    certificate_number text NOT NULL UNIQUE,
    certificate_type text NOT NULL DEFAULT 'completion', -- 'completion', 'proficiency', 'mastery'
    issued_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone,
    final_score numeric(5,2),
    certificate_data jsonb DEFAULT '{}', -- Certificate template data
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
    achievement_type text NOT NULL, -- 'first_completion', 'perfect_score', 'speed_learner', 'helping_hand'
    achievement_name text NOT NULL,
    description text,
    icon_url text,
    earned_at timestamp with time zone DEFAULT now() NOT NULL,
    related_module_id uuid REFERENCES public.training_modules(id),
    metadata jsonb DEFAULT '{}'
);

-- ============================================================================
-- DISCUSSIONS AND COLLABORATION
-- ============================================================================

-- Discussion forums for training modules
CREATE TABLE IF NOT EXISTS public.training_discussions (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    module_id uuid NOT NULL REFERENCES public.training_modules(id) ON DELETE CASCADE,
    section_id uuid REFERENCES public.training_sections(id) ON DELETE CASCADE,
    parent_id uuid REFERENCES public.training_discussions(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    title text,
    content text NOT NULL,
    discussion_type text NOT NULL DEFAULT 'question', -- 'question', 'comment', 'answer', 'tip'
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
    vote_type text NOT NULL, -- 'upvote', 'downvote'
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    UNIQUE(discussion_id, user_id)
);

-- ============================================================================
-- ANALYTICS AND REPORTING
-- ============================================================================

-- Training analytics events
CREATE TABLE IF NOT EXISTS public.training_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    session_id text NOT NULL,
    event_type text NOT NULL, -- 'page_view', 'section_start', 'section_complete', 'assessment_start', 'bookmark_create'
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
    report_type text NOT NULL, -- 'completion_summary', 'progress_report', 'assessment_analysis'
    report_name text NOT NULL,
    parameters jsonb DEFAULT '{}', -- Report parameters (date range, modules, users)
    generated_by uuid NOT NULL REFERENCES public.users(id),
    generated_at timestamp with time zone DEFAULT now() NOT NULL,
    report_data jsonb DEFAULT '{}',
    file_path text, -- Path to generated report file
    expires_at timestamp with time zone
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Training modules indexes
CREATE INDEX IF NOT EXISTS idx_training_modules_tenant ON public.training_modules(tenant_id);
CREATE INDEX IF NOT EXISTS idx_training_modules_category ON public.training_modules(category);
CREATE INDEX IF NOT EXISTS idx_training_modules_active ON public.training_modules(is_active);
CREATE INDEX IF NOT EXISTS idx_training_modules_difficulty ON public.training_modules(difficulty_level);

-- Training sections indexes
CREATE INDEX IF NOT EXISTS idx_training_sections_module ON public.training_sections(module_id);
CREATE INDEX IF NOT EXISTS idx_training_sections_order ON public.training_sections(module_id, section_order);

-- Training assessments indexes
CREATE INDEX IF NOT EXISTS idx_training_assessments_module ON public.training_assessments(module_id);
CREATE INDEX IF NOT EXISTS idx_training_assessments_section ON public.training_assessments(section_id);
CREATE INDEX IF NOT EXISTS idx_training_assessments_active ON public.training_assessments(is_active);

-- Enrollment and progress indexes
CREATE INDEX IF NOT EXISTS idx_training_enrollments_user ON public.training_enrollments(user_id);
CREATE INDEX IF NOT EXISTS idx_training_enrollments_module ON public.training_enrollments(module_id);
CREATE INDEX IF NOT EXISTS idx_training_enrollments_status ON public.training_enrollments(status);
CREATE INDEX IF NOT EXISTS idx_training_enrollments_completion ON public.training_enrollments(completed_at);

CREATE INDEX IF NOT EXISTS idx_training_section_progress_enrollment ON public.training_section_progress(enrollment_id);
CREATE INDEX IF NOT EXISTS idx_training_section_progress_section ON public.training_section_progress(section_id);
CREATE INDEX IF NOT EXISTS idx_training_section_progress_status ON public.training_section_progress(status);

CREATE INDEX IF NOT EXISTS idx_training_assessment_attempts_enrollment ON public.training_assessment_attempts(enrollment_id);
CREATE INDEX IF NOT EXISTS idx_training_assessment_attempts_assessment ON public.training_assessment_attempts(assessment_id);
CREATE INDEX IF NOT EXISTS idx_training_assessment_attempts_completed ON public.training_assessment_attempts(completed_at);

-- Bookmarks indexes
CREATE INDEX IF NOT EXISTS idx_training_bookmarks_user ON public.training_bookmarks(user_id);
CREATE INDEX IF NOT EXISTS idx_training_bookmarks_module ON public.training_bookmarks(module_id);
CREATE INDEX IF NOT EXISTS idx_training_bookmarks_section ON public.training_bookmarks(section_id);

-- Certificates indexes
CREATE INDEX IF NOT EXISTS idx_training_certificates_user ON public.training_certificates(user_id);
CREATE INDEX IF NOT EXISTS idx_training_certificates_module ON public.training_certificates(module_id);
CREATE INDEX IF NOT EXISTS idx_training_certificates_issued ON public.training_certificates(issued_at);
CREATE INDEX IF NOT EXISTS idx_training_certificates_verification ON public.training_certificates(verification_code);

-- Achievements indexes
CREATE INDEX IF NOT EXISTS idx_training_achievements_user ON public.training_achievements(user_id);
CREATE INDEX IF NOT EXISTS idx_training_achievements_type ON public.training_achievements(achievement_type);
CREATE INDEX IF NOT EXISTS idx_training_achievements_earned ON public.training_achievements(earned_at);

-- Discussions indexes
CREATE INDEX IF NOT EXISTS idx_training_discussions_module ON public.training_discussions(module_id);
CREATE INDEX IF NOT EXISTS idx_training_discussions_section ON public.training_discussions(section_id);
CREATE INDEX IF NOT EXISTS idx_training_discussions_parent ON public.training_discussions(parent_id);
CREATE INDEX IF NOT EXISTS idx_training_discussions_user ON public.training_discussions(user_id);
CREATE INDEX IF NOT EXISTS idx_training_discussions_created ON public.training_discussions(created_at);

-- Analytics indexes
CREATE INDEX IF NOT EXISTS idx_training_analytics_user ON public.training_analytics(user_id);
CREATE INDEX IF NOT EXISTS idx_training_analytics_tenant ON public.training_analytics(tenant_id);
CREATE INDEX IF NOT EXISTS idx_training_analytics_timestamp ON public.training_analytics(timestamp);
CREATE INDEX IF NOT EXISTS idx_training_analytics_event_type ON public.training_analytics(event_type);
CREATE INDEX IF NOT EXISTS idx_training_analytics_module ON public.training_analytics(module_id);

-- ============================================================================
-- CONSTRAINTS AND VALIDATION
-- ============================================================================

-- Training modules constraints
ALTER TABLE public.training_modules ADD CONSTRAINT chk_training_module_category 
    CHECK (category IN ('notification_management', 'external_data', 'operational_procedures', 'api_usage', 'compliance', 'security', 'general'));

ALTER TABLE public.training_modules ADD CONSTRAINT chk_training_module_difficulty 
    CHECK (difficulty_level IN ('beginner', 'intermediate', 'advanced', 'expert'));

ALTER TABLE public.training_modules ADD CONSTRAINT chk_training_module_content_type 
    CHECK (content_type IN ('interactive', 'video', 'document', 'hands_on', 'mixed'));

-- Training assessments constraints
ALTER TABLE public.training_assessments ADD CONSTRAINT chk_training_assessment_type 
    CHECK (assessment_type IN ('quiz', 'practical', 'essay', 'hands_on', 'survey'));

ALTER TABLE public.training_assessments ADD CONSTRAINT chk_training_assessment_passing_score 
    CHECK (passing_score >= 0 AND passing_score <= 100);

-- Enrollment constraints
ALTER TABLE public.training_enrollments ADD CONSTRAINT chk_training_enrollment_status 
    CHECK (status IN ('enrolled', 'in_progress', 'completed', 'failed', 'expired', 'withdrawn'));

ALTER TABLE public.training_enrollments ADD CONSTRAINT chk_training_enrollment_completion_percentage 
    CHECK (completion_percentage >= 0.0 AND completion_percentage <= 100.0);

-- Section progress constraints
ALTER TABLE public.training_section_progress ADD CONSTRAINT chk_training_section_progress_status 
    CHECK (status IN ('not_started', 'in_progress', 'completed', 'skipped'));

-- Assessment attempts constraints
ALTER TABLE public.training_assessment_attempts ADD CONSTRAINT chk_training_assessment_attempt_status 
    CHECK (status IN ('in_progress', 'completed', 'abandoned', 'expired'));

ALTER TABLE public.training_assessment_attempts ADD CONSTRAINT chk_training_assessment_attempt_score 
    CHECK (score IS NULL OR (score >= 0.0 AND score <= 100.0));

-- Certificate constraints
ALTER TABLE public.training_certificates ADD CONSTRAINT chk_training_certificate_type 
    CHECK (certificate_type IN ('completion', 'proficiency', 'mastery', 'participation'));

-- Discussion constraints
ALTER TABLE public.training_discussions ADD CONSTRAINT chk_training_discussion_type 
    CHECK (discussion_type IN ('question', 'comment', 'answer', 'tip', 'announcement'));

ALTER TABLE public.training_discussion_votes ADD CONSTRAINT chk_training_discussion_vote_type 
    CHECK (vote_type IN ('upvote', 'downvote'));

-- Analytics constraints
ALTER TABLE public.training_analytics ADD CONSTRAINT chk_training_analytics_event_type 
    CHECK (event_type IN ('page_view', 'section_start', 'section_complete', 'assessment_start', 
                         'assessment_complete', 'bookmark_create', 'bookmark_delete', 'discussion_post', 
                         'search_query', 'download', 'print', 'share'));

-- ============================================================================
-- TRIGGERS FOR AUTOMATIC UPDATES
-- ============================================================================

-- Update timestamps
CREATE TRIGGER update_training_modules_updated_at BEFORE UPDATE ON public.training_modules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_training_sections_updated_at BEFORE UPDATE ON public.training_sections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_training_assessments_updated_at BEFORE UPDATE ON public.training_assessments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_training_discussions_updated_at BEFORE UPDATE ON public.training_discussions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- TABLE COMMENTS
-- ============================================================================

COMMENT ON TABLE public.training_modules IS 'Training modules/courses with content and metadata';
COMMENT ON TABLE public.training_sections IS 'Individual sections within training modules';
COMMENT ON TABLE public.training_assessments IS 'Quizzes and assessments for training modules';
COMMENT ON TABLE public.training_enrollments IS 'User enrollment and progress tracking for training modules';
COMMENT ON TABLE public.training_section_progress IS 'Detailed progress tracking through training sections';
COMMENT ON TABLE public.training_assessment_attempts IS 'Assessment attempts and results with detailed scoring';
COMMENT ON TABLE public.training_bookmarks IS 'User bookmarks and favorites for training content';
COMMENT ON TABLE public.training_certificates IS 'Training completion certificates with verification';
COMMENT ON TABLE public.training_achievements IS 'User achievements and badges for training milestones';
COMMENT ON TABLE public.training_discussions IS 'Discussion forums and Q&A for training modules';
COMMENT ON TABLE public.training_discussion_votes IS 'Voting system for training discussions';
COMMENT ON TABLE public.training_analytics IS 'Analytics events for training portal usage tracking';
COMMENT ON TABLE public.training_reports IS 'Generated training reports and analytics summaries';
