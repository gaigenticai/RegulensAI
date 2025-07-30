"""
Search Engine Utilities
Advanced search functionality for training portal and other components.
"""

import re
import math
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Query
from sqlalchemy import or_, and_, func, text
from datetime import datetime

import structlog

logger = structlog.get_logger(__name__)


class SearchEngine:
    """Advanced search engine with semantic search and ranking capabilities."""
    
    def __init__(self):
        self.stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with', 'the', 'this', 'but', 'they', 'have',
            'had', 'what', 'said', 'each', 'which', 'their', 'time', 'if'
        }
        
    def search_training_content(
        self, 
        query: str, 
        base_query: Query, 
        limit: int = 50
    ) -> List[Tuple[Any, float]]:
        """
        Search training modules with advanced ranking.
        
        Args:
            query: Search query string
            base_query: Base SQLAlchemy query to filter
            limit: Maximum number of results
            
        Returns:
            List of tuples (model_instance, relevance_score)
        """
        try:
            if not query.strip():
                return [(item, 0.0) for item in base_query.limit(limit).all()]
            
            # Tokenize and clean query
            search_terms = self._tokenize_query(query)
            if not search_terms:
                return [(item, 0.0) for item in base_query.limit(limit).all()]
            
            # Build search conditions
            search_conditions = self._build_search_conditions(search_terms)
            
            # Apply search to query
            filtered_query = base_query.filter(search_conditions)
            results = filtered_query.all()
            
            # Calculate relevance scores
            scored_results = []
            for item in results:
                score = self._calculate_relevance_score(item, search_terms, query)
                scored_results.append((item, score))
            
            # Sort by relevance score
            scored_results.sort(key=lambda x: x[1], reverse=True)
            
            return scored_results[:limit]
            
        except Exception as e:
            logger.error("Search failed", query=query, error=str(e))
            # Fallback to basic query
            return [(item, 0.0) for item in base_query.limit(limit).all()]
    
    def _tokenize_query(self, query: str) -> List[str]:
        """
        Tokenize search query into meaningful terms.
        
        Args:
            query: Raw search query
            
        Returns:
            List of cleaned search terms
        """
        # Convert to lowercase and remove special characters
        cleaned = re.sub(r'[^\w\s]', ' ', query.lower())
        
        # Split into words
        words = cleaned.split()
        
        # Remove stop words and short words
        meaningful_words = [
            word for word in words 
            if len(word) > 2 and word not in self.stop_words
        ]
        
        return meaningful_words
    
    def _build_search_conditions(self, search_terms: List[str]):
        """
        Build SQLAlchemy search conditions for training modules.
        
        Args:
            search_terms: List of search terms
            
        Returns:
            SQLAlchemy condition for filtering
        """
        from core_infra.database.models import TrainingModule
        
        conditions = []
        
        for term in search_terms:
            term_pattern = f"%{term}%"
            
            # Search in multiple fields with different weights
            term_conditions = or_(
                TrainingModule.title.ilike(term_pattern),
                TrainingModule.description.ilike(term_pattern),
                TrainingModule.category.ilike(term_pattern),
                TrainingModule.learning_objectives.astext.ilike(term_pattern),
                # Search in JSON content
                func.jsonb_path_exists(
                    TrainingModule.content_data,
                    f'$.** ? (@ like_regex "{term}" flag "i")'
                )
            )
            conditions.append(term_conditions)
        
        # All terms should match (AND logic)
        return and_(*conditions) if len(conditions) > 1 else conditions[0]
    
    def _calculate_relevance_score(
        self, 
        item: Any, 
        search_terms: List[str], 
        original_query: str
    ) -> float:
        """
        Calculate relevance score for a search result.
        
        Args:
            item: Database model instance
            search_terms: Tokenized search terms
            original_query: Original search query
            
        Returns:
            Relevance score (0.0 to 1.0)
        """
        try:
            score = 0.0
            max_score = 0.0
            
            # Title matching (highest weight)
            title_score = self._calculate_field_score(
                item.title or '', search_terms, weight=3.0
            )
            score += title_score
            max_score += 3.0
            
            # Description matching
            description_score = self._calculate_field_score(
                item.description or '', search_terms, weight=2.0
            )
            score += description_score
            max_score += 2.0
            
            # Category matching
            category_score = self._calculate_field_score(
                item.category or '', search_terms, weight=1.5
            )
            score += category_score
            max_score += 1.5
            
            # Learning objectives matching
            if hasattr(item, 'learning_objectives') and item.learning_objectives:
                objectives_text = ' '.join(item.learning_objectives)
                objectives_score = self._calculate_field_score(
                    objectives_text, search_terms, weight=1.0
                )
                score += objectives_score
                max_score += 1.0
            
            # Content data matching
            if hasattr(item, 'content_data') and item.content_data:
                content_text = self._extract_text_from_json(item.content_data)
                content_score = self._calculate_field_score(
                    content_text, search_terms, weight=0.5
                )
                score += content_score
                max_score += 0.5
            
            # Exact phrase bonus
            if self._contains_exact_phrase(item.title or '', original_query):
                score += 0.5
                max_score += 0.5
            
            # Normalize score
            return score / max_score if max_score > 0 else 0.0
            
        except Exception as e:
            logger.warning("Score calculation failed", item_id=getattr(item, 'id', 'unknown'), error=str(e))
            return 0.0
    
    def _calculate_field_score(
        self, 
        field_text: str, 
        search_terms: List[str], 
        weight: float = 1.0
    ) -> float:
        """
        Calculate score for a specific field.
        
        Args:
            field_text: Text content of the field
            search_terms: Search terms to match
            weight: Weight multiplier for this field
            
        Returns:
            Weighted score for the field
        """
        if not field_text or not search_terms:
            return 0.0
        
        field_lower = field_text.lower()
        matches = 0
        total_terms = len(search_terms)
        
        for term in search_terms:
            if term in field_lower:
                matches += 1
                
                # Bonus for exact word matches
                if re.search(r'\b' + re.escape(term) + r'\b', field_lower):
                    matches += 0.5
        
        # Calculate match ratio
        match_ratio = matches / total_terms if total_terms > 0 else 0.0
        
        return match_ratio * weight
    
    def _contains_exact_phrase(self, text: str, phrase: str) -> bool:
        """
        Check if text contains the exact phrase.
        
        Args:
            text: Text to search in
            phrase: Phrase to search for
            
        Returns:
            True if exact phrase is found
        """
        if not text or not phrase:
            return False
        
        return phrase.lower() in text.lower()
    
    def _extract_text_from_json(self, json_data: Dict[str, Any]) -> str:
        """
        Extract searchable text from JSON data.
        
        Args:
            json_data: JSON data to extract text from
            
        Returns:
            Concatenated text content
        """
        text_parts = []
        
        def extract_recursive(obj):
            if isinstance(obj, dict):
                for value in obj.values():
                    extract_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_recursive(item)
            elif isinstance(obj, str):
                text_parts.append(obj)
        
        try:
            extract_recursive(json_data)
            return ' '.join(text_parts)
        except Exception:
            return ''
    
    def search_discussions(
        self, 
        query: str, 
        module_id: Optional[str] = None,
        discussion_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Tuple[Any, float]]:
        """
        Search training discussions with relevance scoring.
        
        Args:
            query: Search query
            module_id: Optional module ID filter
            discussion_type: Optional discussion type filter
            limit: Maximum results
            
        Returns:
            List of scored discussion results
        """
        try:
            from core_infra.database.models import TrainingDiscussion
            
            # Build base query
            base_query = TrainingDiscussion.query
            
            if module_id:
                base_query = base_query.filter(TrainingDiscussion.module_id == module_id)
            
            if discussion_type:
                base_query = base_query.filter(TrainingDiscussion.discussion_type == discussion_type)
            
            # Tokenize query
            search_terms = self._tokenize_query(query)
            if not search_terms:
                return [(item, 0.0) for item in base_query.limit(limit).all()]
            
            # Build search conditions for discussions
            conditions = []
            for term in search_terms:
                term_pattern = f"%{term}%"
                term_conditions = or_(
                    TrainingDiscussion.title.ilike(term_pattern),
                    TrainingDiscussion.content.ilike(term_pattern)
                )
                conditions.append(term_conditions)
            
            search_condition = and_(*conditions) if len(conditions) > 1 else conditions[0]
            filtered_query = base_query.filter(search_condition)
            results = filtered_query.all()
            
            # Score results
            scored_results = []
            for discussion in results:
                score = self._calculate_discussion_score(discussion, search_terms, query)
                scored_results.append((discussion, score))
            
            # Sort by score and recency
            scored_results.sort(key=lambda x: (x[1], x[0].created_at), reverse=True)
            
            return scored_results[:limit]
            
        except Exception as e:
            logger.error("Discussion search failed", query=query, error=str(e))
            return []
    
    def _calculate_discussion_score(
        self, 
        discussion: Any, 
        search_terms: List[str], 
        original_query: str
    ) -> float:
        """Calculate relevance score for discussion results."""
        try:
            score = 0.0
            max_score = 0.0
            
            # Title matching (high weight)
            if discussion.title:
                title_score = self._calculate_field_score(
                    discussion.title, search_terms, weight=2.0
                )
                score += title_score
                max_score += 2.0
            
            # Content matching
            content_score = self._calculate_field_score(
                discussion.content or '', search_terms, weight=1.5
            )
            score += content_score
            max_score += 1.5
            
            # Boost for resolved discussions
            if discussion.is_resolved:
                score += 0.2
                max_score += 0.2
            
            # Boost for highly voted discussions
            if hasattr(discussion, 'upvotes') and discussion.upvotes > 5:
                score += 0.3
                max_score += 0.3
            
            return score / max_score if max_score > 0 else 0.0
            
        except Exception as e:
            logger.warning("Discussion score calculation failed", error=str(e))
            return 0.0
    
    def suggest_search_terms(self, partial_query: str, limit: int = 10) -> List[str]:
        """
        Suggest search terms based on partial input.
        
        Args:
            partial_query: Partial search query
            limit: Maximum suggestions
            
        Returns:
            List of suggested search terms
        """
        try:
            if len(partial_query) < 2:
                return []
            
            from core_infra.database.models import TrainingModule
            
            suggestions = set()
            
            # Get suggestions from module titles
            title_matches = TrainingModule.query.filter(
                TrainingModule.title.ilike(f"%{partial_query}%")
            ).limit(limit).all()
            
            for module in title_matches:
                # Extract relevant words from title
                words = re.findall(r'\b\w+\b', module.title.lower())
                for word in words:
                    if partial_query.lower() in word and len(word) > 2:
                        suggestions.add(word)
            
            # Get suggestions from categories
            category_matches = TrainingModule.query.filter(
                TrainingModule.category.ilike(f"%{partial_query}%")
            ).distinct(TrainingModule.category).limit(5).all()
            
            for module in category_matches:
                if partial_query.lower() in module.category.lower():
                    suggestions.add(module.category)
            
            return sorted(list(suggestions))[:limit]
            
        except Exception as e:
            logger.error("Search suggestion failed", query=partial_query, error=str(e))
            return []
