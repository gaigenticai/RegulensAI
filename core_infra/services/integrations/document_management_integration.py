"""
Document Management Integration Service

Provides enterprise-grade integration with document management systems:
- Microsoft SharePoint
- Box Enterprise
- Google Drive/Workspace
- AWS S3
- Azure Blob Storage

Features:
- Document lifecycle management
- Version control and approval workflows
- Metadata extraction and classification
- Content indexing and search
- Retention policy enforcement
- Compliance tagging
"""

import logging
import uuid
import json
import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import aiohttp
import mimetypes
from urllib.parse import urljoin

from core_infra.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class DocumentManagementIntegrationService:
    """
    Enterprise document management integration service.
    
    Handles document synchronization, lifecycle management, and compliance
    monitoring across multiple document management platforms.
    """
    
    def __init__(self, supabase_client, integration_manager=None):
        self.supabase = supabase_client
        self.integration_manager = integration_manager
        self.session = None
        self.connectors = {
            'sharepoint': SharePointConnector(supabase_client),
            'box': BoxConnector(supabase_client),
            'google_drive': GoogleDriveConnector(supabase_client),
            'aws_s3': AWSS3Connector(supabase_client),
            'azure_blob': AzureBlobConnector(supabase_client)
        }
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        for connector in self.connectors.values():
            await connector.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
        for connector in self.connectors.values():
            await connector.__aexit__(exc_type, exc_val, exc_tb)
    
    async def sync_documents(self, tenant_id: str, repository_type: str = None) -> Dict[str, Any]:
        """
        Synchronize documents from document repositories.
        
        Args:
            tenant_id: Tenant identifier
            repository_type: Specific repository type or None for all
            
        Returns:
            Synchronization results with statistics and errors
        """
        try:
            logger.info(f"Starting document sync for tenant {tenant_id}")
            
            sync_results = {
                'tenant_id': tenant_id,
                'started_at': datetime.utcnow(),
                'repositories_synced': [],
                'total_documents_processed': 0,
                'documents_created': 0,
                'documents_updated': 0,
                'documents_archived': 0,
                'metadata_extracted': 0,
                'compliance_tagged': 0,
                'errors': []
            }
            
            # Get enabled document repositories
            repositories = await self._get_enabled_repositories(tenant_id, repository_type)
            
            for repository in repositories:
                try:
                    logger.info(f"Syncing documents from {repository['repository_name']} ({repository['repository_type']})")
                    
                    connector = self.connectors.get(repository['repository_type'])
                    if not connector:
                        logger.warning(f"No connector available for {repository['repository_type']}")
                        continue
                    
                    # Perform sync with specific connector
                    repo_results = await connector.sync_documents(repository)
                    
                    # Update sync statistics
                    sync_results['repositories_synced'].append(repository['repository_name'])
                    sync_results['total_documents_processed'] += repo_results.get('total_processed', 0)
                    sync_results['documents_created'] += repo_results.get('created', 0)
                    sync_results['documents_updated'] += repo_results.get('updated', 0)
                    sync_results['documents_archived'] += repo_results.get('archived', 0)
                    sync_results['metadata_extracted'] += repo_results.get('metadata_extracted', 0)
                    sync_results['compliance_tagged'] += repo_results.get('compliance_tagged', 0)
                    
                    # Update repository last sync time
                    await self._update_repository_sync_time(repository['id'], repo_results)
                    
                except Exception as e:
                    error_msg = f"Error syncing {repository.get('repository_name', 'unknown')}: {str(e)}"
                    logger.error(error_msg)
                    sync_results['errors'].append(error_msg)
            
            sync_results['completed_at'] = datetime.utcnow()
            sync_results['success'] = len(sync_results['errors']) == 0
            
            # Log sync operation
            await self._log_integration_operation(
                tenant_id=tenant_id,
                operation_type='sync',
                operation_name='document_sync',
                status='success' if sync_results['success'] else 'partial_success',
                result=sync_results
            )
            
            logger.info(f"Document sync completed for tenant {tenant_id}: "
                       f"{sync_results['total_documents_processed']} documents processed")
            
            return sync_results
            
        except Exception as e:
            logger.error(f"Document sync failed for tenant {tenant_id}: {str(e)}")
            raise
    
    async def manage_document_lifecycle(self, tenant_id: str, document_id: str, 
                                      action: str) -> Dict[str, Any]:
        """
        Manage document lifecycle (review, approve, archive, delete).
        
        Args:
            tenant_id: Tenant identifier
            document_id: Document identifier
            action: Lifecycle action ('submit_for_review', 'approve', 'reject', 'archive', 'delete')
            
        Returns:
            Lifecycle action results
        """
        try:
            logger.info(f"Managing document lifecycle: {document_id} -> {action}")
            
            # Get document details
            document = await self._get_document(tenant_id, document_id)
            if not document:
                raise ValueError(f"Document not found: {document_id}")
            
            # Execute lifecycle action
            action_results = await self._execute_lifecycle_action(document, action)
            
            # Update document lifecycle stage
            await self._update_document_lifecycle_stage(document_id, action, action_results)
            
            # Send notifications if required
            await self._send_lifecycle_notifications(document, action, action_results)
            
            logger.info(f"Document lifecycle action completed: {document_id} -> {action}")
            
            return action_results
            
        except Exception as e:
            logger.error(f"Document lifecycle management failed: {str(e)}")
            raise
    
    async def extract_document_metadata(self, tenant_id: str, document_id: str) -> Dict[str, Any]:
        """
        Extract and analyze document metadata and content.
        
        Args:
            tenant_id: Tenant identifier
            document_id: Document identifier
            
        Returns:
            Extracted metadata and analysis results
        """
        try:
            logger.info(f"Extracting metadata for document {document_id}")
            
            # Get document details
            document = await self._get_document(tenant_id, document_id)
            if not document:
                raise ValueError(f"Document not found: {document_id}")
            
            # Download document content if needed
            content = await self._download_document_content(document)
            
            # Extract basic metadata
            basic_metadata = self._extract_basic_metadata(document, content)
            
            # Perform content analysis
            content_analysis = await self._analyze_document_content(content, document['file_extension'])
            
            # Extract compliance-related information
            compliance_metadata = await self._extract_compliance_metadata(content, document)
            
            # Combine all metadata
            extracted_metadata = {
                **basic_metadata,
                **content_analysis,
                **compliance_metadata,
                'extraction_date': datetime.utcnow().isoformat(),
                'extraction_version': '1.0'
            }
            
            # Update document with extracted metadata
            await self._update_document_metadata(document_id, extracted_metadata)
            
            logger.info(f"Metadata extraction completed for document {document_id}")
            
            return extracted_metadata
            
        except Exception as e:
            logger.error(f"Metadata extraction failed for document {document_id}: {str(e)}")
            raise
    
    async def _get_enabled_repositories(self, tenant_id: str, repository_type: str = None) -> List[Dict[str, Any]]:
        """Get enabled document repositories for tenant."""
        try:
            query = self.supabase.table('document_repositories').select('*').eq('tenant_id', tenant_id).eq('status', 'active')
            
            if repository_type:
                query = query.eq('repository_type', repository_type)
            
            result = query.execute()
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error fetching enabled repositories: {str(e)}")
            return []
    
    async def _get_document(self, tenant_id: str, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document details."""
        try:
            result = self.supabase.table('document_lifecycle').select('*').eq('tenant_id', tenant_id).eq('id', document_id).execute()
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Error fetching document: {str(e)}")
            return None
    
    async def _execute_lifecycle_action(self, document: Dict[str, Any], action: str) -> Dict[str, Any]:
        """Execute document lifecycle action."""
        current_stage = document.get('lifecycle_stage', 'creation')
        
        action_map = {
            'submit_for_review': {
                'valid_from': ['creation', 'requires_revision'],
                'next_stage': 'review',
                'approval_status': 'pending'
            },
            'approve': {
                'valid_from': ['review'],
                'next_stage': 'publication',
                'approval_status': 'approved'
            },
            'reject': {
                'valid_from': ['review'],
                'next_stage': 'requires_revision',
                'approval_status': 'rejected'
            },
            'archive': {
                'valid_from': ['publication', 'maintenance'],
                'next_stage': 'archived',
                'approval_status': 'approved'
            },
            'delete': {
                'valid_from': ['archived'],
                'next_stage': 'deleted',
                'approval_status': 'approved'
            }
        }
        
        action_config = action_map.get(action)
        if not action_config:
            raise ValueError(f"Invalid action: {action}")
        
        if current_stage not in action_config['valid_from']:
            raise ValueError(f"Cannot perform {action} from stage {current_stage}")
        
        return {
            'action': action,
            'previous_stage': current_stage,
            'next_stage': action_config['next_stage'],
            'approval_status': action_config['approval_status'],
            'executed_at': datetime.utcnow().isoformat(),
            'executed_by': 'system'  # Would be actual user in production
        }
    
    async def _update_document_lifecycle_stage(self, document_id: str, action: str, 
                                             action_results: Dict[str, Any]):
        """Update document lifecycle stage."""
        try:
            update_data = {
                'lifecycle_stage': action_results['next_stage'],
                'approval_status': action_results['approval_status'],
                'updated_at': datetime.utcnow().isoformat()
            }
            
            self.supabase.table('document_lifecycle').update(update_data).eq('id', document_id).execute()
            
        except Exception as e:
            logger.error(f"Error updating document lifecycle stage: {str(e)}")
    
    async def _download_document_content(self, document: Dict[str, Any]) -> bytes:
        """Download document content for analysis."""
        # Mock implementation - would download from actual repository
        return b"Mock document content for analysis"
    
    def _extract_basic_metadata(self, document: Dict[str, Any], content: bytes) -> Dict[str, Any]:
        """Extract basic document metadata."""
        return {
            'file_size_bytes': len(content),
            'content_hash': hashlib.md5(content).hexdigest(),
            'mime_type': mimetypes.guess_type(document.get('document_name', ''))[0],
            'word_count': len(content.decode('utf-8', errors='ignore').split()) if content else 0,
            'page_count': 1,  # Mock - would use actual document parsing
            'creation_method': 'upload'
        }
    
    async def _analyze_document_content(self, content: bytes, file_extension: str) -> Dict[str, Any]:
        """Analyze document content for classification and insights."""
        # Mock content analysis - would use actual NLP/ML models
        return {
            'document_type': 'policy',
            'document_category': 'compliance',
            'language': 'en',
            'confidence_score': 0.85,
            'key_topics': ['compliance', 'risk management', 'audit'],
            'entities_found': ['regulatory requirement', 'audit trail'],
            'sensitivity_level': 'internal',
            'contains_pii': False,
            'requires_encryption': True
        }
    
    async def _extract_compliance_metadata(self, content: bytes, document: Dict[str, Any]) -> Dict[str, Any]:
        """Extract compliance-related metadata."""
        # Mock compliance analysis
        return {
            'regulatory_frameworks': ['SOX', 'GDPR'],
            'compliance_requirements': ['data retention', 'audit trail'],
            'risk_level': 'medium',
            'retention_period_years': 7,
            'requires_approval': True,
            'approval_workflow': 'standard_compliance',
            'access_restrictions': ['compliance_officer', 'legal_team']
        }
    
    async def _update_document_metadata(self, document_id: str, metadata: Dict[str, Any]):
        """Update document with extracted metadata."""
        try:
            update_data = {
                'metadata_extracted': metadata,
                'document_type': metadata.get('document_type'),
                'document_category': metadata.get('document_category'),
                'compliance_tags': metadata.get('regulatory_frameworks', []),
                'retention_period_years': metadata.get('retention_period_years'),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            self.supabase.table('document_lifecycle').update(update_data).eq('id', document_id).execute()
            
        except Exception as e:
            logger.error(f"Error updating document metadata: {str(e)}")
    
    async def _send_lifecycle_notifications(self, document: Dict[str, Any], action: str, 
                                          action_results: Dict[str, Any]):
        """Send notifications for lifecycle actions."""
        # Mock notification logic
        logger.info(f"Notification: Document {document['document_name']} -> {action}")
    
    async def _update_repository_sync_time(self, repository_id: str, sync_results: Dict[str, Any]):
        """Update repository last sync time."""
        try:
            now = datetime.utcnow()
            self.supabase.table('document_repositories').update({
                'last_sync_at': now.isoformat(),
                'next_sync_at': (now + timedelta(hours=1)).isoformat(),
                'total_documents': sync_results.get('total_documents', 0),
                'storage_used_gb': sync_results.get('storage_used_gb', 0.0)
            }).eq('id', repository_id).execute()
            
        except Exception as e:
            logger.error(f"Error updating repository sync time: {str(e)}")
    
    async def _log_integration_operation(self, tenant_id: str, operation_type: str, 
                                       operation_name: str, status: str, 
                                       result: Dict[str, Any], system_id: str = None):
        """Log integration operation."""
        try:
            log_entry = {
                'id': str(uuid.uuid4()),
                'tenant_id': tenant_id,
                'integration_system_id': system_id,
                'operation_type': operation_type,
                'operation_name': operation_name,
                'status': status,
                'response_body': result,
                'records_processed': result.get('total_documents_processed', 0),
                'records_successful': result.get('documents_created', 0) + result.get('documents_updated', 0),
                'records_failed': len(result.get('errors', [])),
                'business_context': {
                    'component': 'document_management_integration',
                    'operation': operation_name
                }
            }
            
            self.supabase.table('integration_logs').insert(log_entry).execute()
            
        except Exception as e:
            logger.error(f"Error logging integration operation: {str(e)}")


class SharePointConnector:
    """Microsoft SharePoint connector."""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def sync_documents(self, repository_config: Dict[str, Any]) -> Dict[str, Any]:
        """Sync documents from SharePoint."""
        try:
            # Mock implementation - would call SharePoint Graph API
            logger.info(f"Syncing SharePoint documents from {repository_config['base_url']}")
            
            # Simulate document sync
            documents = [
                {
                    'id': 'SP-DOC-001',
                    'name': 'Compliance Policy v2.1.docx',
                    'path': '/Compliance/Policies/',
                    'size': 1024000,
                    'modified': '2024-01-15T09:00:00Z',
                    'type': 'policy'
                }
            ]
            
            created = updated = archived = 0
            metadata_extracted = compliance_tagged = 0
            
            for doc in documents:
                # Process document
                created += 1
                metadata_extracted += 1
                compliance_tagged += 1
            
            return {
                'total_processed': len(documents),
                'created': created,
                'updated': updated,
                'archived': archived,
                'metadata_extracted': metadata_extracted,
                'compliance_tagged': compliance_tagged,
                'total_documents': 150,
                'storage_used_gb': 2.5
            }
            
        except Exception as e:
            logger.error(f"SharePoint sync error: {str(e)}")
            raise


class BoxConnector:
    """Box Enterprise connector."""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def sync_documents(self, repository_config: Dict[str, Any]) -> Dict[str, Any]:
        """Sync documents from Box."""
        # Mock implementation
        return {
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'archived': 0,
            'metadata_extracted': 0,
            'compliance_tagged': 0,
            'total_documents': 0,
            'storage_used_gb': 0.0
        }


class GoogleDriveConnector:
    """Google Drive/Workspace connector."""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def sync_documents(self, repository_config: Dict[str, Any]) -> Dict[str, Any]:
        """Sync documents from Google Drive."""
        # Mock implementation
        return {
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'archived': 0,
            'metadata_extracted': 0,
            'compliance_tagged': 0,
            'total_documents': 0,
            'storage_used_gb': 0.0
        }


class AWSS3Connector:
    """AWS S3 connector."""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def sync_documents(self, repository_config: Dict[str, Any]) -> Dict[str, Any]:
        """Sync documents from AWS S3."""
        # Mock implementation
        return {
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'archived': 0,
            'metadata_extracted': 0,
            'compliance_tagged': 0,
            'total_documents': 0,
            'storage_used_gb': 0.0
        }


class AzureBlobConnector:
    """Azure Blob Storage connector."""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def sync_documents(self, repository_config: Dict[str, Any]) -> Dict[str, Any]:
        """Sync documents from Azure Blob Storage."""
        # Mock implementation
        return {
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'archived': 0,
            'metadata_extracted': 0,
            'compliance_tagged': 0,
            'total_documents': 0,
            'storage_used_gb': 0.0
        } 