"""
Training Service
Handles business logic for training portal functionality.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, func, desc
from sqlalchemy.orm import joinedload

from core_infra.database.models import (
    db, User, Tenant,
    TrainingModule, TrainingSection, TrainingAssessment,
    TrainingEnrollment, TrainingSectionProgress, TrainingAssessmentAttempt,
    TrainingBookmark, TrainingCertificate, TrainingAchievement,
    TrainingDiscussion, TrainingAnalytics
)
from core_infra.utils.search import SearchEngine
from core_infra.utils.recommendations import RecommendationEngine
from core_infra.utils.email import EmailService
from core_infra.utils.storage import FileStorage
from core_infra.exceptions import ValidationException, BusinessLogicException
import structlog

logger = structlog.get_logger(__name__)


class TrainingService:
    """Service class for training portal operations."""
    
    def __init__(self):
        self.search_engine = SearchEngine()
        self.recommendation_engine = RecommendationEngine()
        self.email_service = EmailService()
        self.file_storage = FileStorage()
    
    def search_modules(
        self, 
        tenant_id: str, 
        query: str, 
        filters: Dict[str, Any] = None,
        user_id: str = None
    ) -> List[Dict[str, Any]]:
        """
        Advanced search for training modules with semantic search and filtering.
        """
        try:
            filters = filters or {}
            
            # Build base query
            base_query = TrainingModule.query.filter(
                TrainingModule.tenant_id == tenant_id,
                TrainingModule.is_active == True
            )
            
            # Apply filters
            if filters.get('category'):
                base_query = base_query.filter(TrainingModule.category == filters['category'])
            
            if filters.get('difficulty'):
                base_query = base_query.filter(TrainingModule.difficulty_level == filters['difficulty'])
            
            if filters.get('content_type'):
                base_query = base_query.filter(TrainingModule.content_type == filters['content_type'])
            
            # Perform semantic search
            search_results = self.search_engine.search_training_content(
                query=query,
                base_query=base_query,
                limit=50
            )
            
            # Get user enrollments for relevance scoring
            user_enrollments = {}
            if user_id:
                enrollments = TrainingEnrollment.query.filter(
                    TrainingEnrollment.user_id == user_id
                ).all()
                user_enrollments = {e.module_id: e for e in enrollments}
            
            # Format results with relevance scoring
            results = []
            for module, score in search_results:
                enrollment = user_enrollments.get(module.id)
                
                result = {
                    'id': str(module.id),
                    'module_code': module.module_code,
                    'title': module.title,
                    'description': module.description,
                    'category': module.category,
                    'difficulty_level': module.difficulty_level,
                    'estimated_duration_minutes': module.estimated_duration_minutes,
                    'content_type': module.content_type,
                    'is_mandatory': module.is_mandatory,
                    'search_score': score,
                    'enrollment_status': enrollment.status if enrollment else None,
                    'completion_percentage': float(enrollment.completion_percentage or 0) if enrollment else 0
                }
                results.append(result)
            
            # Sort by relevance score
            results.sort(key=lambda x: x['search_score'], reverse=True)
            
            return results
            
        except Exception as e:
            logger.error("Failed to search training modules", error=str(e))
            raise
    
    def get_recommended_modules(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get personalized module recommendations for a user.
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return []
            
            # Get user's training history
            enrollments = TrainingEnrollment.query.filter(
                TrainingEnrollment.user_id == user_id
            ).options(joinedload(TrainingEnrollment.module)).all()
            
            # Use recommendation engine
            recommendations = self.recommendation_engine.get_training_recommendations(
                user_id=user_id,
                tenant_id=user.tenant_id,
                user_history=enrollments,
                limit=limit
            )
            
            return recommendations
            
        except Exception as e:
            logger.error("Failed to get recommended modules", user_id=user_id, error=str(e))
            return []
    
    def update_enrollment_progress(self, enrollment_id: str) -> None:
        """
        Update overall enrollment progress based on section progress.
        """
        try:
            enrollment = TrainingEnrollment.query.get(enrollment_id)
            if not enrollment:
                return
            
            # Get all sections for the module
            sections = TrainingSection.query.filter(
                TrainingSection.module_id == enrollment.module_id,
                TrainingSection.is_required == True
            ).all()
            
            if not sections:
                return
            
            # Get section progress
            section_progress = TrainingSectionProgress.query.filter(
                TrainingSectionProgress.enrollment_id == enrollment_id
            ).all()
            
            progress_map = {sp.section_id: sp for sp in section_progress}
            
            # Calculate completion percentage
            completed_sections = 0
            total_time_spent = 0
            
            for section in sections:
                progress = progress_map.get(section.id)
                if progress:
                    if progress.status == 'completed':
                        completed_sections += 1
                    total_time_spent += progress.time_spent_minutes or 0
            
            completion_percentage = (completed_sections / len(sections)) * 100 if sections else 0
            
            # Update enrollment
            enrollment.completion_percentage = completion_percentage
            enrollment.total_time_spent_minutes = total_time_spent
            
            # Update status based on completion
            if completion_percentage == 100:
                enrollment.status = 'completed'
                if not enrollment.completed_at:
                    enrollment.completed_at = datetime.utcnow()
            elif completion_percentage > 0:
                enrollment.status = 'in_progress'
                if not enrollment.started_at:
                    enrollment.started_at = datetime.utcnow()
            
            db.session.commit()
            
            # Check for achievements
            self._check_achievements(enrollment)
            
        except Exception as e:
            logger.error("Failed to update enrollment progress", enrollment_id=enrollment_id, error=str(e))
            db.session.rollback()
            raise
    
    def _check_achievements(self, enrollment: TrainingEnrollment) -> None:
        """
        Check and award achievements based on enrollment progress.
        """
        try:
            user_id = enrollment.user_id
            
            # Check for completion achievement
            if enrollment.status == 'completed':
                # First completion achievement
                first_completion = TrainingAchievement.query.filter(
                    TrainingAchievement.user_id == user_id,
                    TrainingAchievement.achievement_type == 'first_completion'
                ).first()
                
                if not first_completion:
                    achievement = TrainingAchievement(
                        user_id=user_id,
                        achievement_type='first_completion',
                        achievement_name='First Steps',
                        description='Completed your first training module',
                        related_module_id=enrollment.module_id
                    )
                    db.session.add(achievement)
                
                # Perfect score achievement
                if enrollment.completion_percentage == 100:
                    # Check if user got perfect scores on assessments
                    perfect_score = self._check_perfect_assessment_scores(enrollment.id)
                    if perfect_score:
                        existing_perfect = TrainingAchievement.query.filter(
                            TrainingAchievement.user_id == user_id,
                            TrainingAchievement.achievement_type == 'perfect_score',
                            TrainingAchievement.related_module_id == enrollment.module_id
                        ).first()
                        
                        if not existing_perfect:
                            achievement = TrainingAchievement(
                                user_id=user_id,
                                achievement_type='perfect_score',
                                achievement_name='Perfect Score',
                                description='Achieved perfect scores on all assessments',
                                related_module_id=enrollment.module_id
                            )
                            db.session.add(achievement)
                
                # Speed learner achievement (completed in less than estimated time)
                if (enrollment.total_time_spent_minutes and 
                    enrollment.module.estimated_duration_minutes and
                    enrollment.total_time_spent_minutes < enrollment.module.estimated_duration_minutes * 0.8):
                    
                    existing_speed = TrainingAchievement.query.filter(
                        TrainingAchievement.user_id == user_id,
                        TrainingAchievement.achievement_type == 'speed_learner',
                        TrainingAchievement.related_module_id == enrollment.module_id
                    ).first()
                    
                    if not existing_speed:
                        achievement = TrainingAchievement(
                            user_id=user_id,
                            achievement_type='speed_learner',
                            achievement_name='Speed Learner',
                            description='Completed training faster than estimated time',
                            related_module_id=enrollment.module_id
                        )
                        db.session.add(achievement)
            
            # Check for streak achievements
            self._check_learning_streak(user_id)
            
            db.session.commit()
            
        except Exception as e:
            logger.error("Failed to check achievements", enrollment_id=enrollment.id, error=str(e))
    
    def _check_perfect_assessment_scores(self, enrollment_id: str) -> bool:
        """
        Check if user achieved perfect scores on all assessments for an enrollment.
        """
        try:
            # Get all assessment attempts for this enrollment
            attempts = TrainingAssessmentAttempt.query.filter(
                TrainingAssessmentAttempt.enrollment_id == enrollment_id,
                TrainingAssessmentAttempt.status == 'completed'
            ).all()
            
            if not attempts:
                return False
            
            # Check if all attempts have perfect scores
            for attempt in attempts:
                if not attempt.score or attempt.score < 100:
                    return False
            
            return True
            
        except Exception as e:
            logger.error("Failed to check perfect assessment scores", enrollment_id=enrollment_id, error=str(e))
            return False
    
    def _check_learning_streak(self, user_id: str) -> None:
        """
        Check and update learning streak achievements.
        """
        try:
            # Get recent training activity (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            recent_activity = TrainingAnalytics.query.filter(
                TrainingAnalytics.user_id == user_id,
                TrainingAnalytics.timestamp >= thirty_days_ago,
                TrainingAnalytics.event_type.in_(['section_complete', 'assessment_complete'])
            ).order_by(TrainingAnalytics.timestamp.desc()).all()
            
            if not recent_activity:
                return
            
            # Calculate consecutive days with activity
            activity_dates = set()
            for activity in recent_activity:
                activity_dates.add(activity.timestamp.date())
            
            # Find longest streak
            sorted_dates = sorted(activity_dates, reverse=True)
            current_streak = 1
            max_streak = 1
            
            for i in range(1, len(sorted_dates)):
                if (sorted_dates[i-1] - sorted_dates[i]).days == 1:
                    current_streak += 1
                    max_streak = max(max_streak, current_streak)
                else:
                    current_streak = 1
            
            # Award streak achievements
            streak_milestones = [7, 14, 30]
            for milestone in streak_milestones:
                if max_streak >= milestone:
                    existing_streak = TrainingAchievement.query.filter(
                        TrainingAchievement.user_id == user_id,
                        TrainingAchievement.achievement_type == f'learning_streak_{milestone}'
                    ).first()
                    
                    if not existing_streak:
                        achievement = TrainingAchievement(
                            user_id=user_id,
                            achievement_type=f'learning_streak_{milestone}',
                            achievement_name=f'{milestone}-Day Streak',
                            description=f'Maintained learning activity for {milestone} consecutive days',
                            metadata={'streak_days': max_streak}
                        )
                        db.session.add(achievement)
            
        except Exception as e:
            logger.error("Failed to check learning streak", user_id=user_id, error=str(e))
    
    def get_learning_path(self, user_id: str, target_skills: List[str] = None) -> List[Dict[str, Any]]:
        """
        Generate a personalized learning path for a user.
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return []
            
            # Get user's current progress
            enrollments = TrainingEnrollment.query.filter(
                TrainingEnrollment.user_id == user_id
            ).options(joinedload(TrainingEnrollment.module)).all()
            
            completed_modules = [e.module for e in enrollments if e.status == 'completed']
            in_progress_modules = [e.module for e in enrollments if e.status == 'in_progress']
            
            # Get all available modules
            available_modules = TrainingModule.query.filter(
                TrainingModule.tenant_id == user.tenant_id,
                TrainingModule.is_active == True
            ).all()
            
            # Filter out already enrolled modules
            enrolled_module_ids = {e.module_id for e in enrollments}
            candidate_modules = [m for m in available_modules if m.id not in enrolled_module_ids]
            
            # Build learning path based on prerequisites and difficulty progression
            learning_path = []
            
            # Add mandatory modules first
            mandatory_modules = [m for m in candidate_modules if m.is_mandatory]
            for module in mandatory_modules:
                if self._check_prerequisites(module, completed_modules):
                    learning_path.append({
                        'module': module,
                        'reason': 'Required training',
                        'priority': 'high'
                    })
            
            # Add recommended modules based on user's progress and interests
            if target_skills:
                skill_modules = [m for m in candidate_modules 
                               if any(skill.lower() in m.category.lower() for skill in target_skills)]
                for module in skill_modules:
                    if self._check_prerequisites(module, completed_modules):
                        learning_path.append({
                            'module': module,
                            'reason': f'Matches target skill: {module.category}',
                            'priority': 'medium'
                        })
            
            # Add progression modules (next difficulty level)
            if completed_modules:
                user_categories = set(m.category for m in completed_modules)
                for category in user_categories:
                    next_level_modules = self._get_next_difficulty_modules(
                        category, completed_modules, candidate_modules
                    )
                    for module in next_level_modules:
                        learning_path.append({
                            'module': module,
                            'reason': f'Next level in {category}',
                            'priority': 'medium'
                        })
            
            # Remove duplicates and sort by priority
            seen_modules = set()
            unique_path = []
            priority_order = {'high': 0, 'medium': 1, 'low': 2}
            
            for item in sorted(learning_path, key=lambda x: priority_order.get(x['priority'], 3)):
                if item['module'].id not in seen_modules:
                    seen_modules.add(item['module'].id)
                    unique_path.append({
                        'id': str(item['module'].id),
                        'title': item['module'].title,
                        'category': item['module'].category,
                        'difficulty_level': item['module'].difficulty_level,
                        'estimated_duration_minutes': item['module'].estimated_duration_minutes,
                        'reason': item['reason'],
                        'priority': item['priority']
                    })
            
            return unique_path[:10]  # Limit to top 10 recommendations
            
        except Exception as e:
            logger.error("Failed to generate learning path", user_id=user_id, error=str(e))
            return []
    
    def _check_prerequisites(self, module: TrainingModule, completed_modules: List[TrainingModule]) -> bool:
        """
        Check if user has completed all prerequisites for a module.
        """
        if not module.prerequisites:
            return True
        
        completed_codes = {m.module_code for m in completed_modules}
        return all(prereq in completed_codes for prereq in module.prerequisites)
    
    def _get_next_difficulty_modules(
        self, 
        category: str, 
        completed_modules: List[TrainingModule], 
        candidate_modules: List[TrainingModule]
    ) -> List[TrainingModule]:
        """
        Get modules of the next difficulty level in a category.
        """
        difficulty_order = ['beginner', 'intermediate', 'advanced', 'expert']
        
        # Find highest completed difficulty in this category
        completed_in_category = [m for m in completed_modules if m.category == category]
        if not completed_in_category:
            target_difficulty = 'beginner'
        else:
            max_difficulty_index = max(
                difficulty_order.index(m.difficulty_level) 
                for m in completed_in_category 
                if m.difficulty_level in difficulty_order
            )
            if max_difficulty_index < len(difficulty_order) - 1:
                target_difficulty = difficulty_order[max_difficulty_index + 1]
            else:
                return []  # Already at highest level
        
        # Find modules at target difficulty
        return [
            m for m in candidate_modules 
            if m.category == category and m.difficulty_level == target_difficulty
        ]
