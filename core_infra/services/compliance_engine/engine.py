"""
Compliance Engine Service
Real-time AML/KYC monitoring and compliance assessment
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any
import structlog
from core_infra.config import get_settings
from core_infra.database.connection import get_database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger(__name__)

class ComplianceEngine:
    """Main compliance engine service for AML/KYC monitoring"""
    
    def __init__(self):
        self.aml_enabled = os.getenv('AML_MONITORING_ENABLED', 'true').lower() == 'true'
        self.real_time_monitoring = os.getenv('TRANSACTION_MONITORING_REAL_TIME', 'true').lower() == 'true'
        
    async def start_monitoring(self):
        """Start the compliance monitoring service"""
        logger.info("Starting Compliance Engine...")
        logger.info(f"AML Monitoring: {'Enabled' if self.aml_enabled else 'Disabled'}")
        logger.info(f"Real-time Monitoring: {'Enabled' if self.real_time_monitoring else 'Disabled'}")
        
        # Start monitoring loops
        await asyncio.gather(
            self.transaction_monitor(),
            self.kyc_monitor(),
            self.risk_assessment_monitor()
        )
    
    async def transaction_monitor(self):
        """Monitor transactions for suspicious activity"""
        while True:
            try:
                logger.info("Running transaction monitoring cycle...")
                await self._process_transaction_monitoring()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in transaction monitoring: {e}")
                await asyncio.sleep(10)

    async def _process_transaction_monitoring(self):
        """Process transaction monitoring logic."""
        try:
            async with get_database() as db:
                # Get unprocessed transactions from the last hour
                query = """
                    SELECT t.*, c.risk_score, c.pep_status, c.sanctions_status
                    FROM transactions t
                    JOIN customers c ON t.customer_id = c.id
                    WHERE t.created_at >= NOW() - INTERVAL '1 hour'
                    AND t.monitoring_status = 'pending'
                    ORDER BY t.amount DESC
                    LIMIT 1000
                """

                transactions = await db.fetch(query)

                for transaction in transactions:
                    await self._analyze_transaction(db, transaction)

                logger.info(f"Processed {len(transactions)} transactions for monitoring")

        except Exception as e:
            logger.error(f"Transaction monitoring processing failed: {e}")
            raise

    async def _analyze_transaction(self, db, transaction):
        """Analyze individual transaction for suspicious activity."""
        try:
            suspicious_indicators = []
            risk_score = 0

            # High amount threshold check
            if transaction['amount'] > 10000:
                suspicious_indicators.append("HIGH_AMOUNT")
                risk_score += 30

            # Velocity check - multiple transactions in short time
            velocity_query = """
                SELECT COUNT(*) as count, SUM(amount) as total_amount
                FROM transactions
                WHERE customer_id = $1
                AND created_at >= NOW() - INTERVAL '24 hours'
                AND id != $2
            """
            velocity_result = await db.fetchrow(
                velocity_query,
                transaction['customer_id'],
                transaction['id']
            )

            if velocity_result['count'] > 5:
                suspicious_indicators.append("HIGH_VELOCITY")
                risk_score += 25

            if velocity_result['total_amount'] > 50000:
                suspicious_indicators.append("HIGH_DAILY_VOLUME")
                risk_score += 20

            # Round amount check (potential structuring)
            if transaction['amount'] % 1000 == 0 and transaction['amount'] < 10000:
                suspicious_indicators.append("ROUND_AMOUNT_STRUCTURING")
                risk_score += 15

            # Cross-border transaction check
            if transaction['destination_country'] != transaction['source_country']:
                suspicious_indicators.append("CROSS_BORDER")
                risk_score += 10

                # High-risk jurisdiction check
                high_risk_countries = ['AF', 'IR', 'KP', 'SY']  # Example list
                if (transaction['destination_country'] in high_risk_countries or
                    transaction['source_country'] in high_risk_countries):
                    suspicious_indicators.append("HIGH_RISK_JURISDICTION")
                    risk_score += 40

            # Customer risk factors
            if transaction['risk_score'] > 70:
                suspicious_indicators.append("HIGH_RISK_CUSTOMER")
                risk_score += transaction['risk_score'] // 10

            if transaction['pep_status']:
                suspicious_indicators.append("PEP_CUSTOMER")
                risk_score += 20

            if transaction['sanctions_status']:
                suspicious_indicators.append("SANCTIONS_MATCH")
                risk_score += 100  # Immediate escalation

            # Cash transaction patterns
            if transaction['transaction_type'] == 'cash_deposit' and transaction['amount'] > 5000:
                suspicious_indicators.append("LARGE_CASH_DEPOSIT")
                risk_score += 25

            # Determine monitoring status
            if risk_score >= 80:
                monitoring_status = 'high_risk'
                requires_sar = True
            elif risk_score >= 50:
                monitoring_status = 'medium_risk'
                requires_sar = False
            elif risk_score >= 20:
                monitoring_status = 'low_risk'
                requires_sar = False
            else:
                monitoring_status = 'cleared'
                requires_sar = False

            # Update transaction monitoring status
            await db.execute(
                """
                UPDATE transactions
                SET monitoring_status = $1,
                    risk_score = $2,
                    suspicious_indicators = $3,
                    requires_sar = $4,
                    monitored_at = NOW()
                WHERE id = $5
                """,
                monitoring_status,
                risk_score,
                suspicious_indicators,
                requires_sar,
                transaction['id']
            )

            # Create alert if high risk
            if monitoring_status in ['high_risk', 'medium_risk']:
                await self._create_transaction_alert(db, transaction, risk_score, suspicious_indicators)

            # Auto-generate SAR if required
            if requires_sar:
                await self._generate_sar(db, transaction, suspicious_indicators)

        except Exception as e:
            logger.error(f"Transaction analysis failed for transaction {transaction['id']}: {e}")
            # Mark as failed for retry
            await db.execute(
                "UPDATE transactions SET monitoring_status = 'failed' WHERE id = $1",
                transaction['id']
            )

    async def _create_transaction_alert(self, db, transaction, risk_score, indicators):
        """Create alert for suspicious transaction."""
        try:
            alert_id = uuid.uuid4()
            await db.execute(
                """
                INSERT INTO alerts (
                    id, tenant_id, alert_type, severity, title, description,
                    entity_type, entity_id, metadata, status, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
                """,
                alert_id,
                transaction['tenant_id'],
                'aml_transaction',
                'high' if risk_score >= 80 else 'medium',
                f"Suspicious Transaction Alert - ${transaction['amount']:,.2f}",
                f"Transaction {transaction['id']} flagged with risk score {risk_score}",
                'transaction',
                transaction['id'],
                {
                    'risk_score': risk_score,
                    'indicators': indicators,
                    'amount': float(transaction['amount']),
                    'customer_id': str(transaction['customer_id'])
                },
                'open'
            )

            logger.info(f"Created alert {alert_id} for transaction {transaction['id']}")

        except Exception as e:
            logger.error(f"Failed to create transaction alert: {e}")

    async def _generate_sar(self, db, transaction, indicators):
        """Generate Suspicious Activity Report."""
        try:
            sar_id = uuid.uuid4()
            await db.execute(
                """
                INSERT INTO suspicious_activity_reports (
                    id, tenant_id, customer_id, transaction_id, report_type,
                    suspicious_activity_description, indicators, amount,
                    status, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                """,
                sar_id,
                transaction['tenant_id'],
                transaction['customer_id'],
                transaction['id'],
                'transaction_monitoring',
                f"Automated SAR generated for transaction with risk indicators: {', '.join(indicators)}",
                indicators,
                transaction['amount'],
                'draft'
            )

            logger.info(f"Generated SAR {sar_id} for transaction {transaction['id']}")

        except Exception as e:
            logger.error(f"Failed to generate SAR: {e}")
    
    async def kyc_monitor(self):
        """Monitor KYC compliance status"""
        while True:
            try:
                logger.info("Running KYC monitoring cycle...")
                await self._process_kyc_monitoring()
                await asyncio.sleep(300)  # Check every 5 minutes
            except Exception as e:
                logger.error(f"Error in KYC monitoring: {e}")
                await asyncio.sleep(30)

    async def _process_kyc_monitoring(self):
        """Process KYC compliance monitoring."""
        try:
            async with get_database() as db:
                # Get customers requiring KYC review
                query = """
                    SELECT c.*,
                           COALESCE(cd.document_count, 0) as document_count,
                           COALESCE(cd.verified_count, 0) as verified_count,
                           EXTRACT(DAYS FROM NOW() - c.created_at) as days_since_creation,
                           EXTRACT(DAYS FROM NOW() - c.last_kyc_review) as days_since_review
                    FROM customers c
                    LEFT JOIN (
                        SELECT customer_id,
                               COUNT(*) as document_count,
                               COUNT(CASE WHEN verification_status = 'verified' THEN 1 END) as verified_count
                        FROM customer_documents
                        GROUP BY customer_id
                    ) cd ON c.id = cd.customer_id
                    WHERE c.kyc_status IN ('pending', 'incomplete', 'expired')
                    OR (c.last_kyc_review IS NULL AND c.created_at < NOW() - INTERVAL '7 days')
                    OR (c.last_kyc_review < NOW() - INTERVAL '1 year')
                    ORDER BY c.risk_score DESC, c.created_at ASC
                    LIMIT 500
                """

                customers = await db.fetch(query)

                for customer in customers:
                    await self._assess_kyc_compliance(db, customer)

                logger.info(f"Processed {len(customers)} customers for KYC monitoring")

        except Exception as e:
            logger.error(f"KYC monitoring processing failed: {e}")
            raise

    async def _assess_kyc_compliance(self, db, customer):
        """Assess individual customer KYC compliance."""
        try:
            compliance_issues = []
            kyc_score = 100  # Start with perfect score, deduct for issues

            # Required documents check
            required_docs = ['identity_document', 'proof_of_address', 'source_of_funds']
            if customer['customer_type'] == 'business':
                required_docs.extend(['business_registration', 'beneficial_ownership'])

            missing_docs = []
            for doc_type in required_docs:
                doc_check = await db.fetchrow(
                    """
                    SELECT id FROM customer_documents
                    WHERE customer_id = $1 AND document_type = $2
                    AND verification_status = 'verified'
                    """,
                    customer['id'], doc_type
                )

                if not doc_check:
                    missing_docs.append(doc_type)
                    kyc_score -= 20

            if missing_docs:
                compliance_issues.append(f"Missing documents: {', '.join(missing_docs)}")

            # Document expiry check
            expired_docs = await db.fetch(
                """
                SELECT document_type FROM customer_documents
                WHERE customer_id = $1
                AND expiry_date < NOW()
                AND verification_status = 'verified'
                """,
                customer['id']
            )

            if expired_docs:
                expired_types = [doc['document_type'] for doc in expired_docs]
                compliance_issues.append(f"Expired documents: {', '.join(expired_types)}")
                kyc_score -= len(expired_docs) * 15

            # Sanctions screening check
            if not customer['sanctions_checked_at'] or customer['sanctions_checked_at'] < datetime.utcnow() - timedelta(days=30):
                compliance_issues.append("Sanctions screening overdue")
                kyc_score -= 25

                # Trigger sanctions screening
                await self._trigger_sanctions_screening(db, customer)

            # PEP screening check
            if not customer['pep_checked_at'] or customer['pep_checked_at'] < datetime.utcnow() - timedelta(days=90):
                compliance_issues.append("PEP screening overdue")
                kyc_score -= 15

                # Trigger PEP screening
                await self._trigger_pep_screening(db, customer)

            # Enhanced due diligence for high-risk customers
            if customer['risk_score'] > 70:
                edd_check = await db.fetchrow(
                    """
                    SELECT id FROM customer_documents
                    WHERE customer_id = $1 AND document_type = 'enhanced_due_diligence'
                    AND verification_status = 'verified'
                    AND created_at > NOW() - INTERVAL '6 months'
                    """,
                    customer['id']
                )

                if not edd_check:
                    compliance_issues.append("Enhanced due diligence required")
                    kyc_score -= 30

            # Business customer specific checks
            if customer['customer_type'] == 'business':
                # Beneficial ownership check
                bo_check = await db.fetchrow(
                    """
                    SELECT COUNT(*) as count FROM beneficial_owners
                    WHERE customer_id = $1 AND ownership_percentage >= 25
                    """,
                    customer['id']
                )

                if bo_check['count'] == 0:
                    compliance_issues.append("Beneficial ownership not identified")
                    kyc_score -= 25

            # Determine KYC status
            if kyc_score >= 90 and not compliance_issues:
                kyc_status = 'compliant'
            elif kyc_score >= 70:
                kyc_status = 'minor_issues'
            elif kyc_score >= 50:
                kyc_status = 'incomplete'
            else:
                kyc_status = 'non_compliant'

            # Update customer KYC status
            await db.execute(
                """
                UPDATE customers
                SET kyc_status = $1,
                    kyc_score = $2,
                    kyc_issues = $3,
                    last_kyc_review = NOW(),
                    updated_at = NOW()
                WHERE id = $4
                """,
                kyc_status,
                kyc_score,
                compliance_issues,
                customer['id']
            )

            # Create alerts for non-compliant customers
            if kyc_status in ['incomplete', 'non_compliant']:
                await self._create_kyc_alert(db, customer, kyc_status, compliance_issues)

            # Auto-suspend high-risk non-compliant customers
            if kyc_status == 'non_compliant' and customer['risk_score'] > 80:
                await self._suspend_customer(db, customer, "KYC non-compliance")

        except Exception as e:
            logger.error(f"KYC assessment failed for customer {customer['id']}: {e}")

    async def _trigger_sanctions_screening(self, db, customer):
        """Trigger sanctions screening for customer."""
        try:
            # Create screening task
            task_id = uuid.uuid4()
            await db.execute(
                """
                INSERT INTO screening_tasks (
                    id, tenant_id, customer_id, screening_type, status,
                    entity_name, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
                """,
                task_id,
                customer['tenant_id'],
                customer['id'],
                'sanctions',
                'pending',
                f"{customer['first_name']} {customer['last_name']}"
            )

            logger.info(f"Triggered sanctions screening for customer {customer['id']}")

        except Exception as e:
            logger.error(f"Failed to trigger sanctions screening: {e}")

    async def _trigger_pep_screening(self, db, customer):
        """Trigger PEP screening for customer."""
        try:
            # Create screening task
            task_id = uuid.uuid4()
            await db.execute(
                """
                INSERT INTO screening_tasks (
                    id, tenant_id, customer_id, screening_type, status,
                    entity_name, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
                """,
                task_id,
                customer['tenant_id'],
                customer['id'],
                'pep',
                'pending',
                f"{customer['first_name']} {customer['last_name']}"
            )

            logger.info(f"Triggered PEP screening for customer {customer['id']}")

        except Exception as e:
            logger.error(f"Failed to trigger PEP screening: {e}")

    async def _create_kyc_alert(self, db, customer, kyc_status, issues):
        """Create alert for KYC compliance issues."""
        try:
            alert_id = uuid.uuid4()
            severity = 'high' if kyc_status == 'non_compliant' else 'medium'

            await db.execute(
                """
                INSERT INTO alerts (
                    id, tenant_id, alert_type, severity, title, description,
                    entity_type, entity_id, metadata, status, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
                """,
                alert_id,
                customer['tenant_id'],
                'kyc_compliance',
                severity,
                f"KYC Compliance Issue - {customer['first_name']} {customer['last_name']}",
                f"Customer KYC status: {kyc_status}. Issues: {'; '.join(issues)}",
                'customer',
                customer['id'],
                {
                    'kyc_status': kyc_status,
                    'issues': issues,
                    'customer_name': f"{customer['first_name']} {customer['last_name']}"
                },
                'open'
            )

            logger.info(f"Created KYC alert {alert_id} for customer {customer['id']}")

        except Exception as e:
            logger.error(f"Failed to create KYC alert: {e}")

    async def _suspend_customer(self, db, customer, reason):
        """Suspend customer account for compliance reasons."""
        try:
            await db.execute(
                """
                UPDATE customers
                SET status = 'suspended',
                    suspension_reason = $1,
                    suspended_at = NOW(),
                    updated_at = NOW()
                WHERE id = $2
                """,
                reason,
                customer['id']
            )

            # Log suspension
            logger.warning(f"Customer {customer['id']} suspended: {reason}")

        except Exception as e:
            logger.error(f"Failed to suspend customer: {e}")
    
    async def risk_assessment_monitor(self):
        """Continuous risk assessment"""
        while True:
            try:
                logger.info("Running risk assessment cycle...")
                await self._process_risk_assessment()
                await asyncio.sleep(600)  # Check every 10 minutes
            except Exception as e:
                logger.error(f"Error in risk assessment: {e}")
                await asyncio.sleep(60)

    async def _process_risk_assessment(self):
        """Process risk assessment for customers and transactions."""
        try:
            async with get_database() as db:
                # Get customers requiring risk reassessment
                query = """
                    SELECT c.*,
                           EXTRACT(DAYS FROM NOW() - c.last_risk_assessment) as days_since_assessment,
                           COALESCE(t.transaction_count, 0) as recent_transaction_count,
                           COALESCE(t.total_amount, 0) as recent_transaction_amount
                    FROM customers c
                    LEFT JOIN (
                        SELECT customer_id,
                               COUNT(*) as transaction_count,
                               SUM(amount) as total_amount
                        FROM transactions
                        WHERE created_at >= NOW() - INTERVAL '30 days'
                        GROUP BY customer_id
                    ) t ON c.id = t.customer_id
                    WHERE c.last_risk_assessment IS NULL
                    OR c.last_risk_assessment < NOW() - INTERVAL '90 days'
                    OR (c.risk_score > 70 AND c.last_risk_assessment < NOW() - INTERVAL '30 days')
                    ORDER BY c.risk_score DESC, c.last_risk_assessment ASC NULLS FIRST
                    LIMIT 200
                """

                customers = await db.fetch(query)

                for customer in customers:
                    await self._assess_customer_risk(db, customer)

                logger.info(f"Processed {len(customers)} customers for risk assessment")

        except Exception as e:
            logger.error(f"Risk assessment processing failed: {e}")
            raise

    async def _assess_customer_risk(self, db, customer):
        """Assess individual customer risk score."""
        try:
            risk_factors = {}
            risk_score = 0

            # Geographic risk factors
            high_risk_countries = ['AF', 'IR', 'KP', 'SY', 'MM', 'BY']  # Example high-risk countries
            medium_risk_countries = ['PK', 'BD', 'LK', 'NP']  # Example medium-risk countries

            if customer['country'] in high_risk_countries:
                risk_factors['geographic_risk'] = 'high'
                risk_score += 40
            elif customer['country'] in medium_risk_countries:
                risk_factors['geographic_risk'] = 'medium'
                risk_score += 20
            else:
                risk_factors['geographic_risk'] = 'low'
                risk_score += 5

            # Customer type risk
            if customer['customer_type'] == 'business':
                risk_score += 10
                risk_factors['customer_type_risk'] = 'business'

                # Industry risk
                high_risk_industries = ['money_services', 'gambling', 'precious_metals', 'art_dealers']
                medium_risk_industries = ['real_estate', 'legal_services', 'accounting']

                if customer['industry'] in high_risk_industries:
                    risk_factors['industry_risk'] = 'high'
                    risk_score += 30
                elif customer['industry'] in medium_risk_industries:
                    risk_factors['industry_risk'] = 'medium'
                    risk_score += 15
                else:
                    risk_factors['industry_risk'] = 'low'
                    risk_score += 5
            else:
                risk_factors['customer_type_risk'] = 'individual'
                risk_score += 5

            # PEP status
            if customer['pep_status']:
                risk_factors['pep_risk'] = 'high'
                risk_score += 35
            else:
                risk_factors['pep_risk'] = 'none'

            # Sanctions status
            if customer['sanctions_status']:
                risk_factors['sanctions_risk'] = 'match'
                risk_score += 100  # Maximum risk
            else:
                risk_factors['sanctions_risk'] = 'clear'

            # Transaction behavior analysis
            transaction_stats = await db.fetchrow(
                """
                SELECT
                    COUNT(*) as total_transactions,
                    AVG(amount) as avg_amount,
                    MAX(amount) as max_amount,
                    COUNT(DISTINCT destination_country) as country_count,
                    COUNT(CASE WHEN amount > 10000 THEN 1 END) as large_transactions
                FROM transactions
                WHERE customer_id = $1
                AND created_at >= NOW() - INTERVAL '6 months'
                """,
                customer['id']
            )

            if transaction_stats['total_transactions'] > 0:
                # High transaction volume
                if transaction_stats['total_transactions'] > 100:
                    risk_factors['transaction_volume'] = 'high'
                    risk_score += 15
                elif transaction_stats['total_transactions'] > 50:
                    risk_factors['transaction_volume'] = 'medium'
                    risk_score += 8
                else:
                    risk_factors['transaction_volume'] = 'low'
                    risk_score += 3

                # Large transaction amounts
                if transaction_stats['max_amount'] > 100000:
                    risk_factors['transaction_size'] = 'very_high'
                    risk_score += 25
                elif transaction_stats['max_amount'] > 50000:
                    risk_factors['transaction_size'] = 'high'
                    risk_score += 15
                elif transaction_stats['max_amount'] > 10000:
                    risk_factors['transaction_size'] = 'medium'
                    risk_score += 8
                else:
                    risk_factors['transaction_size'] = 'low'
                    risk_score += 3

                # Cross-border activity
                if transaction_stats['country_count'] > 5:
                    risk_factors['cross_border_activity'] = 'high'
                    risk_score += 20
                elif transaction_stats['country_count'] > 2:
                    risk_factors['cross_border_activity'] = 'medium'
                    risk_score += 10
                else:
                    risk_factors['cross_border_activity'] = 'low'
                    risk_score += 2

            # KYC compliance status
            if customer['kyc_status'] == 'non_compliant':
                risk_factors['kyc_compliance'] = 'non_compliant'
                risk_score += 30
            elif customer['kyc_status'] == 'incomplete':
                risk_factors['kyc_compliance'] = 'incomplete'
                risk_score += 15
            elif customer['kyc_status'] == 'minor_issues':
                risk_factors['kyc_compliance'] = 'minor_issues'
                risk_score += 5
            else:
                risk_factors['kyc_compliance'] = 'compliant'

            # Historical alerts and SARs
            alert_count = await db.fetchval(
                """
                SELECT COUNT(*) FROM alerts
                WHERE entity_type = 'customer' AND entity_id = $1
                AND created_at >= NOW() - INTERVAL '1 year'
                """,
                customer['id']
            )

            sar_count = await db.fetchval(
                """
                SELECT COUNT(*) FROM suspicious_activity_reports
                WHERE customer_id = $1
                AND created_at >= NOW() - INTERVAL '2 years'
                """,
                customer['id']
            )

            if sar_count > 0:
                risk_factors['sar_history'] = sar_count
                risk_score += sar_count * 20

            if alert_count > 5:
                risk_factors['alert_frequency'] = 'high'
                risk_score += 15
            elif alert_count > 2:
                risk_factors['alert_frequency'] = 'medium'
                risk_score += 8

            # Age of relationship
            days_since_onboarding = (datetime.utcnow() - customer['created_at']).days
            if days_since_onboarding < 30:
                risk_factors['relationship_age'] = 'new'
                risk_score += 10
            elif days_since_onboarding < 90:
                risk_factors['relationship_age'] = 'recent'
                risk_score += 5
            else:
                risk_factors['relationship_age'] = 'established'

            # Cap risk score at 100
            risk_score = min(risk_score, 100)

            # Determine risk category
            if risk_score >= 80:
                risk_category = 'high'
            elif risk_score >= 50:
                risk_category = 'medium'
            elif risk_score >= 20:
                risk_category = 'low'
            else:
                risk_category = 'minimal'

            # Update customer risk assessment
            await db.execute(
                """
                UPDATE customers
                SET risk_score = $1,
                    risk_category = $2,
                    risk_factors = $3,
                    last_risk_assessment = NOW(),
                    updated_at = NOW()
                WHERE id = $4
                """,
                risk_score,
                risk_category,
                risk_factors,
                customer['id']
            )

            # Create alert for high-risk customers
            if risk_category == 'high' and customer['risk_score'] < 80:
                await self._create_risk_alert(db, customer, risk_score, risk_factors)

            # Trigger enhanced monitoring for high-risk customers
            if risk_category == 'high':
                await self._enable_enhanced_monitoring(db, customer)

        except Exception as e:
            logger.error(f"Risk assessment failed for customer {customer['id']}: {e}")

    async def _create_risk_alert(self, db, customer, risk_score, risk_factors):
        """Create alert for high-risk customer."""
        try:
            alert_id = uuid.uuid4()
            await db.execute(
                """
                INSERT INTO alerts (
                    id, tenant_id, alert_type, severity, title, description,
                    entity_type, entity_id, metadata, status, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
                """,
                alert_id,
                customer['tenant_id'],
                'risk_assessment',
                'high',
                f"High Risk Customer - {customer['first_name']} {customer['last_name']}",
                f"Customer risk score increased to {risk_score}",
                'customer',
                customer['id'],
                {
                    'risk_score': risk_score,
                    'risk_factors': risk_factors,
                    'customer_name': f"{customer['first_name']} {customer['last_name']}"
                },
                'open'
            )

            logger.info(f"Created risk alert {alert_id} for customer {customer['id']}")

        except Exception as e:
            logger.error(f"Failed to create risk alert: {e}")

    async def _enable_enhanced_monitoring(self, db, customer):
        """Enable enhanced monitoring for high-risk customer."""
        try:
            await db.execute(
                """
                INSERT INTO enhanced_monitoring (
                    id, tenant_id, customer_id, monitoring_type, status,
                    start_date, review_date, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                ON CONFLICT (customer_id, monitoring_type)
                DO UPDATE SET
                    status = EXCLUDED.status,
                    review_date = EXCLUDED.review_date,
                    updated_at = NOW()
                """,
                uuid.uuid4(),
                customer['tenant_id'],
                customer['id'],
                'high_risk',
                'active',
                datetime.utcnow().date(),
                (datetime.utcnow() + timedelta(days=90)).date()
            )

            logger.info(f"Enabled enhanced monitoring for customer {customer['id']}")

        except Exception as e:
            logger.error(f"Failed to enable enhanced monitoring: {e}")

async def main():
    """Main entry point"""
    engine = ComplianceEngine()
    await engine.start_monitoring()

if __name__ == "__main__":
    asyncio.run(main()) 