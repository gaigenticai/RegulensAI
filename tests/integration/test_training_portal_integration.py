"""
Integration tests for Training Portal
Tests the complete training portal workflow from API to frontend.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import json

from core_infra.main import app
from core_infra.database.models import (
    User, Tenant, TrainingModule, TrainingSection, 
    TrainingEnrollment, TrainingSectionProgress,
    TrainingAssessment, TrainingCertificate
)
from core_infra.database.connection import get_db
from core_infra.api.auth import create_access_token
from tests.fixtures.training_fixtures import (
    create_test_training_module,
    create_test_training_sections,
    create_test_assessment
)


class TestTrainingPortalIntegration:
    """Integration tests for the complete training portal workflow."""
    
    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session, test_user: User, test_tenant: Tenant):
        """Set up test data for each test."""
        self.db = db_session
        self.user = test_user
        self.tenant = test_tenant
        self.client = TestClient(app)
        
        # Create access token for authentication
        self.access_token = create_access_token(
            data={"sub": str(self.user.id), "tenant_id": str(self.tenant.id)}
        )
        self.headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # Create test training module
        self.module = create_test_training_module(
            db_session=self.db,
            tenant_id=self.tenant.id,
            title="Integration Test Module",
            category="compliance",
            difficulty_level="beginner"
        )
        
        # Create test sections
        self.sections = create_test_training_sections(
            db_session=self.db,
            module_id=self.module.id,
            count=3
        )
        
        # Create test assessment
        self.assessment = create_test_assessment(
            db_session=self.db,
            module_id=self.module.id
        )
    
    def test_complete_training_workflow(self):
        """Test the complete training workflow from enrollment to certification."""
        
        # Step 1: Get available training modules
        response = self.client.get("/api/v1/training/modules", headers=self.headers)
        assert response.status_code == 200
        modules_data = response.json()
        assert len(modules_data["modules"]) >= 1
        assert any(module["id"] == str(self.module.id) for module in modules_data["modules"])
        
        # Step 2: Get specific module details
        response = self.client.get(f"/api/v1/training/modules/{self.module.id}", headers=self.headers)
        assert response.status_code == 200
        module_data = response.json()
        assert module_data["title"] == "Integration Test Module"
        assert module_data["category"] == "compliance"
        
        # Step 3: Enroll in the module
        enrollment_data = {
            "module_id": str(self.module.id),
            "target_completion_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "notes": "Integration test enrollment"
        }
        response = self.client.post("/api/v1/training/enrollments", 
                                  json=enrollment_data, headers=self.headers)
        assert response.status_code == 201
        enrollment_response = response.json()
        enrollment_id = enrollment_response["id"]
        
        # Step 4: Get user enrollments
        response = self.client.get("/api/v1/training/enrollments", headers=self.headers)
        assert response.status_code == 200
        enrollments_data = response.json()
        assert len(enrollments_data["enrollments"]) >= 1
        assert any(enr["id"] == enrollment_id for enr in enrollments_data["enrollments"])
        
        # Step 5: Update section progress
        for i, section in enumerate(self.sections):
            progress_data = {
                "status": "completed" if i < 2 else "in_progress",
                "time_spent_minutes": 15 + i * 5,
                "last_position": f"section_{i}_end" if i < 2 else f"section_{i}_middle",
                "notes": f"Completed section {i+1}",
                "interactions": {"clicks": 10 + i, "scrolls": 20 + i}
            }
            
            response = self.client.post(
                f"/api/v1/training/enrollments/{enrollment_id}/sections/{section.id}/progress",
                json=progress_data,
                headers=self.headers
            )
            assert response.status_code == 200
        
        # Step 6: Get enrollment progress
        response = self.client.get(f"/api/v1/training/enrollments/{enrollment_id}/progress", 
                                 headers=self.headers)
        assert response.status_code == 200
        progress_data = response.json()
        assert "sections" in progress_data
        assert len(progress_data["sections"]) == 3
        
        # Step 7: Get module assessments
        response = self.client.get(f"/api/v1/training/modules/{self.module.id}/assessments", 
                                 headers=self.headers)
        assert response.status_code == 200
        assessments_data = response.json()
        assert len(assessments_data) >= 1
        
        # Step 8: Submit assessment
        assessment_submission = {
            "assessment_id": str(self.assessment.id),
            "answers": {
                "question_1": "answer_a",
                "question_2": "answer_b",
                "question_3": "answer_c"
            },
            "time_spent_minutes": 20
        }
        response = self.client.post(f"/api/v1/training/assessments/{self.assessment.id}/submit",
                                  json=assessment_submission, headers=self.headers)
        assert response.status_code == 200
        attempt_data = response.json()
        assert "score" in attempt_data
        
        # Step 9: Complete remaining section to finish module
        final_section = self.sections[-1]
        final_progress = {
            "status": "completed",
            "time_spent_minutes": 25,
            "last_position": "section_end",
            "notes": "Final section completed"
        }
        response = self.client.post(
            f"/api/v1/training/enrollments/{enrollment_id}/sections/{final_section.id}/progress",
            json=final_progress,
            headers=self.headers
        )
        assert response.status_code == 200
        
        # Step 10: Check if certificate is available
        response = self.client.get("/api/v1/training/certificates", headers=self.headers)
        assert response.status_code == 200
        certificates_data = response.json()
        
        # If certificate was auto-generated, verify it exists
        if certificates_data:
            certificate = certificates_data[0]
            assert certificate["module_title"] == "Integration Test Module"
            assert "verification_code" in certificate
            
            # Test certificate verification
            verification_code = certificate["verification_code"]
            response = self.client.get(f"/api/v1/training/certificates/verify/{verification_code}")
            assert response.status_code == 200
            verification_data = response.json()
            assert verification_data["valid"] is True
    
    def test_training_analytics_workflow(self):
        """Test training analytics and tracking functionality."""
        
        # Create enrollment for analytics testing
        enrollment_data = {
            "module_id": str(self.module.id),
            "notes": "Analytics test enrollment"
        }
        response = self.client.post("/api/v1/training/enrollments", 
                                  json=enrollment_data, headers=self.headers)
        assert response.status_code == 201
        enrollment_id = response.json()["id"]
        
        # Track various analytics events
        events = [
            {"event_type": "module_view", "data": {"duration": 30}},
            {"event_type": "section_start", "data": {"section_order": 1}},
            {"event_type": "video_play", "data": {"video_id": "intro_video", "position": 0}},
            {"event_type": "quiz_attempt", "data": {"question_count": 5}},
            {"event_type": "bookmark_create", "data": {"bookmark_type": "important"}}
        ]
        
        for event in events:
            event["module_id"] = str(self.module.id)
            if "section" in event["event_type"]:
                event["section_id"] = str(self.sections[0].id)
            
            response = self.client.post("/api/v1/training/analytics/track",
                                      json=event, headers=self.headers)
            assert response.status_code == 200
            track_response = response.json()
            assert track_response["success"] is True
        
        # Get dashboard analytics
        response = self.client.get("/api/v1/training/analytics/dashboard", headers=self.headers)
        assert response.status_code == 200
        dashboard_data = response.json()
        assert "total_modules" in dashboard_data
        assert "active_enrollments" in dashboard_data
        
        # Get user analytics
        response = self.client.get(f"/api/v1/training/analytics/user/{self.user.id}", 
                                 headers=self.headers)
        assert response.status_code == 200
        user_analytics = response.json()
        assert "learning_time" in user_analytics
        assert "modules_completed" in user_analytics
    
    def test_search_and_recommendations(self):
        """Test search functionality and recommendations."""
        
        # Test module search
        search_request = {
            "query": "compliance",
            "category": "compliance",
            "limit": 10
        }
        response = self.client.post("/api/v1/training/search", 
                                  json=search_request, headers=self.headers)
        assert response.status_code == 200
        search_results = response.json()
        assert "results" in search_results
        assert len(search_results["results"]) >= 1
        
        # Test recommendations
        response = self.client.get("/api/v1/training/recommendations?limit=5", 
                                 headers=self.headers)
        assert response.status_code == 200
        recommendations_data = response.json()
        assert "recommendations" in recommendations_data
        assert "total" in recommendations_data
    
    def test_error_handling_and_permissions(self):
        """Test error handling and permission checks."""
        
        # Test accessing non-existent module
        response = self.client.get("/api/v1/training/modules/non-existent-id", 
                                 headers=self.headers)
        assert response.status_code == 404
        
        # Test enrolling in non-existent module
        invalid_enrollment = {"module_id": "non-existent-id"}
        response = self.client.post("/api/v1/training/enrollments", 
                                  json=invalid_enrollment, headers=self.headers)
        assert response.status_code == 404
        
        # Test accessing without authentication
        response = self.client.get("/api/v1/training/modules")
        assert response.status_code == 401
        
        # Test invalid assessment submission
        invalid_submission = {
            "assessment_id": "non-existent-id",
            "answers": {}
        }
        response = self.client.post("/api/v1/training/assessments/non-existent-id/submit",
                                  json=invalid_submission, headers=self.headers)
        assert response.status_code == 404
    
    def test_health_check(self):
        """Test training portal health check endpoint."""
        response = self.client.get("/api/v1/training/health")
        assert response.status_code == 200
        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert "services" in health_data
        assert "timestamp" in health_data
