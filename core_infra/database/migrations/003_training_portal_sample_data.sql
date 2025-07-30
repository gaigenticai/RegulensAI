-- ============================================================================
-- TRAINING PORTAL SAMPLE DATA
-- Version: 003
-- Description: Insert sample training content for testing and demonstration
-- ============================================================================

-- Check if migration already applied
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM migration_history WHERE migration_name = '003_training_portal_sample_data') THEN
        RAISE NOTICE 'Migration 003_training_portal_sample_data already applied, skipping...';
        RETURN;
    END IF;
END
$$;

-- ============================================================================
-- SAMPLE TRAINING MODULES
-- ============================================================================

-- Get first tenant and user for sample data
DO $$
DECLARE
    sample_tenant_id uuid;
    sample_user_id uuid;
    module1_id uuid;
    module2_id uuid;
    module3_id uuid;
    section1_id uuid;
    section2_id uuid;
    assessment1_id uuid;
BEGIN
    -- Get first tenant
    SELECT id INTO sample_tenant_id FROM public.tenants LIMIT 1;
    
    -- Get first user
    SELECT id INTO sample_user_id FROM public.users LIMIT 1;
    
    -- If no tenant or user exists, create sample ones
    IF sample_tenant_id IS NULL THEN
        INSERT INTO public.tenants (id, name, domain, industry, country_code, regulatory_jurisdictions)
        VALUES (gen_random_uuid(), 'Sample Financial Corp', 'sample-financial.com', 'financial_services', 'US', '["SEC", "FINRA"]')
        RETURNING id INTO sample_tenant_id;
    END IF;
    
    IF sample_user_id IS NULL THEN
        INSERT INTO public.users (id, tenant_id, email, full_name, role, department, is_active)
        VALUES (gen_random_uuid(), sample_tenant_id, 'admin@sample-financial.com', 'Training Administrator', 'admin', 'Compliance', true)
        RETURNING id INTO sample_user_id;
    END IF;

    -- Insert sample training modules
    INSERT INTO public.training_modules (
        id, tenant_id, module_code, title, description, category, difficulty_level,
        estimated_duration_minutes, prerequisites, learning_objectives, content_type,
        content_data, is_mandatory, is_active, created_by
    ) VALUES 
    (
        gen_random_uuid(), sample_tenant_id, 'REG-INTRO-001', 
        'Introduction to RegulensAI Platform',
        'Comprehensive introduction to the RegulensAI compliance platform, covering core features, navigation, and basic operations.',
        'general', 'beginner', 45,
        '[]'::jsonb,
        '["Understand RegulensAI platform overview", "Navigate the main dashboard", "Access key features", "Understand user roles and permissions"]'::jsonb,
        'interactive',
        '{"sections": 4, "has_video": true, "interactive_demos": 3}'::jsonb,
        true, true, sample_user_id
    ),
    (
        gen_random_uuid(), sample_tenant_id, 'NOTIF-MGT-001',
        'Notification Management Fundamentals',
        'Learn how to effectively manage notifications, alerts, and communication workflows within the RegulensAI platform.',
        'notification_management', 'beginner', 60,
        '["REG-INTRO-001"]'::jsonb,
        '["Configure notification preferences", "Manage alert workflows", "Set up escalation procedures", "Monitor notification effectiveness"]'::jsonb,
        'interactive',
        '{"sections": 5, "has_assessment": true, "practical_exercises": 2}'::jsonb,
        true, true, sample_user_id
    ),
    (
        gen_random_uuid(), sample_tenant_id, 'EXT-DATA-001',
        'External Data Integration',
        'Advanced training on integrating external data sources, APIs, and third-party services with RegulensAI.',
        'external_data', 'intermediate', 90,
        '["REG-INTRO-001", "NOTIF-MGT-001"]'::jsonb,
        '["Connect external data sources", "Configure API integrations", "Validate data quality", "Monitor data flows", "Troubleshoot integration issues"]'::jsonb,
        'hands_on',
        '{"sections": 6, "has_assessment": true, "lab_exercises": 4, "api_examples": 8}'::jsonb,
        false, true, sample_user_id
    ),
    (
        gen_random_uuid(), sample_tenant_id, 'COMPLIANCE-001',
        'Regulatory Compliance Essentials',
        'Essential knowledge for regulatory compliance, covering key regulations, reporting requirements, and best practices.',
        'compliance', 'intermediate', 120,
        '["REG-INTRO-001"]'::jsonb,
        '["Understand key regulations", "Implement compliance workflows", "Generate compliance reports", "Manage audit trails", "Handle regulatory inquiries"]'::jsonb,
        'mixed',
        '{"sections": 8, "has_assessment": true, "case_studies": 3, "templates": 5}'::jsonb,
        true, true, sample_user_id
    ),
    (
        gen_random_uuid(), sample_tenant_id, 'SECURITY-001',
        'Platform Security and Best Practices',
        'Comprehensive security training covering authentication, authorization, data protection, and security best practices.',
        'security', 'advanced', 75,
        '["REG-INTRO-001", "COMPLIANCE-001"]'::jsonb,
        '["Implement security controls", "Manage user access", "Protect sensitive data", "Monitor security events", "Respond to security incidents"]'::jsonb,
        'interactive',
        '{"sections": 6, "has_assessment": true, "security_scenarios": 4}'::jsonb,
        true, true, sample_user_id
    );

    -- Get module IDs for creating sections and assessments
    SELECT id INTO module1_id FROM public.training_modules WHERE module_code = 'REG-INTRO-001';
    SELECT id INTO module2_id FROM public.training_modules WHERE module_code = 'NOTIF-MGT-001';
    SELECT id INTO module3_id FROM public.training_modules WHERE module_code = 'EXT-DATA-001';

    -- Insert sample training sections
    INSERT INTO public.training_sections (
        id, module_id, section_code, title, description, content_markdown,
        section_order, estimated_duration_minutes, is_interactive, interactive_elements
    ) VALUES 
    (
        gen_random_uuid(), module1_id, 'INTRO-001', 
        'Platform Overview',
        'Introduction to RegulensAI platform architecture and core concepts.',
        '# Platform Overview\n\nWelcome to RegulensAI, the comprehensive compliance platform...\n\n## Key Features\n- Real-time monitoring\n- Automated reporting\n- Risk assessment\n- Compliance tracking',
        1, 15, true,
        '{"interactive_tour": true, "knowledge_check": 3}'::jsonb
    ),
    (
        gen_random_uuid(), module1_id, 'INTRO-002',
        'Dashboard Navigation',
        'Learn to navigate the main dashboard and access key features.',
        '# Dashboard Navigation\n\n## Main Dashboard Components\n\n### Navigation Menu\nThe left sidebar provides access to all major platform features...\n\n### Quick Actions\nThe top toolbar contains frequently used actions...',
        2, 10, true,
        '{"guided_tour": true, "practice_exercises": 2}'::jsonb
    ),
    (
        gen_random_uuid(), module2_id, 'NOTIF-001',
        'Notification Types and Channels',
        'Understanding different notification types and delivery channels.',
        '# Notification Types and Channels\n\n## Notification Categories\n\n### Alert Notifications\n- System alerts\n- Compliance violations\n- Risk threshold breaches\n\n### Informational Notifications\n- Status updates\n- Report completions\n- System maintenance',
        1, 20, false,
        '{}'::jsonb
    );

    -- Get section IDs for assessments
    SELECT id INTO section1_id FROM public.training_sections WHERE section_code = 'INTRO-001';
    SELECT id INTO section2_id FROM public.training_sections WHERE section_code = 'NOTIF-001';

    -- Insert sample assessments
    INSERT INTO public.training_assessments (
        id, module_id, section_id, assessment_code, title, description,
        assessment_type, passing_score, max_attempts, time_limit_minutes, questions
    ) VALUES 
    (
        gen_random_uuid(), module1_id, section1_id, 'INTRO-QUIZ-001',
        'Platform Overview Quiz',
        'Test your understanding of RegulensAI platform basics.',
        'quiz', 80, 3, 15,
        '[
            {
                "id": 1,
                "type": "multiple_choice",
                "question": "What is the primary purpose of RegulensAI?",
                "options": [
                    "Financial trading",
                    "Compliance management",
                    "Customer relationship management",
                    "Inventory management"
                ],
                "correct_answer": 1,
                "points": 25
            },
            {
                "id": 2,
                "type": "multiple_choice",
                "question": "Which feature provides real-time monitoring capabilities?",
                "options": [
                    "Dashboard alerts",
                    "Static reports",
                    "Email notifications",
                    "File uploads"
                ],
                "correct_answer": 0,
                "points": 25
            },
            {
                "id": 3,
                "type": "true_false",
                "question": "RegulensAI supports automated compliance reporting.",
                "correct_answer": true,
                "points": 25
            },
            {
                "id": 4,
                "type": "multiple_choice",
                "question": "What type of assessment capabilities does RegulensAI provide?",
                "options": [
                    "Risk assessment only",
                    "Compliance assessment only",
                    "Both risk and compliance assessment",
                    "No assessment capabilities"
                ],
                "correct_answer": 2,
                "points": 25
            }
        ]'::jsonb
    ),
    (
        gen_random_uuid(), module2_id, NULL, 'NOTIF-PRACTICAL-001',
        'Notification Configuration Exercise',
        'Hands-on exercise to configure notification workflows.',
        'practical', 75, 2, 30,
        '[
            {
                "id": 1,
                "type": "practical",
                "task": "Configure an alert notification for compliance violations",
                "instructions": "Set up a notification workflow that triggers when a compliance violation is detected. Include email and dashboard notifications.",
                "evaluation_criteria": [
                    "Correct trigger configuration",
                    "Appropriate notification channels selected",
                    "Proper escalation rules defined"
                ],
                "points": 50
            },
            {
                "id": 2,
                "type": "practical",
                "task": "Create a custom notification template",
                "instructions": "Design a notification template for risk threshold breaches that includes relevant context and action items.",
                "evaluation_criteria": [
                    "Template includes required fields",
                    "Clear and actionable content",
                    "Appropriate formatting"
                ],
                "points": 50
            }
        ]'::jsonb
    );

END $$;

-- Record migration completion
INSERT INTO migration_history (migration_name, description, rollback_sql) VALUES (
    '003_training_portal_sample_data',
    'Insert sample training content for testing and demonstration',
    'DELETE FROM public.training_assessments WHERE assessment_code LIKE ''%001''; DELETE FROM public.training_sections WHERE section_code LIKE ''%001'' OR section_code LIKE ''%002''; DELETE FROM public.training_modules WHERE module_code LIKE ''REG-%'' OR module_code LIKE ''NOTIF-%'' OR module_code LIKE ''EXT-%'' OR module_code LIKE ''COMPLIANCE-%'' OR module_code LIKE ''SECURITY-%'';'
);

COMMIT;
