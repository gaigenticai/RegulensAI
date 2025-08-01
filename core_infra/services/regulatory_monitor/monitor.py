"""
Regulatory Monitor - Main Monitoring Service
Real-time monitoring of regulatory changes from global financial authorities.
"""

import asyncio
import aiohttp
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import structlog
from urllib.parse import urljoin
import hashlib
import json

from core_infra.database.connection import get_database
from core_infra.services.monitoring import record_database_operation, track_operation
from core_infra.config import get_settings
from .processor import DocumentProcessor
from .analyzer import RegulatoryAnalyzer

logger = structlog.get_logger(__name__)
settings = get_settings()


@dataclass
class RegulatorySource:
    """Configuration for a regulatory data source."""
    id: str
    name: str
    type: str  # 'rss', 'api', 'web_scrape'
    url: str
    jurisdiction: str
    country_code: str
    update_frequency: int  # minutes
    api_key: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    selectors: Optional[Dict[str, str]] = None  # For web scraping
    is_active: bool = True


class RegulatoryMonitor:
    """
    Main regulatory monitoring service that tracks regulatory changes
    from multiple global sources in real-time.
    """
    
    def __init__(self):
        self.sources = self._initialize_sources()
        self.processor = DocumentProcessor()
        self.analyzer = RegulatoryAnalyzer()
        self.session: Optional[aiohttp.ClientSession] = None
        self.monitoring_tasks: List[asyncio.Task] = []
        self.is_running = False
        
    def _initialize_sources(self) -> List[RegulatorySource]:
        """Initialize regulatory data sources configuration."""
        return [
            # US Regulatory Sources
            RegulatorySource(
                id="sec_rss",
                name="SEC - Securities and Exchange Commission",
                type="rss",
                url="https://www.sec.gov/news/rss",
                jurisdiction="Federal",
                country_code="US",
                update_frequency=30
            ),
            RegulatorySource(
                id="fed_rss",
                name="Federal Reserve Board",
                type="rss", 
                url="https://www.federalreserve.gov/feeds/press_all.xml",
                jurisdiction="Federal",
                country_code="US",
                update_frequency=60
            ),
            RegulatorySource(
                id="fdic_rss",
                name="FDIC - Federal Deposit Insurance Corporation",
                type="rss",
                url="https://www.fdic.gov/news/rss",
                jurisdiction="Federal",
                country_code="US",
                update_frequency=60
            ),
            RegulatorySource(
                id="occ_rss",
                name="OCC - Office of the Comptroller of the Currency",
                type="rss",
                url="https://www.occ.gov/news-issuances/rss",
                jurisdiction="Federal",
                country_code="US",
                update_frequency=60
            ),
            RegulatorySource(
                id="fincen_rss",
                name="FinCEN - Financial Crimes Enforcement Network",
                type="rss",
                url="https://www.fincen.gov/news/rss",
                jurisdiction="Federal",
                country_code="US",
                update_frequency=120
            ),
            
            # UK Regulatory Sources
            RegulatorySource(
                id="fca_rss",
                name="FCA - Financial Conduct Authority",
                type="rss",
                url="https://www.fca.org.uk/news/rss",
                jurisdiction="UK",
                country_code="GB",
                update_frequency=60
            ),
            RegulatorySource(
                id="pra_rss",
                name="PRA - Prudential Regulation Authority",
                type="rss",
                url="https://www.bankofengland.co.uk/rss/prudential-regulation",
                jurisdiction="UK",
                country_code="GB",
                update_frequency=60
            ),
            
            # EU Regulatory Sources
            RegulatorySource(
                id="ecb_rss",
                name="ECB - European Central Bank",
                type="rss",
                url="https://www.ecb.europa.eu/rss/all.xml",
                jurisdiction="European Union",
                country_code="EU",
                update_frequency=120
            ),
            RegulatorySource(
                id="eba_rss",
                name="EBA - European Banking Authority",
                type="rss",
                url="https://www.eba.europa.eu/rss.xml",
                jurisdiction="European Union", 
                country_code="EU",
                update_frequency=120
            ),
            RegulatorySource(
                id="esma_rss",
                name="ESMA - European Securities and Markets Authority",
                type="rss",
                url="https://www.esma.europa.eu/rss.xml",
                jurisdiction="European Union",
                country_code="EU",
                update_frequency=120
            ),
            
            # International Sources
            RegulatorySource(
                id="bis_rss",
                name="BIS - Bank for International Settlements",
                type="rss",
                url="https://www.bis.org/doclist/press_releases.rss",
                jurisdiction="International",
                country_code="CH",
                update_frequency=240
            ),
            RegulatorySource(
                id="fsb_rss",
                name="FSB - Financial Stability Board",
                type="rss",
                url="https://www.fsb.org/feed/",
                jurisdiction="International",
                country_code="CH",
                update_frequency=360
            ),
            
            # Asia-Pacific Sources
            RegulatorySource(
                id="mas_rss",
                name="MAS - Monetary Authority of Singapore",
                type="rss",
                url="https://www.mas.gov.sg/rss/news-releases",
                jurisdiction="National",
                country_code="SG",
                update_frequency=120
            ),
            RegulatorySource(
                id="apra_rss",
                name="APRA - Australian Prudential Regulation Authority",
                type="rss",
                url="https://www.apra.gov.au/rss.xml",
                jurisdiction="Federal",
                country_code="AU",
                update_frequency=120
            ),
        ]
    
    async def start_monitoring(self):
        """Start the regulatory monitoring service."""
        if self.is_running:
            logger.warning("Regulatory monitoring is already running")
            return
            
        logger.info("Starting regulatory monitoring service")
        self.is_running = True
        
        # Create HTTP session
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        
        # Start monitoring tasks for each active source
        for source in self.sources:
            if source.is_active:
                task = asyncio.create_task(self._monitor_source(source))
                self.monitoring_tasks.append(task)
                logger.info(f"Started monitoring task for {source.name}")
        
        logger.info(f"Started monitoring {len(self.monitoring_tasks)} regulatory sources")
    
    async def stop_monitoring(self):
        """Stop the regulatory monitoring service."""
        if not self.is_running:
            return
            
        logger.info("Stopping regulatory monitoring service")
        self.is_running = False
        
        # Cancel all monitoring tasks
        for task in self.monitoring_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.monitoring_tasks:
            await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
        
        # Close HTTP session
        if self.session:
            await self.session.close()
            
        self.monitoring_tasks.clear()
        logger.info("Regulatory monitoring service stopped")
    
    @track_operation("regulatory_monitor.monitor_source")
    async def _monitor_source(self, source: RegulatorySource):
        """Monitor a single regulatory source continuously."""
        logger.info(f"Starting monitoring for {source.name}")
        
        while self.is_running:
            try:
                await self._check_source_updates(source)
                
                # Wait for the next check interval
                await asyncio.sleep(source.update_frequency * 60)
                
            except asyncio.CancelledError:
                logger.info(f"Monitoring cancelled for {source.name}")
                break
            except Exception as e:
                logger.error(f"Error monitoring {source.name}: {e}", exc_info=True)
                # Wait before retrying
                await asyncio.sleep(60)
    
    @track_operation("regulatory_monitor.check_source_updates")
    async def _check_source_updates(self, source: RegulatorySource):
        """Check for updates from a specific regulatory source."""
        try:
            logger.debug(f"Checking updates for {source.name}")
            
            if source.type == "rss":
                await self._process_rss_feed(source)
            elif source.type == "api":
                await self._process_api_source(source)
            elif source.type == "web_scrape":
                await self._process_web_scrape(source)
            else:
                logger.warning(f"Unknown source type: {source.type}")
                
        except Exception as e:
            logger.error(f"Failed to check updates for {source.name}: {e}")
            raise
    
    async def _process_rss_feed(self, source: RegulatorySource):
        """Process RSS feed from a regulatory source."""
        try:
            headers = source.headers or {
                'User-Agent': 'Regulens-AI-Compliance-Platform/1.0'
            }
            
            async with self.session.get(source.url, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} for {source.name}")
                    return
                
                content = await response.text()
                
            # Parse RSS feed
            feed = feedparser.parse(content)
            
            if feed.bozo:
                logger.warning(f"Malformed RSS feed for {source.name}: {feed.bozo_exception}")
            
            # Process each entry
            new_documents = 0
            for entry in feed.entries:
                if await self._process_feed_entry(source, entry):
                    new_documents += 1
            
            if new_documents > 0:
                logger.info(f"Processed {new_documents} new documents from {source.name}")
            
            # Update last monitored timestamp
            await self._update_source_timestamp(source.id)
            
        except Exception as e:
            logger.error(f"Error processing RSS feed for {source.name}: {e}")
            raise
    
    async def _process_feed_entry(self, source: RegulatorySource, entry) -> bool:
        """Process a single RSS feed entry."""
        try:
            # Extract document metadata
            document_data = {
                'source_id': await self._get_source_db_id(source.id),
                'document_number': getattr(entry, 'id', '') or self._generate_document_id(entry),
                'title': getattr(entry, 'title', 'Untitled'),
                'document_type': self._classify_document_type(entry),
                'status': 'published',
                'publication_date': self._parse_date(getattr(entry, 'published', '')),
                'summary': getattr(entry, 'summary', ''),
                'document_url': getattr(entry, 'link', ''),
                'topics': self._extract_topics(entry),
                'keywords': self._extract_keywords(entry)
            }
            
            # Check if document already exists
            if await self._document_exists(document_data['document_number'], source.id):
                return False
            
            # Download and process full document if available
            full_text = await self._download_document_content(document_data['document_url'])
            if full_text:
                document_data['full_text'] = full_text
            
            # Store document in database
            document_id = await self._store_document(document_data)
            
            # Trigger AI analysis
            await self._trigger_document_analysis(document_id, document_data)
            
            # Create regulatory change notification
            await self._create_change_notification(document_id, source, document_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing feed entry: {e}")
            return False
    
    async def _download_document_content(self, url: str) -> Optional[str]:
        """Download full document content from URL."""
        try:
            if not url:
                return None
                
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                
                content_type = response.headers.get('content-type', '').lower()
                
                if 'text/html' in content_type:
                    html_content = await response.text()
                    # Extract text from HTML using the processor
                    return await self.processor.extract_text_from_html(html_content)
                elif 'application/pdf' in content_type:
                    pdf_content = await response.read()
                    # Extract text from PDF using the processor
                    return await self.processor.extract_text_from_pdf(pdf_content)
                elif 'text/' in content_type:
                    return await response.text()
                
        except Exception as e:
            logger.warning(f"Failed to download document content from {url}: {e}")
            
        return None
    
    def _classify_document_type(self, entry) -> str:
        """Classify document type based on entry metadata."""
        title = getattr(entry, 'title', '').lower()
        summary = getattr(entry, 'summary', '').lower()
        content = f"{title} {summary}"
        
        # Classification rules
        if any(word in content for word in ['rule', 'regulation', 'final rule']):
            return 'regulation'
        elif any(word in content for word in ['guidance', 'advisory', 'interpretation']):
            return 'guidance'
        elif any(word in content for word in ['enforcement', 'penalty', 'fine', 'violation']):
            return 'enforcement'
        elif any(word in content for word in ['proposal', 'comment', 'draft']):
            return 'proposal'
        else:
            return 'announcement'
    
    def _extract_topics(self, entry) -> List[str]:
        """Extract topics/tags from feed entry."""
        topics = []
        
        # Extract from tags if available
        if hasattr(entry, 'tags'):
            topics.extend([tag.term for tag in entry.tags])
        
        # Extract from categories
        if hasattr(entry, 'category'):
            topics.append(entry.category)
        
        # Extract from title/summary using keywords
        content = f"{getattr(entry, 'title', '')} {getattr(entry, 'summary', '')}"
        financial_topics = self._identify_financial_topics(content)
        topics.extend(financial_topics)
        
        return list(set(topics))  # Remove duplicates
    
    def _identify_financial_topics(self, text: str) -> List[str]:
        """Identify financial topics from text content."""
        text_lower = text.lower()
        topics = []
        
        topic_keywords = {
            'banking': ['bank', 'banking', 'deposit', 'lending', 'credit'],
            'securities': ['securities', 'investment', 'trading', 'market'],
            'insurance': ['insurance', 'insurer', 'policy', 'coverage'],
            'aml': ['anti-money laundering', 'aml', 'suspicious activity', 'sar'],
            'kyc': ['know your customer', 'kyc', 'customer identification'],
            'cybersecurity': ['cyber', 'security', 'data breach', 'privacy'],
            'fintech': ['fintech', 'digital', 'cryptocurrency', 'blockchain'],
            'stress_testing': ['stress test', 'capital', 'liquidity'],
            'compliance': ['compliance', 'regulatory', 'examination']
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    def _extract_keywords(self, entry) -> List[str]:
        """Extract keywords from entry content."""
        # Simple keyword extraction - can be enhanced with NLP
        content = f"{getattr(entry, 'title', '')} {getattr(entry, 'summary', '')}"
        
        # Financial regulatory keywords
        keywords = []
        regulatory_terms = [
            'compliance', 'regulation', 'guidance', 'enforcement', 'penalty',
            'capital', 'liquidity', 'risk management', 'stress test',
            'anti-money laundering', 'know your customer', 'suspicious activity',
            'cybersecurity', 'data privacy', 'fintech', 'digital assets'
        ]
        
        for term in regulatory_terms:
            if term.lower() in content.lower():
                keywords.append(term)
        
        return keywords
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object."""
        if not date_str:
            return None
            
        try:
            # Try multiple date formats
            import dateutil.parser
            return dateutil.parser.parse(date_str)
        except:
            return None
    
    def _generate_document_id(self, entry) -> str:
        """Generate unique document ID from entry data."""
        content = f"{getattr(entry, 'title', '')}{getattr(entry, 'link', '')}{getattr(entry, 'published', '')}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def _get_source_db_id(self, source_id: str) -> str:
        """Get database ID for regulatory source."""
        async with get_database() as db:
            query = "SELECT id FROM regulatory_sources WHERE name = $1"
            result = await db.fetchrow(query, source_id)
            if result:
                return result['id']
            else:
                # Create source if it doesn't exist
                return await self._create_regulatory_source(source_id)
    
    async def _create_regulatory_source(self, source_id: str) -> str:
        """Create regulatory source in database."""
        source = next((s for s in self.sources if s.id == source_id), None)
        if not source:
            raise ValueError(f"Unknown source ID: {source_id}")
        
        async with get_database() as db:
            query = """
                INSERT INTO regulatory_sources (name, type, country_code, jurisdiction, website_url, monitoring_enabled)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """
            result = await db.fetchrow(
                query, source.name, source.type, source.country_code,
                source.jurisdiction, source.url, source.is_active
            )
            return result['id']
    
    async def _document_exists(self, document_number: str, source_id: str) -> bool:
        """Check if document already exists in database."""
        async with get_database() as db:
            query = """
                SELECT COUNT(*) as count FROM regulatory_documents rd
                JOIN regulatory_sources rs ON rd.source_id = rs.id
                WHERE rd.document_number = $1 AND rs.name = $2
            """
            result = await db.fetchrow(query, document_number, source_id)
            return result['count'] > 0
    
    async def _store_document(self, document_data: Dict[str, Any]) -> str:
        """Store regulatory document in database."""
        async with get_database() as db:
            query = """
                INSERT INTO regulatory_documents (
                    source_id, document_number, title, document_type, status,
                    publication_date, summary, full_text, document_url,
                    topics, keywords
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING id
            """
            result = await db.fetchrow(
                query,
                document_data['source_id'],
                document_data['document_number'],
                document_data['title'],
                document_data['document_type'],
                document_data['status'],
                document_data['publication_date'],
                document_data['summary'],
                document_data.get('full_text'),
                document_data['document_url'],
                json.dumps(document_data['topics']),
                json.dumps(document_data['keywords'])
            )
            return result['id']
    
    async def _trigger_document_analysis(self, document_id: str, document_data: Dict[str, Any]):
        """Trigger AI analysis of the regulatory document."""
        try:
            # Queue document for AI analysis
            await self.analyzer.analyze_document(document_id, document_data)
        except Exception as e:
            logger.error(f"Failed to trigger document analysis for {document_id}: {e}")
    
    async def _create_change_notification(self, document_id: str, source: RegulatorySource, document_data: Dict[str, Any]):
        """Create notification for regulatory change."""
        try:
            # Determine impact level
            impact_level = self._assess_document_impact(document_data)
            
            # Create notification record
            await self._store_change_notification(document_id, source, document_data, impact_level)
            
            # Send real-time notifications if high impact
            if impact_level in ['critical', 'high']:
                await self._send_real_time_notifications(document_id, document_data, impact_level)
                
        except Exception as e:
            logger.error(f"Failed to create change notification for {document_id}: {e}")
    
    def _assess_document_impact(self, document_data: Dict[str, Any]) -> str:
        """Assess the impact level of a regulatory document."""
        title = document_data.get('title', '').lower()
        doc_type = document_data.get('document_type', '')
        topics = document_data.get('topics', [])
        
        # High impact indicators
        high_impact_terms = [
            'final rule', 'emergency', 'immediate', 'enforcement action',
            'penalty', 'cease and desist', 'capital requirements'
        ]
        
        # Critical impact for enforcement actions
        if doc_type == 'enforcement' or any(term in title for term in ['penalty', 'enforcement', 'violation']):
            return 'critical'
        
        # High impact for final rules and regulations
        if doc_type == 'regulation' or any(term in title for term in high_impact_terms):
            return 'high'
        
        # Medium impact for guidance and proposals
        if doc_type in ['guidance', 'proposal']:
            return 'medium'
        
        # Low impact for general announcements
        return 'low'
    
    async def _store_change_notification(self, document_id: str, source: RegulatorySource, 
                                       document_data: Dict[str, Any], impact_level: str):
        """Store regulatory change notification in database."""
        async with get_database() as db:
            query = """
                INSERT INTO regulatory_notifications 
                (document_id, source_id, impact_level, details, created_at)
                VALUES ($1, $2, $3, $4, $5)
            """
            await db.execute(query, document_id, source.id, impact_level, document_data, datetime.utcnow())
    
    async def _send_real_time_notifications(self, document_id: str, 
                                          document_data: Dict[str, Any], impact_level: str):
        """Send real-time notifications for high-impact regulatory changes."""
        message = f"High-impact regulatory change: {document_data.get('title')} (Impact: {impact_level})"
        # Assuming notification_service is defined elsewhere or needs to be imported
        # For now, we'll just log the message as a placeholder
        logger.info(f"Sending real-time notification: {message}")
    
    async def _update_source_timestamp(self, source_id: str):
        """Update last monitored timestamp for source."""
        async with get_database() as db:
            query = """
                UPDATE regulatory_sources 
                SET last_monitored = $1 
                WHERE name = $2
            """
            await db.execute(query, datetime.utcnow(), source_id)
    
    async def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status and statistics."""
        status = {
            'is_running': self.is_running,
            'active_sources': len([s for s in self.sources if s.is_active]),
            'total_sources': len(self.sources),
            'monitoring_tasks': len(self.monitoring_tasks),
            'sources': []
        }
        
        for source in self.sources:
            source_status = {
                'id': source.id,
                'name': source.name,
                'jurisdiction': source.jurisdiction,
                'is_active': source.is_active,
                'update_frequency': source.update_frequency
            }
            
            # Get last update time from database
            try:
                async with get_database() as db:
                    query = "SELECT last_monitored FROM regulatory_sources WHERE name = $1"
                    result = await db.fetchrow(query, source.id)
                    if result:
                        source_status['last_monitored'] = result['last_monitored']
            except:
                pass
                
            status['sources'].append(source_status)
        
        return status


# Global instance
regulatory_monitor = RegulatoryMonitor()


async def start_monitoring():
    """Start the regulatory monitoring service."""
    await regulatory_monitor.start_monitoring()


async def stop_monitoring():
    """Stop the regulatory monitoring service."""
    await regulatory_monitor.stop_monitoring()


async def get_monitor_status():
    """Get monitoring status."""
    return await regulatory_monitor.get_monitoring_status() 