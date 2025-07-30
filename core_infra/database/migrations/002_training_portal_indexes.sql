-- ============================================================================
-- TRAINING PORTAL INDEXES AND CONSTRAINTS
-- Version: 002
-- Description: Add indexes, constraints, and performance optimizations
-- ============================================================================

-- Check if migration already applied
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM migration_history WHERE migration_name = '002_training_portal_indexes') THEN
        RAISE NOTICE 'Migration 002_training_portal_indexes already applied, skipping...';
        RETURN;
    END IF;
END
$$;

-- ============================================================================
-- TRAINING PORTAL INDEXES
-- ============================================================================

-- Training modules indexes
CREATE INDEX IF NOT EXISTS idx_training_modules_tenant ON public.training_modules(tenant_id);
CREATE INDEX IF NOT EXISTS idx_training_modules_category ON public.training_modules(category);
CREATE INDEX IF NOT EXISTS idx_training_modules_active ON public.training_modules(is_active);
CREATE INDEX IF NOT EXISTS idx_training_modules_difficulty ON public.training_modules(difficulty_level);
CREATE INDEX IF NOT EXISTS idx_training_modules_created ON public.training_modules(created_at);
CREATE INDEX IF NOT EXISTS idx_training_modules_code ON public.training_modules(module_code);

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
CREATE INDEX IF NOT EXISTS idx_training_enrollments_enrolled ON public.training_enrollments(enrolled_at);

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
-- TRAINING PORTAL CONSTRAINTS
-- ============================================================================

-- Training modules constraints
ALTER TABLE public.training_modules ADD CONSTRAINT IF NOT EXISTS chk_training_module_category 
    CHECK (category IN ('notification_management', 'external_data', 'operational_procedures', 'api_usage', 'compliance', 'security', 'general'));

ALTER TABLE public.training_modules ADD CONSTRAINT IF NOT EXISTS chk_training_module_difficulty 
    CHECK (difficulty_level IN ('beginner', 'intermediate', 'advanced', 'expert'));

ALTER TABLE public.training_modules ADD CONSTRAINT IF NOT EXISTS chk_training_module_content_type 
    CHECK (content_type IN ('interactive', 'video', 'document', 'hands_on', 'mixed'));

-- Training assessments constraints
ALTER TABLE public.training_assessments ADD CONSTRAINT IF NOT EXISTS chk_training_assessment_type 
    CHECK (assessment_type IN ('quiz', 'practical', 'essay', 'hands_on', 'survey'));

ALTER TABLE public.training_assessments ADD CONSTRAINT IF NOT EXISTS chk_training_assessment_passing_score 
    CHECK (passing_score >= 0 AND passing_score <= 100);

-- Enrollment constraints
ALTER TABLE public.training_enrollments ADD CONSTRAINT IF NOT EXISTS chk_training_enrollment_status 
    CHECK (status IN ('enrolled', 'in_progress', 'completed', 'failed', 'expired', 'withdrawn'));

ALTER TABLE public.training_enrollments ADD CONSTRAINT IF NOT EXISTS chk_training_enrollment_completion_percentage 
    CHECK (completion_percentage >= 0.0 AND completion_percentage <= 100.0);

-- Section progress constraints
ALTER TABLE public.training_section_progress ADD CONSTRAINT IF NOT EXISTS chk_training_section_progress_status 
    CHECK (status IN ('not_started', 'in_progress', 'completed', 'skipped'));

-- Assessment attempts constraints
ALTER TABLE public.training_assessment_attempts ADD CONSTRAINT IF NOT EXISTS chk_training_assessment_attempt_status 
    CHECK (status IN ('in_progress', 'completed', 'abandoned', 'expired'));

ALTER TABLE public.training_assessment_attempts ADD CONSTRAINT IF NOT EXISTS chk_training_assessment_attempt_score 
    CHECK (score IS NULL OR (score >= 0.0 AND score <= 100.0));

-- Certificate constraints
ALTER TABLE public.training_certificates ADD CONSTRAINT IF NOT EXISTS chk_training_certificate_type 
    CHECK (certificate_type IN ('completion', 'proficiency', 'mastery', 'participation'));

-- Discussion constraints
ALTER TABLE public.training_discussions ADD CONSTRAINT IF NOT EXISTS chk_training_discussion_type 
    CHECK (discussion_type IN ('question', 'comment', 'answer', 'tip', 'announcement'));

ALTER TABLE public.training_discussion_votes ADD CONSTRAINT IF NOT EXISTS chk_training_discussion_vote_type 
    CHECK (vote_type IN ('upvote', 'downvote'));

-- Analytics constraints
ALTER TABLE public.training_analytics ADD CONSTRAINT IF NOT EXISTS chk_training_analytics_event_type 
    CHECK (event_type IN ('page_view', 'section_start', 'section_complete', 'assessment_start', 
                         'assessment_complete', 'bookmark_create', 'bookmark_delete', 'discussion_post', 
                         'search_query', 'download', 'print', 'share'));

-- ============================================================================
-- TRAINING PORTAL TRIGGERS
-- ============================================================================

-- Create update timestamp function if not exists
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Update timestamps
CREATE TRIGGER IF NOT EXISTS update_training_modules_updated_at 
    BEFORE UPDATE ON public.training_modules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER IF NOT EXISTS update_training_sections_updated_at 
    BEFORE UPDATE ON public.training_sections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER IF NOT EXISTS update_training_assessments_updated_at 
    BEFORE UPDATE ON public.training_assessments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER IF NOT EXISTS update_training_discussions_updated_at 
    BEFORE UPDATE ON public.training_discussions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- TRAINING PORTAL PERMISSIONS
-- ============================================================================

-- Insert training portal permissions
INSERT INTO public.permissions (name, description, category, resource, action) VALUES
    ('training.modules.read', 'View training modules', 'training', 'training_modules', 'read'),
    ('training.modules.create', 'Create training modules', 'training', 'training_modules', 'create'),
    ('training.modules.update', 'Update training modules', 'training', 'training_modules', 'update'),
    ('training.modules.delete', 'Delete training modules', 'training', 'training_modules', 'delete'),
    ('training.enrollments.read', 'View training enrollments', 'training', 'training_enrollments', 'read'),
    ('training.enrollments.create', 'Create training enrollments', 'training', 'training_enrollments', 'create'),
    ('training.enrollments.update', 'Update training enrollments', 'training', 'training_enrollments', 'update'),
    ('training.enrollments.delete', 'Delete training enrollments', 'training', 'training_enrollments', 'delete'),
    ('training.assessments.read', 'View training assessments', 'training', 'training_assessments', 'read'),
    ('training.assessments.take', 'Take training assessments', 'training', 'training_assessments', 'take'),
    ('training.certificates.read', 'View training certificates', 'training', 'training_certificates', 'read'),
    ('training.certificates.generate', 'Generate training certificates', 'training', 'training_certificates', 'generate'),
    ('training.discussions.read', 'View training discussions', 'training', 'training_discussions', 'read'),
    ('training.discussions.create', 'Create training discussions', 'training', 'training_discussions', 'create'),
    ('training.discussions.moderate', 'Moderate training discussions', 'training', 'training_discussions', 'moderate'),
    ('training.analytics.read', 'View training analytics', 'training', 'training_analytics', 'read'),
    ('training.reports.read', 'View training reports', 'training', 'training_reports', 'read'),
    ('training.reports.generate', 'Generate training reports', 'training', 'training_reports', 'generate')
ON CONFLICT (name) DO NOTHING;

-- Record migration completion
INSERT INTO migration_history (migration_name, description, rollback_sql) VALUES (
    '002_training_portal_indexes',
    'Add indexes, constraints, and performance optimizations for training portal',
    'DROP INDEX IF EXISTS idx_training_modules_tenant; DROP INDEX IF EXISTS idx_training_modules_category; -- Add all other DROP INDEX statements here'
);

COMMIT;
