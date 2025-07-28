"""
Vector Store Service
Manages vector embeddings storage and search using Qdrant.
"""

import asyncio
import uuid
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import structlog
import json

# Qdrant client
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        VectorParams, Distance, PointStruct, Filter, 
        FieldCondition, MatchValue, SearchRequest,
        Collection, CollectionStatus
    )
    from qdrant_client.http import models
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

from core_infra.config import get_settings
from core_infra.services.monitoring import track_operation

logger = structlog.get_logger(__name__)
settings = get_settings()


class VectorStore:
    """
    Vector store client for managing document embeddings using Qdrant.
    Provides storage, search, and management capabilities for regulatory documents.
    """
    
    def __init__(self):
        self.client = None
        self.collection_name = settings.qdrant_collection_name
        self.vector_dimension = settings.vector_dimension
        self.is_connected = False
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Qdrant client connection."""
        if not QDRANT_AVAILABLE:
            logger.error("Qdrant client not available. Install qdrant-client package.")
            return
        
        try:
            # Create client connection
            if settings.qdrant_api_key:
                self.client = QdrantClient(
                    host=settings.qdrant_host,
                    port=settings.qdrant_port,
                    api_key=settings.qdrant_api_key.get_secret_value(),
                    https=True if settings.qdrant_api_key else False
                )
            else:
                self.client = QdrantClient(
                    host=settings.qdrant_host,
                    port=settings.qdrant_port
                )
            
            logger.info(f"Qdrant client initialized: {settings.qdrant_host}:{settings.qdrant_port}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {e}")
            self.client = None
    
    async def connect(self) -> bool:
        """Establish connection and ensure collection exists."""
        if not self.client:
            logger.error("Qdrant client not available")
            return False
        
        try:
            # Test connection
            collections = await self._run_sync(self.client.get_collections)
            logger.info(f"Connected to Qdrant. Collections: {len(collections.collections)}")
            
            # Ensure collection exists
            await self._ensure_collection()
            
            self.is_connected = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            self.is_connected = False
            return False
    
    async def _run_sync(self, func, *args, **kwargs):
        """Run synchronous Qdrant operations in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)
    
    async def _ensure_collection(self):
        """Ensure the collection exists with proper configuration."""
        try:
            # Check if collection exists
            collections = await self._run_sync(self.client.get_collections)
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating collection: {self.collection_name}")
                
                # Create collection
                await self._run_sync(
                    self.client.create_collection,
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_dimension,
                        distance=Distance.COSINE
                    )
                )
                
                logger.info(f"Created collection: {self.collection_name}")
            else:
                logger.info(f"Collection already exists: {self.collection_name}")
                
                # Verify collection configuration
                collection_info = await self._run_sync(
                    self.client.get_collection,
                    self.collection_name
                )
                
                if collection_info.config.params.vectors.size != self.vector_dimension:
                    logger.warning(
                        f"Collection vector dimension mismatch. "
                        f"Expected: {self.vector_dimension}, "
                        f"Actual: {collection_info.config.params.vectors.size}"
                    )
                
        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")
            raise
    
    @track_operation("vector_store.store_document")
    async def store_document(self, document_id: str, embeddings: List[float],
                           metadata: Dict[str, Any], text: str = "") -> bool:
        """
        Store document embeddings with metadata.
        
        Args:
            document_id: Unique document identifier
            embeddings: Vector embeddings for the document
            metadata: Document metadata
            text: Document text excerpt for context
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.is_connected:
                await self.connect()
            
            if not self.is_connected:
                return False
            
            # Validate embeddings dimension
            if len(embeddings) != self.vector_dimension:
                logger.error(
                    f"Embedding dimension mismatch for {document_id}. "
                    f"Expected: {self.vector_dimension}, Got: {len(embeddings)}"
                )
                return False
            
            # Prepare payload
            payload = {
                "document_id": document_id,
                "text_excerpt": text[:500],  # Store first 500 chars
                "created_at": datetime.utcnow().isoformat(),
                **metadata
            }
            
            # Create point
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embeddings,
                payload=payload
            )
            
            # Store in Qdrant
            await self._run_sync(
                self.client.upsert,
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.debug(f"Stored embeddings for document: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store document {document_id}: {e}")
            return False
    
    @track_operation("vector_store.search_similar")
    async def search_similar(self, query_embeddings: List[float],
                           limit: int = 10,
                           score_threshold: float = 0.7,
                           filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Search for similar documents using vector similarity.
        
        Args:
            query_embeddings: Query vector embeddings
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            filters: Optional metadata filters
            
        Returns:
            List of similar documents with scores and metadata
        """
        try:
            if not self.is_connected:
                await self.connect()
            
            if not self.is_connected:
                return []
            
            # Validate query embeddings dimension
            if len(query_embeddings) != self.vector_dimension:
                logger.error(
                    f"Query embedding dimension mismatch. "
                    f"Expected: {self.vector_dimension}, Got: {len(query_embeddings)}"
                )
                return []
            
            # Build filter if provided
            search_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    if isinstance(value, list):
                        # Handle list values (IN filter)
                        for v in value:
                            conditions.append(
                                FieldCondition(key=key, match=MatchValue(value=v))
                            )
                    else:
                        conditions.append(
                            FieldCondition(key=key, match=MatchValue(value=value))
                        )
                
                if conditions:
                    search_filter = Filter(must=conditions)
            
            # Perform search
            search_result = await self._run_sync(
                self.client.search,
                collection_name=self.collection_name,
                query_vector=query_embeddings,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=search_filter,
                with_payload=True,
                with_vectors=False  # Don't return vectors to save bandwidth
            )
            
            # Format results
            results = []
            for hit in search_result:
                result = {
                    "document_id": hit.payload.get("document_id"),
                    "score": hit.score,
                    "metadata": {k: v for k, v in hit.payload.items() 
                               if k not in ["document_id", "text_excerpt"]},
                    "text_excerpt": hit.payload.get("text_excerpt", ""),
                    "point_id": hit.id
                }
                results.append(result)
            
            logger.debug(f"Found {len(results)} similar documents")
            return results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    @track_operation("vector_store.get_document")
    async def get_document_embeddings(self, document_id: str) -> Optional[List[float]]:
        """
        Get embeddings for a specific document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Vector embeddings or None if not found
        """
        try:
            if not self.is_connected:
                await self.connect()
            
            if not self.is_connected:
                return None
            
            # Search for document by ID
            search_result = await self._run_sync(
                self.client.scroll,
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id)
                        )
                    ]
                ),
                limit=1,
                with_vectors=True,
                with_payload=False
            )
            
            if search_result[0]:  # If points found
                return search_result[0][0].vector
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get embeddings for document {document_id}: {e}")
            return None
    
    @track_operation("vector_store.delete_document")
    async def delete_document(self, document_id: str) -> bool:
        """
        Delete embeddings for a document.
        
        Args:
            document_id: Document identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.is_connected:
                await self.connect()
            
            if not self.is_connected:
                return False
            
            # Find points with matching document_id
            search_result = await self._run_sync(
                self.client.scroll,
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id)
                        )
                    ]
                ),
                with_vectors=False,
                with_payload=True
            )
            
            points_to_delete = [point.id for point in search_result[0]]
            
            if points_to_delete:
                # Delete points
                await self._run_sync(
                    self.client.delete,
                    collection_name=self.collection_name,
                    points_selector=models.PointIdsList(
                        points=points_to_delete
                    )
                )
                
                logger.debug(f"Deleted {len(points_to_delete)} points for document: {document_id}")
                return True
            else:
                logger.warning(f"No points found for document: {document_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False
    
    @track_operation("vector_store.find_similar_documents")
    async def find_similar_documents(self, document_id: str,
                                   limit: int = 5,
                                   score_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Find documents similar to a specific document.
        
        Args:
            document_id: Reference document ID
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            
        Returns:
            List of similar documents
        """
        try:
            # Get embeddings for the reference document
            embeddings = await self.get_document_embeddings(document_id)
            if not embeddings:
                logger.warning(f"No embeddings found for document: {document_id}")
                return []
            
            # Search for similar documents
            similar_docs = await self.search_similar(
                query_embeddings=embeddings,
                limit=limit + 1,  # +1 because the document itself might be included
                score_threshold=score_threshold
            )
            
            # Filter out the original document
            filtered_docs = [
                doc for doc in similar_docs 
                if doc["document_id"] != document_id
            ]
            
            return filtered_docs[:limit]
            
        except Exception as e:
            logger.error(f"Failed to find similar documents for {document_id}: {e}")
            return []
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        try:
            if not self.is_connected:
                await self.connect()
            
            if not self.is_connected:
                return {"error": "Not connected to Qdrant"}
            
            # Get collection info
            collection_info = await self._run_sync(
                self.client.get_collection,
                self.collection_name
            )
            
            stats = {
                "collection_name": self.collection_name,
                "vector_dimension": self.vector_dimension,
                "distance_metric": collection_info.config.params.vectors.distance.value,
                "status": collection_info.status.value,
                "points_count": collection_info.points_count,
                "segments_count": collection_info.segments_count,
                "indexed_vectors_count": getattr(collection_info, 'indexed_vectors_count', 0),
                "disk_data_size": getattr(collection_info, 'disk_data_size', 0),
                "ram_data_size": getattr(collection_info, 'ram_data_size', 0),
                "is_connected": self.is_connected
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get vector store stats: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on vector store."""
        try:
            if not self.client:
                return {"status": "error", "message": "Client not initialized"}
            
            # Test connection
            collections = await self._run_sync(self.client.get_collections)
            
            # Check collection exists
            collection_names = [col.name for col in collections.collections]
            collection_exists = self.collection_name in collection_names
            
            status = "healthy" if collection_exists else "degraded"
            message = "All checks passed" if collection_exists else "Collection missing"
            
            return {
                "status": status,
                "message": message,
                "collection_exists": collection_exists,
                "total_collections": len(collections.collections),
                "connected": True
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "connected": False
            }
    
    async def create_index(self, field_name: str, field_type: str = "keyword") -> bool:
        """
        Create an index on a payload field for faster filtering.
        
        Args:
            field_name: Name of the field to index
            field_type: Type of index ('keyword', 'integer', 'float', 'bool')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.is_connected:
                await self.connect()
            
            if not self.is_connected:
                return False
            
            # Create index
            await self._run_sync(
                self.client.create_payload_index,
                collection_name=self.collection_name,
                field_name=field_name,
                field_schema=field_type
            )
            
            logger.info(f"Created index on field: {field_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create index on {field_name}: {e}")
            return False
    
    async def backup_collection(self, backup_path: str) -> bool:
        """
        Create a backup of the collection.
        
        Args:
            backup_path: Path to store the backup
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.is_connected:
                await self.connect()
            
            if not self.is_connected:
                return False
            
            # Create snapshot
            snapshot_result = await self._run_sync(
                self.client.create_snapshot,
                collection_name=self.collection_name
            )
            
            logger.info(f"Created backup snapshot: {snapshot_result.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False
    
    async def optimize_collection(self) -> bool:
        """
        Optimize the collection for better performance.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.is_connected:
                await self.connect()
            
            if not self.is_connected:
                return False
            
            # Trigger optimization
            await self._run_sync(
                self.client.update_collection,
                collection_name=self.collection_name,
                optimizer_config=models.OptimizersConfigDiff(
                    indexing_threshold=10000,
                    max_segment_size=100000
                )
            )
            
            logger.info(f"Optimization triggered for collection: {self.collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to optimize collection: {e}")
            return False


# Global vector store instance
_vector_store = None


async def get_vector_store() -> VectorStore:
    """Get the global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
        await _vector_store.connect()
    return _vector_store


async def initialize_vector_store():
    """Initialize and connect to vector store."""
    vector_store = await get_vector_store()
    return vector_store.is_connected 