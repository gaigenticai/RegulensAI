"""
Recommendation Engine
AI-powered recommendation system for training modules and learning paths.
"""

import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from sqlalchemy import func, and_, or_

import structlog

logger = structlog.get_logger(__name__)


class RecommendationEngine:
    """Advanced recommendation engine for personalized learning experiences."""
    
    def __init__(self):
        self.category_weights = {
            'notification_management': 1.0,
            'external_data': 0.9,
            'operational_procedures': 0.8,
            'api_usage': 0.7,
            'compliance': 1.2,
            'security': 1.1,
            'general': 0.6
        }
        
        self.difficulty_progression = {
            'beginner': ['beginner', 'intermediate'],
            'intermediate': ['intermediate', 'advanced'],
            'advanced': ['advanced', 'expert'],
            'expert': ['expert']
        }
    
    def get_training_recommendations(
        self,
        user_id: str,
        tenant_id: str,
        user_history: List[Any],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Generate personalized training recommendations for a user.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            user_history: List of user's training enrollments
            limit: Maximum number of recommendations
            
        Returns:
            List of recommended training modules with scores
        """
        try:
            from core_infra.database.models import TrainingModule, TrainingEnrollment
            
            # Analyze user's learning patterns
            user_profile = self._build_user_profile(user_history)
            
            # Get all available modules
            available_modules = TrainingModule.query.filter(
                TrainingModule.tenant_id == tenant_id,
                TrainingModule.is_active == True
            ).all()
            
            # Filter out already enrolled modules
            enrolled_module_ids = {enrollment.module_id for enrollment in user_history}
            candidate_modules = [
                module for module in available_modules 
                if module.id not in enrolled_module_ids
            ]
            
            # Score each candidate module
            recommendations = []
            for module in candidate_modules:
                score = self._calculate_recommendation_score(module, user_profile, user_history)
                if score > 0.1:  # Minimum threshold
                    recommendations.append({
                        'module': module,
                        'score': score,
                        'reasons': self._get_recommendation_reasons(module, user_profile)
                    })
            
            # Sort by score and return top recommendations
            recommendations.sort(key=lambda x: x['score'], reverse=True)
            
            # Format recommendations
            formatted_recommendations = []
            for rec in recommendations[:limit]:
                module = rec['module']
                formatted_recommendations.append({
                    'id': str(module.id),
                    'module_code': module.module_code,
                    'title': module.title,
                    'description': module.description,
                    'category': module.category,
                    'difficulty_level': module.difficulty_level,
                    'estimated_duration_minutes': module.estimated_duration_minutes,
                    'recommendation_score': rec['score'],
                    'recommendation_reasons': rec['reasons'],
                    'is_mandatory': module.is_mandatory
                })
            
            return formatted_recommendations
            
        except Exception as e:
            logger.error("Recommendation generation failed", user_id=user_id, error=str(e))
            return []
    
    def _build_user_profile(self, user_history: List[Any]) -> Dict[str, Any]:
        """
        Build user learning profile from history.
        
        Args:
            user_history: User's training enrollment history
            
        Returns:
            User profile dictionary
        """
        profile = {
            'preferred_categories': defaultdict(float),
            'difficulty_progression': defaultdict(int),
            'completion_rate': 0.0,
            'average_time_per_module': 0,
            'learning_velocity': 0.0,
            'recent_activity': [],
            'strengths': [],
            'areas_for_improvement': []
        }
        
        if not user_history:
            return profile
        
        # Analyze category preferences
        category_counts = Counter()
        category_scores = defaultdict(list)
        
        completed_modules = 0
        total_time = 0
        total_modules = len(user_history)
        
        for enrollment in user_history:
            module = enrollment.module
            
            # Category analysis
            category_counts[module.category] += 1
            
            # Completion analysis
            if enrollment.status == 'completed':
                completed_modules += 1
                
                # Time analysis
                if enrollment.total_time_spent_minutes:
                    total_time += enrollment.total_time_spent_minutes
                
                # Performance analysis (if available)
                if hasattr(enrollment, 'final_score') and enrollment.final_score:
                    category_scores[module.category].append(enrollment.final_score)
        
        # Calculate metrics
        profile['completion_rate'] = completed_modules / total_modules if total_modules > 0 else 0.0
        profile['average_time_per_module'] = total_time / completed_modules if completed_modules > 0 else 0
        
        # Category preferences (normalized)
        total_categories = sum(category_counts.values())
        for category, count in category_counts.items():
            profile['preferred_categories'][category] = count / total_categories
        
        # Difficulty progression analysis
        for enrollment in user_history:
            if enrollment.status == 'completed':
                profile['difficulty_progression'][enrollment.module.difficulty_level] += 1
        
        # Identify strengths and improvement areas
        for category, scores in category_scores.items():
            if scores:
                avg_score = sum(scores) / len(scores)
                if avg_score >= 85:
                    profile['strengths'].append(category)
                elif avg_score < 70:
                    profile['areas_for_improvement'].append(category)
        
        # Recent activity (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        profile['recent_activity'] = [
            enrollment for enrollment in user_history
            if enrollment.last_accessed_at and enrollment.last_accessed_at >= thirty_days_ago
        ]
        
        # Learning velocity (modules completed per month)
        if user_history:
            first_enrollment = min(user_history, key=lambda x: x.enrolled_at)
            months_active = max(1, (datetime.utcnow() - first_enrollment.enrolled_at).days / 30)
            profile['learning_velocity'] = completed_modules / months_active
        
        return profile
    
    def _calculate_recommendation_score(
        self,
        module: Any,
        user_profile: Dict[str, Any],
        user_history: List[Any]
    ) -> float:
        """
        Calculate recommendation score for a module.
        
        Args:
            module: Training module to score
            user_profile: User's learning profile
            user_history: User's enrollment history
            
        Returns:
            Recommendation score (0.0 to 1.0)
        """
        try:
            score = 0.0
            
            # Base score from category preference
            category_preference = user_profile['preferred_categories'].get(module.category, 0.0)
            score += category_preference * 0.3
            
            # Category weight bonus
            category_weight = self.category_weights.get(module.category, 0.5)
            score += category_weight * 0.2
            
            # Difficulty progression score
            difficulty_score = self._calculate_difficulty_score(module, user_profile)
            score += difficulty_score * 0.25
            
            # Prerequisites check
            prereq_score = self._calculate_prerequisite_score(module, user_history)
            score += prereq_score * 0.15
            
            # Mandatory module bonus
            if module.is_mandatory:
                score += 0.3
            
            # Recency bonus for areas of improvement
            if module.category in user_profile['areas_for_improvement']:
                score += 0.2
            
            # Duration preference (prefer modules matching user's average time)
            duration_score = self._calculate_duration_preference_score(module, user_profile)
            score += duration_score * 0.1
            
            # Popularity bonus (based on completion rates)
            popularity_score = self._calculate_popularity_score(module)
            score += popularity_score * 0.05
            
            # Normalize score to 0-1 range
            return min(1.0, max(0.0, score))
            
        except Exception as e:
            logger.warning("Score calculation failed", module_id=str(module.id), error=str(e))
            return 0.0
    
    def _calculate_difficulty_score(self, module: Any, user_profile: Dict[str, Any]) -> float:
        """Calculate score based on difficulty progression."""
        difficulty_counts = user_profile['difficulty_progression']
        
        if not difficulty_counts:
            # New user - recommend beginner modules
            return 1.0 if module.difficulty_level == 'beginner' else 0.3
        
        # Find user's current level
        max_completed_level = 'beginner'
        for level in ['expert', 'advanced', 'intermediate', 'beginner']:
            if difficulty_counts.get(level, 0) > 0:
                max_completed_level = level
                break
        
        # Check if module difficulty is appropriate
        appropriate_levels = self.difficulty_progression.get(max_completed_level, ['beginner'])
        
        if module.difficulty_level in appropriate_levels:
            return 1.0
        elif module.difficulty_level == 'beginner' and max_completed_level != 'beginner':
            return 0.3  # Lower score for going backwards
        else:
            return 0.1  # Very low score for inappropriate difficulty
    
    def _calculate_prerequisite_score(self, module: Any, user_history: List[Any]) -> float:
        """Calculate score based on prerequisite completion."""
        if not module.prerequisites:
            return 1.0  # No prerequisites required
        
        # Get completed module codes
        completed_codes = set()
        for enrollment in user_history:
            if enrollment.status == 'completed':
                completed_codes.add(enrollment.module.module_code)
        
        # Check prerequisite completion
        met_prerequisites = sum(1 for prereq in module.prerequisites if prereq in completed_codes)
        total_prerequisites = len(module.prerequisites)
        
        return met_prerequisites / total_prerequisites if total_prerequisites > 0 else 1.0
    
    def _calculate_duration_preference_score(self, module: Any, user_profile: Dict[str, Any]) -> float:
        """Calculate score based on user's time preferences."""
        user_avg_time = user_profile['average_time_per_module']
        
        if user_avg_time == 0:
            return 0.5  # Neutral score for new users
        
        module_duration = module.estimated_duration_minutes
        
        # Prefer modules within 50% of user's average time
        time_ratio = abs(module_duration - user_avg_time) / user_avg_time
        
        if time_ratio <= 0.5:
            return 1.0
        elif time_ratio <= 1.0:
            return 0.7
        else:
            return 0.3
    
    def _calculate_popularity_score(self, module: Any) -> float:
        """Calculate score based on module popularity."""
        try:
            from core_infra.database.models import TrainingEnrollment
            
            # Get enrollment and completion counts
            total_enrollments = TrainingEnrollment.query.filter(
                TrainingEnrollment.module_id == module.id
            ).count()
            
            completed_enrollments = TrainingEnrollment.query.filter(
                TrainingEnrollment.module_id == module.id,
                TrainingEnrollment.status == 'completed'
            ).count()
            
            if total_enrollments == 0:
                return 0.5  # Neutral score for new modules
            
            completion_rate = completed_enrollments / total_enrollments
            
            # Higher completion rate = higher popularity score
            return completion_rate
            
        except Exception as e:
            logger.warning("Popularity calculation failed", module_id=str(module.id), error=str(e))
            return 0.5
    
    def _get_recommendation_reasons(self, module: Any, user_profile: Dict[str, Any]) -> List[str]:
        """Generate human-readable reasons for recommendation."""
        reasons = []
        
        # Category preference
        category_pref = user_profile['preferred_categories'].get(module.category, 0.0)
        if category_pref > 0.3:
            reasons.append(f"Matches your interest in {module.category}")
        
        # Mandatory modules
        if module.is_mandatory:
            reasons.append("Required training for your role")
        
        # Areas for improvement
        if module.category in user_profile['areas_for_improvement']:
            reasons.append(f"Helps improve your {module.category} skills")
        
        # Difficulty progression
        difficulty_counts = user_profile['difficulty_progression']
        if difficulty_counts:
            max_level = max(difficulty_counts.keys(), key=lambda x: difficulty_counts[x])
            if module.difficulty_level in self.difficulty_progression.get(max_level, []):
                reasons.append(f"Appropriate {module.difficulty_level} level for your experience")
        
        # Prerequisites met
        if module.prerequisites:
            reasons.append("You've completed the prerequisite modules")
        
        # Default reason
        if not reasons:
            reasons.append("Recommended based on your learning profile")
        
        return reasons
    
    def get_learning_path_recommendations(
        self,
        user_id: str,
        target_category: str,
        target_level: str = 'advanced'
    ) -> List[Dict[str, Any]]:
        """
        Generate a complete learning path for a specific category.
        
        Args:
            user_id: User identifier
            target_category: Target learning category
            target_level: Target difficulty level
            
        Returns:
            Ordered list of modules forming a learning path
        """
        try:
            from core_infra.database.models import TrainingModule, TrainingEnrollment
            
            # Get user's current progress in the category
            user_enrollments = TrainingEnrollment.query.filter(
                TrainingEnrollment.user_id == user_id
            ).all()
            
            completed_in_category = [
                e for e in user_enrollments 
                if e.module.category == target_category and e.status == 'completed'
            ]
            
            # Get all modules in the category
            category_modules = TrainingModule.query.filter(
                TrainingModule.category == target_category,
                TrainingModule.is_active == True
            ).order_by(
                TrainingModule.difficulty_level,
                TrainingModule.estimated_duration_minutes
            ).all()
            
            # Build learning path
            learning_path = []
            difficulty_order = ['beginner', 'intermediate', 'advanced', 'expert']
            
            for difficulty in difficulty_order:
                level_modules = [m for m in category_modules if m.difficulty_level == difficulty]
                
                for module in level_modules:
                    # Check if already completed
                    already_completed = any(
                        e.module_id == module.id for e in completed_in_category
                    )
                    
                    if not already_completed:
                        learning_path.append({
                            'id': str(module.id),
                            'title': module.title,
                            'difficulty_level': module.difficulty_level,
                            'estimated_duration_minutes': module.estimated_duration_minutes,
                            'prerequisites': module.prerequisites,
                            'order': len(learning_path) + 1
                        })
                
                # Stop if we've reached the target level
                if difficulty == target_level:
                    break
            
            return learning_path
            
        except Exception as e:
            logger.error("Learning path generation failed", user_id=user_id, error=str(e))
            return []
