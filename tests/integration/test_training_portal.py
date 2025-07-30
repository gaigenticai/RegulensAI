"""
Integration tests for Training Portal functionality.
Tests end-to-end workflows including enrollment, progress tracking, assessments, and certificates.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from core_infra.database.models import (
    db, User, Tenant, TrainingModule, TrainingSection, TrainingAssessment,
    TrainingEnrollment, TrainingSectionProgress, TrainingAssessmentAttempt,
    TrainingBookmark, TrainingCertificate, TrainingDiscussion, TrainingAnalytics
)
from core_infra.services.training_service import TrainingService
from core_infra.services.certificate_service import CertificateService
from core_infra.services.analytics_service import AnalyticsService


class TestTrainingPortalIntegration:
    """Integration tests for training portal workflows."""
    
    @pytest.fixture
    def setup_training_data(self, db_session, test_tenant, test_user):
        """Set up test training modules and content."""
        # Create training module
        module = TrainingModule(
            tenant_id=test_tenant.id,
            module_code='test_module_001',
            title='Test Training Module',
            description='A comprehensive test training module',
            category='notification_management',
            difficulty_level='intermediate',
            estimated_duration_minutes=120,
            learning_objectives=['Objective 1', 'Objective 2'],
            prerequisites=['basic_training'],
            content_type='interactive',
            is_mandatory=True,
            is_active=True,
            version='1.0',
            created_by=test_user.id
        )
        db_session.add(module)
        db_session.flush()
        
        # Create training sections
        sections = []
        for i in range(3):
            section = TrainingSection(
                module_id=module.id,
                section_code=f'section_{i+1}',
                title=f'Section {i+1}',
                description=f'Description for section {i+1}',
                content_markdown=f'# Section {i+1}\n\nContent for section {i+1}',
                content_html=f'<h1>Section {i+1}</h1><p>Content for section {i+1}</p>',
                section_order=i+1,
                estimated_duration_minutes=30,
                is_interactive=True,
                interactive_elements={
                    'exercises': [
                        {
                            'id': f'exercise_{i+1}',
                            'type': 'code',
                            'title': f'Exercise {i+1}',
                            'description': 'Practice exercise',
                            'language': 'python',
                            'code': 'print("Hello World")'
                        }
                    ],
                    'quiz': {
                        'questions': [
                            {
                                'id': f'q_{i+1}',
                                'type': 'multiple_choice',
                                'question': f'Question {i+1}?',
                                'options': [
                                    {'id': 'a', 'text': 'Option A', 'correct': True},
                                    {'id': 'b', 'text': 'Option B', 'correct': False}
                                ]
                            }
                        ]
                    }
                },
                is_required=True
            )
            sections.append(section)
            db_session.add(section)
        
        db_session.flush()
        
        # Create assessment
        assessment = TrainingAssessment(
            module_id=module.id,
            assessment_code='final_assessment',
            title='Final Assessment',
            description='Comprehensive final assessment',
            assessment_type='quiz',
            passing_score=80,
            max_attempts=3,
            time_limit_minutes=30,
            questions=[
                {
                    'id': 'final_q1',
                    'type': 'multiple_choice',
                    'question': 'What is the main purpose of this module?',
                    'options': [
                        {'id': 'a', 'text': 'Learning', 'correct': True},
                        {'id': 'b', 'text': 'Testing', 'correct': False}
                    ]
                }
            ],
            is_required=True,
            is_active=True
        )
        db_session.add(assessment)
        
        db_session.commit()
        
        return {
            'module': module,
            'sections': sections,
            'assessment': assessment
        }
    
    def test_complete_training_workflow(self, client, auth_headers, setup_training_data, test_user):
        """Test complete training workflow from enrollment to certificate."""
        module = setup_training_data['module']
        sections = setup_training_data['sections']
        assessment = setup_training_data['assessment']
        
        # Step 1: Get available modules
        response = client.get('/api/v1/training/modules', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['modules']) == 1
        assert data['modules'][0]['title'] == 'Test Training Module'
        
        # Step 2: Enroll in module
        enrollment_data = {
            'module_id': str(module.id),
            'target_completion_date': (datetime.utcnow() + timedelta(days=30)).isoformat()
        }
        response = client.post('/api/v1/training/enrollments', 
                             json=enrollment_data, headers=auth_headers)
        assert response.status_code == 201
        enrollment_id = response.get_json()['id']
        
        # Step 3: Get module details with enrollment
        response = client.get(f'/api/v1/training/modules/{module.id}', headers=auth_headers)
        assert response.status_code == 200
        module_data = response.get_json()
        assert module_data['enrollment']['status'] == 'enrolled'
        assert len(module_data['sections']) == 3
        
        # Step 4: Progress through sections
        for i, section in enumerate(sections):
            # Start section
            progress_data = {
                'status': 'in_progress',
                'time_spent_minutes': 5
            }
            response = client.post(
                f'/api/v1/training/enrollments/{enrollment_id}/sections/{section.id}/progress',
                json=progress_data, headers=auth_headers
            )
            assert response.status_code == 200
            
            # Complete section
            progress_data = {
                'status': 'completed',
                'time_spent_minutes': 25,
                'notes': f'Completed section {i+1}'
            }
            response = client.post(
                f'/api/v1/training/enrollments/{enrollment_id}/sections/{section.id}/progress',
                json=progress_data, headers=auth_headers
            )
            assert response.status_code == 200
        
        # Step 5: Check enrollment progress
        response = client.get('/api/v1/training/enrollments', headers=auth_headers)
        assert response.status_code == 200
        enrollments = response.get_json()['enrollments']
        assert len(enrollments) == 1
        assert enrollments[0]['status'] == 'completed'
        assert enrollments[0]['completion_percentage'] == 100.0
        
        # Step 6: Generate certificate
        cert_data = {'enrollment_id': enrollment_id}
        response = client.post('/api/v1/training/certificates/generate',
                             json=cert_data, headers=auth_headers)
        assert response.status_code == 201
        certificate_data = response.get_json()
        assert 'certificate_number' in certificate_data
        assert 'verification_code' in certificate_data
        
        # Step 7: Verify certificate
        verification_code = certificate_data['verification_code']
        response = client.get(f'/api/v1/training/certificates/verify/{verification_code}')
        assert response.status_code == 200
        verification_data = response.get_json()
        assert verification_data['valid'] == True
        assert verification_data['user_name'] == test_user.full_name
        assert verification_data['module_title'] == module.title
    
    def test_assessment_workflow(self, client, auth_headers, setup_training_data, test_user):
        """Test assessment taking and scoring workflow."""
        module = setup_training_data['module']
        assessment = setup_training_data['assessment']
        
        # Enroll in module first
        enrollment_data = {'module_id': str(module.id)}
        response = client.post('/api/v1/training/enrollments', 
                             json=enrollment_data, headers=auth_headers)
        enrollment_id = response.get_json()['id']
        
        # Get module assessments
        response = client.get(f'/api/v1/training/modules/{module.id}/assessments', 
                            headers=auth_headers)
        assert response.status_code == 200
        assessments = response.get_json()['assessments']
        assert len(assessments) == 1
        
        # Start assessment attempt
        attempt_data = {'enrollment_id': enrollment_id}
        response = client.post(f'/api/v1/training/assessments/{assessment.id}/attempts',
                             json=attempt_data, headers=auth_headers)
        assert response.status_code == 201
        attempt_id = response.get_json()['id']
        
        # Submit assessment answers
        answers_data = {
            'answers': {
                'final_q1': 'a'  # Correct answer
            }
        }
        response = client.post(f'/api/v1/training/assessment-attempts/{attempt_id}/submit',
                             json=answers_data, headers=auth_headers)
        assert response.status_code == 200
        
        # Get assessment results
        response = client.get(f'/api/v1/training/assessment-attempts/{attempt_id}/results',
                            headers=auth_headers)
        assert response.status_code == 200
        results = response.get_json()
        assert results['passed'] == True
        assert results['score'] == 100.0
    
    def test_discussion_forum_workflow(self, client, auth_headers, setup_training_data, test_user):
        """Test discussion forum functionality."""
        module = setup_training_data['module']
        
        # Create discussion post
        discussion_data = {
            'module_id': str(module.id),
            'title': 'Test Discussion',
            'content': 'This is a test discussion post',
            'discussion_type': 'question'
        }
        response = client.post('/api/v1/training/discussions',
                             json=discussion_data, headers=auth_headers)
        assert response.status_code == 201
        discussion_id = response.get_json()['id']
        
        # Get module discussions
        response = client.get(f'/api/v1/training/modules/{module.id}/discussions',
                            headers=auth_headers)
        assert response.status_code == 200
        discussions = response.get_json()['discussions']
        assert len(discussions) == 1
        assert discussions[0]['title'] == 'Test Discussion'
        
        # Vote on discussion
        vote_data = {'vote_type': 'upvote'}
        response = client.post(f'/api/v1/training/discussions/{discussion_id}/vote',
                             json=vote_data, headers=auth_headers)
        assert response.status_code == 200
        
        # Check updated vote count
        response = client.get(f'/api/v1/training/modules/{module.id}/discussions',
                            headers=auth_headers)
        discussions = response.get_json()['discussions']
        assert discussions[0]['upvotes'] == 1
    
    def test_bookmark_management(self, client, auth_headers, setup_training_data, test_user):
        """Test bookmark creation and management."""
        module = setup_training_data['module']
        section = setup_training_data['sections'][0]
        
        # Create bookmark
        bookmark_data = {
            'module_id': str(module.id),
            'section_id': str(section.id),
            'title': 'Important Section',
            'description': 'This section contains important information',
            'bookmark_type': 'section',
            'tags': ['important', 'review']
        }
        response = client.post('/api/v1/training/bookmarks',
                             json=bookmark_data, headers=auth_headers)
        assert response.status_code == 201
        bookmark_id = response.get_json()['id']
        
        # Get user bookmarks
        response = client.get('/api/v1/training/bookmarks', headers=auth_headers)
        assert response.status_code == 200
        bookmarks = response.get_json()['bookmarks']
        assert len(bookmarks) == 1
        assert bookmarks[0]['title'] == 'Important Section'
        assert 'important' in bookmarks[0]['tags']
        
        # Delete bookmark
        response = client.delete(f'/api/v1/training/bookmarks/{bookmark_id}',
                               headers=auth_headers)
        assert response.status_code == 200
        
        # Verify bookmark deleted
        response = client.get('/api/v1/training/bookmarks', headers=auth_headers)
        bookmarks = response.get_json()['bookmarks']
        assert len(bookmarks) == 0
    
    def test_analytics_tracking(self, client, auth_headers, setup_training_data, test_user):
        """Test analytics event tracking and reporting."""
        module = setup_training_data['module']
        section = setup_training_data['sections'][0]
        
        # Track analytics events
        events = [
            {
                'event_type': 'page_view',
                'event_data': {'page': 'module_overview'},
                'module_id': str(module.id)
            },
            {
                'event_type': 'section_start',
                'event_data': {'section_title': section.title},
                'module_id': str(module.id),
                'section_id': str(section.id)
            },
            {
                'event_type': 'section_complete',
                'event_data': {'time_spent': 30},
                'module_id': str(module.id),
                'section_id': str(section.id)
            }
        ]
        
        for event in events:
            response = client.post('/api/v1/training/analytics/events',
                                 json=event, headers=auth_headers)
            assert response.status_code == 200
        
        # Get user analytics
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        
        params = {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
        response = client.get('/api/v1/training/analytics/user',
                            params=params, headers=auth_headers)
        assert response.status_code == 200
        analytics = response.get_json()
        
        # Verify analytics data structure
        assert 'total_events' in analytics
        assert 'event_breakdown' in analytics
        assert analytics['total_events'] >= 3
    
    @patch('core_infra.services.certificate_service.CertificateService._generate_pdf_certificate')
    @patch('core_infra.services.certificate_service.CertificateService._send_certificate_notification')
    def test_certificate_generation_service(self, mock_email, mock_pdf, setup_training_data, test_user):
        """Test certificate generation service functionality."""
        module = setup_training_data['module']
        
        # Create completed enrollment
        enrollment = TrainingEnrollment(
            user_id=test_user.id,
            module_id=module.id,
            status='completed',
            completion_percentage=100.0,
            enrolled_at=datetime.utcnow() - timedelta(days=7),
            completed_at=datetime.utcnow()
        )
        db.session.add(enrollment)
        db.session.commit()
        
        # Mock PDF generation
        mock_pdf.return_value = '/tmp/test_certificate.pdf'
        
        # Generate certificate
        certificate_service = CertificateService()
        certificate = certificate_service.generate_certificate(str(enrollment.id))
        
        # Verify certificate creation
        assert certificate is not None
        assert certificate.user_id == test_user.id
        assert certificate.module_id == module.id
        assert certificate.enrollment_id == enrollment.id
        assert certificate.is_valid == True
        assert len(certificate.certificate_number) > 0
        assert len(certificate.verification_code) > 0
        
        # Verify PDF generation was called
        mock_pdf.assert_called_once()
        
        # Verify email notification was called
        mock_email.assert_called_once()
    
    def test_training_service_recommendations(self, setup_training_data, test_user):
        """Test training service recommendation functionality."""
        module = setup_training_data['module']
        
        # Create user enrollment history
        enrollment = TrainingEnrollment(
            user_id=test_user.id,
            module_id=module.id,
            status='completed',
            completion_percentage=100.0
        )
        db.session.add(enrollment)
        db.session.commit()
        
        # Get recommendations
        training_service = TrainingService()
        recommendations = training_service.get_recommended_modules(str(test_user.id))
        
        # Verify recommendations structure
        assert isinstance(recommendations, list)
        # Note: Actual recommendations depend on recommendation engine implementation
    
    def test_search_functionality(self, client, auth_headers, setup_training_data):
        """Test training module search functionality."""
        module = setup_training_data['module']
        
        # Search for modules
        search_params = {
            'q': 'test training',
            'category': 'notification_management',
            'difficulty': 'intermediate'
        }
        response = client.get('/api/v1/training/modules/search',
                            params=search_params, headers=auth_headers)
        assert response.status_code == 200
        
        results = response.get_json()['results']
        assert len(results) >= 1
        
        # Verify search result contains our module
        found_module = next((r for r in results if r['id'] == str(module.id)), None)
        assert found_module is not None
        assert found_module['title'] == module.title
        assert 'search_score' in found_module
    
    def test_error_handling(self, client, auth_headers):
        """Test API error handling for invalid requests."""
        # Test invalid module ID
        response = client.get('/api/v1/training/modules/invalid-id', headers=auth_headers)
        assert response.status_code == 404
        
        # Test enrollment without module_id
        response = client.post('/api/v1/training/enrollments',
                             json={}, headers=auth_headers)
        assert response.status_code == 400
        
        # Test certificate generation for non-existent enrollment
        response = client.post('/api/v1/training/certificates/generate',
                             json={'enrollment_id': 'invalid-id'}, headers=auth_headers)
        assert response.status_code == 404
        
        # Test certificate verification with invalid code
        response = client.get('/api/v1/training/certificates/verify/invalid-code')
        assert response.status_code == 404
    
    def test_permission_checks(self, client, setup_training_data):
        """Test that endpoints require proper authentication."""
        # Test without authentication headers
        response = client.get('/api/v1/training/modules')
        assert response.status_code == 401
        
        response = client.post('/api/v1/training/enrollments', json={})
        assert response.status_code == 401
        
        response = client.get('/api/v1/training/certificates')
        assert response.status_code == 401
    
    def test_data_isolation(self, client, auth_headers, setup_training_data, test_user):
        """Test that users can only access their own training data."""
        # Create another user in different tenant
        other_tenant = Tenant(name='Other Tenant', domain='other.com')
        db.session.add(other_tenant)
        db.session.flush()
        
        other_user = User(
            email='other@other.com',
            full_name='Other User',
            tenant_id=other_tenant.id,
            is_active=True
        )
        db.session.add(other_user)
        db.session.commit()
        
        # Create enrollment for other user
        other_enrollment = TrainingEnrollment(
            user_id=other_user.id,
            module_id=setup_training_data['module'].id,
            status='enrolled'
        )
        db.session.add(other_enrollment)
        db.session.commit()
        
        # Test that current user cannot see other user's enrollments
        response = client.get('/api/v1/training/enrollments', headers=auth_headers)
        assert response.status_code == 200
        enrollments = response.get_json()['enrollments']
        
        # Should not contain other user's enrollment
        other_enrollment_ids = [e['id'] for e in enrollments if e['id'] == str(other_enrollment.id)]
        assert len(other_enrollment_ids) == 0
