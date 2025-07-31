"""
AI Embeddings Service
Generates vector embeddings for regulatory documents and text content.
"""

import asyncio
import numpy as np
from typing import List, Dict, Any, Optional, Union
import structlog
from datetime import datetime
import hashlib

# FastEmbed for local embeddings
try:
    from fastembed import TextEmbedding
    FASTEMBED_AVAILABLE = True
except ImportError:
    FASTEMBED_AVAILABLE = False

# OpenAI embeddings
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from core_infra.config import get_settings
from core_infra.services.monitoring import track_operation

logger = structlog.get_logger(__name__)
settings = get_settings()


class EmbeddingsClient:
    """
    Client for generating text embeddings using various providers.
    Supports both local (FastEmbed) and cloud (OpenAI) embedding models.
    """
    
    def __init__(self):
        self.fastembed_model = None
        self.openai_client = None
        self.cache = {}  # Simple in-memory cache
        self.max_cache_size = 1000
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize embedding model clients."""
        try:
            # Initialize FastEmbed (local model)
            if FASTEMBED_AVAILABLE:
                try:
                    self.fastembed_model = TextEmbedding(
                        model_name=settings.fastembed_model,
                        cache_dir=settings.fastembed_cache_dir
                    )
                    logger.info(f"FastEmbed model loaded: {settings.fastembed_model}")
                except Exception as e:
                    logger.warning(f"Failed to load FastEmbed model: {e}")
            
            # Initialize OpenAI client
            if OPENAI_AVAILABLE and settings.openai_api_key:
                openai.api_key = settings.openai_api_key.get_secret_value()
                self.openai_client = openai
                logger.info("OpenAI embeddings client initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize embedding clients: {e}")
    
    @track_operation("embeddings.generate_embeddings")
    async def generate_embeddings(self, text: Union[str, List[str]], 
                                model: str = "auto") -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings for text content.
        
        Args:
            text: Single text string or list of text strings
            model: Embedding model to use ('auto', 'fastembed', 'openai')
            
        Returns:
            Single embedding vector or list of embedding vectors
        """
        try:
            is_batch = isinstance(text, list)
            texts = text if is_batch else [text]
            
            if not texts or (len(texts) == 1 and not texts[0].strip()):
                raise ValueError("Empty text provided")
            
            # Separate cached from non-cached texts
            cached_embeddings: Dict[int, List[float]] = {}
            texts_to_process: Dict[int, str] = {}
            
            for i, txt in enumerate(texts):
                cache_key = self._get_cache_key(txt, model)
                if cache_key in self.cache:
                    cached_embeddings[i] = self.cache[cache_key]
                else:
                    texts_to_process[i] = txt

            # Process texts that are not cached
            new_embeddings: Dict[int, List[float]] = {}
            if texts_to_process:
                indices_to_process = list(texts_to_process.keys())
                texts_for_embedding = list(texts_to_process.values())
                
                if model == "auto":
                    model = self._choose_best_model()
                
                generated_embeddings = []
                if model == "fastembed" and self.fastembed_model:
                    generated_embeddings = await self._generate_fastembed_embeddings(texts_for_embedding)
                elif model == "openai" and self.openai_client:
                    generated_embeddings = await self._generate_openai_embeddings(texts_for_embedding)
                else:
                    if self.fastembed_model:
                        generated_embeddings = await self._generate_fastembed_embeddings(texts_for_embedding)
                    elif self.openai_client:
                        generated_embeddings = await self._generate_openai_embeddings(texts_for_embedding)
                    else:
                        raise Exception("No embedding models available")

                for i, embedding in zip(indices_to_process, generated_embeddings):
                    new_embeddings[i] = embedding
                    cache_key = self._get_cache_key(texts[i], model)
                    self._cache_embedding(cache_key, embedding)

            # Combine cached and new embeddings in the correct order
            result_embeddings = []
            for i in range(len(texts)):
                if i in cached_embeddings:
                    result_embeddings.append(cached_embeddings[i])
                elif i in new_embeddings:
                    result_embeddings.append(new_embeddings[i])
            
            return result_embeddings if is_batch else result_embeddings[0]
                
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    async def _generate_fastembed_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using FastEmbed (local model)."""
        try:
            # Preprocess texts
            processed_texts = [self._preprocess_text(text) for text in texts]
            
            # Generate embeddings
            embeddings = list(self.fastembed_model.embed(processed_texts))
            
            # Convert to list of lists
            return [embedding.tolist() for embedding in embeddings]
            
        except Exception as e:
            logger.error(f"FastEmbed embedding generation failed: {e}")
            raise
    
    async def _generate_openai_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API."""
        try:
            # Preprocess texts
            processed_texts = [self._preprocess_text(text) for text in texts]
            
            # Batch API calls for efficiency
            batch_size = 20  # OpenAI recommended batch size
            all_embeddings = []
            
            for i in range(0, len(processed_texts), batch_size):
                batch = processed_texts[i:i + batch_size]
                
                response = await self.openai_client.Embedding.acreate(
                    model="text-embedding-ada-002",
                    input=batch
                )
                
                batch_embeddings = [data.embedding for data in response.data]
                all_embeddings.extend(batch_embeddings)
            
            return all_embeddings
            
        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {e}")
            raise
    
    def _preprocess_text(self, text: str, max_tokens: int = 8000) -> str:
        """Preprocess text for embedding generation."""
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Truncate if too long (approximate token count)
        if len(text) > max_tokens * 4:  # Rough estimation: 1 token ≈ 4 characters
            text = text[:max_tokens * 4]
            # Try to cut at sentence boundary
            last_period = text.rfind('.')
            if last_period > max_tokens * 3:  # Keep most of the text
                text = text[:last_period + 1]
        
        return text
    
    def _choose_best_model(self) -> str:
        """Choose the best available embedding model."""
        if self.fastembed_model:
            return "fastembed"  # Prefer local model for privacy and speed
        elif self.openai_client:
            return "openai"
        else:
            raise Exception("No embedding models available")
    
    def _get_cache_key(self, text: str, model: str) -> str:
        """Generate cache key for text and model combination."""
        content = f"{model}:{text}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _cache_embedding(self, cache_key: str, embedding: List[float]):
        """Cache an embedding result."""
        # Simple LRU cache eviction
        if len(self.cache) >= self.max_cache_size:
            # Remove oldest entry (first in dict)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        self.cache[cache_key] = embedding
    
    @track_operation("embeddings.similarity_search")
    async def find_similar_texts(self, query_text: str, 
                               candidate_texts: List[str],
                               top_k: int = 5,
                               threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Find similar texts using cosine similarity.
        
        Args:
            query_text: Text to find similarities for
            candidate_texts: List of candidate texts to compare against
            top_k: Number of top similar texts to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of similar texts with similarity scores
        """
        try:
            # Generate embeddings for query and candidates
            query_embedding = await self.generate_embeddings(query_text)
            candidate_embeddings = await self.generate_embeddings(candidate_texts)
            
            # Calculate similarities
            similarities = []
            for i, candidate_embedding in enumerate(candidate_embeddings):
                similarity = self._cosine_similarity(query_embedding, candidate_embedding)
                
                if similarity >= threshold:
                    similarities.append({
                        'index': i,
                        'text': candidate_texts[i],
                        'similarity': similarity
                    })
            
            # Sort by similarity (descending) and return top_k
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            # Convert to numpy arrays
            a = np.array(vec1)
            b = np.array(vec2)
            
            # Calculate cosine similarity
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            similarity = dot_product / (norm_a * norm_b)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Cosine similarity calculation failed: {e}")
            return 0.0
    
    async def get_embedding_stats(self) -> Dict[str, Any]:
        """Get embedding service statistics."""
        return {
            'fastembed_available': self.fastembed_model is not None,
            'openai_available': self.openai_client is not None,
            'cache_size': len(self.cache),
            'max_cache_size': self.max_cache_size,
            'preferred_model': self._choose_best_model() if (self.fastembed_model or self.openai_client) else None
        }
    
    def clear_cache(self):
        """Clear the embedding cache."""
        self.cache.clear()
        logger.info("Embedding cache cleared")


class DocumentEmbeddingsManager:
    """
    Manages embeddings for regulatory documents with persistence and search capabilities.
    """
    
    def __init__(self):
        self.embeddings_client = EmbeddingsClient()
        self.vector_store = None  # Will be initialized when needed
    
    async def _get_vector_store(self):
        """Get vector store client (lazy initialization)."""
        if self.vector_store is None:
            from .vector_store import get_vector_store
            self.vector_store = await get_vector_store()
        return self.vector_store
    
    @track_operation("doc_embeddings.process_document")
    async def process_document(self, document_id: str, text_content: str, 
                             metadata: Dict[str, Any] = None) -> bool:
        """
        Process a document by generating embeddings and storing them.
        
        Args:
            document_id: Unique document identifier
            text_content: Document text content
            metadata: Additional document metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not text_content.strip():
                logger.warning(f"Empty text content for document {document_id}")
                return False
            
            # Generate embeddings
            embeddings = await self.embeddings_client.generate_embeddings(text_content)
            
            # Store in vector database
            vector_store = await self._get_vector_store()
            success = await vector_store.store_document(
                document_id=document_id,
                embeddings=embeddings,
                metadata=metadata or {},
                text=text_content[:1000]  # Store excerpt for context
            )
            
            if success:
                logger.info(f"Processed embeddings for document {document_id}")
            else:
                logger.error(f"Failed to store embeddings for document {document_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to process document {document_id}: {e}")
            return False
    
    @track_operation("doc_embeddings.search_similar")
    async def search_similar_documents(self, query_text: str, 
                                     limit: int = 10,
                                     filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Search for documents similar to the query text.
        
        Args:
            query_text: Text to search for
            limit: Maximum number of results
            filters: Optional metadata filters
            
        Returns:
            List of similar documents with scores
        """
        try:
            # Generate query embeddings
            query_embeddings = await self.embeddings_client.generate_embeddings(query_text)
            
            # Search in vector store
            vector_store = await self._get_vector_store()
            results = await vector_store.search_similar(
                query_embeddings=query_embeddings,
                limit=limit,
                filters=filters
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Similar document search failed: {e}")
            return []
    
    async def get_document_embeddings(self, document_id: str) -> Optional[List[float]]:
        """Get embeddings for a specific document."""
        try:
            vector_store = await self._get_vector_store()
            return await vector_store.get_document_embeddings(document_id)
        except Exception as e:
            logger.error(f"Failed to get embeddings for document {document_id}: {e}")
            return None
    
    async def delete_document_embeddings(self, document_id: str) -> bool:
        """Delete embeddings for a document."""
        try:
            vector_store = await self._get_vector_store()
            return await vector_store.delete_document(document_id)
        except Exception as e:
            logger.error(f"Failed to delete embeddings for document {document_id}: {e}")
            return False
    
    async def update_document_embeddings(self, document_id: str, 
                                       text_content: str,
                                       metadata: Dict[str, Any] = None) -> bool:
        """Update embeddings for an existing document."""
        try:
            # Delete existing embeddings
            await self.delete_document_embeddings(document_id)
            
            # Process new embeddings
            return await self.process_document(document_id, text_content, metadata)
            
        except Exception as e:
            logger.error(f"Failed to update embeddings for document {document_id}: {e}")
            return False
    
    async def bulk_process_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, bool]:
        """
        Process multiple documents in bulk.
        
        Args:
            documents: List of dicts with 'id', 'text', and optional 'metadata'
            
        Returns:
            Dict mapping document IDs to success status
        """
        results = {}
        
        # Process in batches to avoid overwhelming the system
        batch_size = 10
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            # Process batch concurrently
            tasks = []
            for doc in batch:
                task = self.process_document(
                    document_id=doc['id'],
                    text_content=doc['text'],
                    metadata=doc.get('metadata')
                )
                tasks.append(task)
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Record results
            for doc, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Batch processing failed for {doc['id']}: {result}")
                    results[doc['id']] = False
                else:
                    results[doc['id']] = result
        
        return results
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get document embeddings statistics."""
        try:
            vector_store = await self._get_vector_store()
            vector_stats = await vector_store.get_stats()
            
            embeddings_stats = await self.embeddings_client.get_embedding_stats()
            
            return {
                'vector_store': vector_stats,
                'embeddings_client': embeddings_stats,
                'total_documents': vector_stats.get('document_count', 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get embeddings stats: {e}")
            return {}


# Global instances
_embeddings_client = None
_doc_embeddings_manager = None


def get_embeddings_client() -> EmbeddingsClient:
    """Get the global embeddings client instance."""
    global _embeddings_client
    if _embeddings_client is None:
        _embeddings_client = EmbeddingsClient()
    return _embeddings_client


def get_document_embeddings_manager() -> DocumentEmbeddingsManager:
    """Get the global document embeddings manager instance."""
    global _doc_embeddings_manager
    if _doc_embeddings_manager is None:
        _doc_embeddings_manager = DocumentEmbeddingsManager()
    return _doc_embeddings_manager
