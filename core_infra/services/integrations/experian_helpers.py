"""
Experian Provider Helper Methods
Supporting functions for Experian credit bureau integration.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ExperianHelpers:
    """Helper methods for Experian integration."""
    
    @staticmethod
    def parse_credit_response(credit_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Experian credit response into standardized format."""
        try:
            parsed = {
                'status': 'success',
                'credit_score': None,
                'score_factors': [],
                'accounts': [],
                'inquiries': [],
                'public_records': [],
                'alerts': [],
                'summary': {}
            }
            
            # Extract credit score
            if 'riskModel' in credit_data:
                for model in credit_data['riskModel']:
                    if model.get('modelIndicator') == '7000':  # FICO Score 8
                        parsed['credit_score'] = model.get('score')
                        parsed['score_factors'] = model.get('scoreFactors', [])
                        break
            
            # Extract account information
            if 'tradeline' in credit_data:
                for account in credit_data['tradeline']:
                    account_info = {
                        'creditor_name': account.get('creditorName', ''),
                        'account_type': account.get('accountTypeDescription', ''),
                        'balance': account.get('currentBalance', 0),
                        'credit_limit': account.get('creditLimit', 0),
                        'payment_status': account.get('paymentStatus', ''),
                        'date_opened': account.get('dateOpened', ''),
                        'last_activity': account.get('dateLastActivity', ''),
                        'payment_history': account.get('paymentHistory', [])
                    }
                    parsed['accounts'].append(account_info)
            
            # Extract inquiries
            if 'inquiry' in credit_data:
                for inquiry in credit_data['inquiry']:
                    inquiry_info = {
                        'creditor_name': inquiry.get('subscriberName', ''),
                        'inquiry_date': inquiry.get('dateOfInquiry', ''),
                        'inquiry_type': inquiry.get('type', ''),
                        'industry_code': inquiry.get('industryCode', '')
                    }
                    parsed['inquiries'].append(inquiry_info)
            
            # Extract public records
            if 'publicRecord' in credit_data:
                for record in credit_data['publicRecord']:
                    record_info = {
                        'type': record.get('type', ''),
                        'status': record.get('status', ''),
                        'date_filed': record.get('dateFiled', ''),
                        'amount': record.get('amount', 0),
                        'court': record.get('court', ''),
                        'case_number': record.get('caseNumber', '')
                    }
                    parsed['public_records'].append(record_info)
            
            # Extract alerts and fraud indicators
            if 'alert' in credit_data:
                for alert in credit_data['alert']:
                    alert_info = {
                        'type': alert.get('type', ''),
                        'description': alert.get('description', ''),
                        'date': alert.get('date', '')
                    }
                    parsed['alerts'].append(alert_info)
            
            # Extract summary information
            if 'summary' in credit_data:
                summary = credit_data['summary']
                parsed['summary'] = {
                    'total_accounts': summary.get('totalAccounts', 0),
                    'open_accounts': summary.get('openAccounts', 0),
                    'closed_accounts': summary.get('closedAccounts', 0),
                    'total_balance': summary.get('totalBalance', 0),
                    'total_monthly_payment': summary.get('totalMonthlyPayment', 0),
                    'total_inquiries': summary.get('totalInquiries', 0),
                    'oldest_account_date': summary.get('oldestAccountDate', ''),
                    'newest_account_date': summary.get('newestAccountDate', '')
                }
            
            return parsed
            
        except Exception as e:
            logger.error(f"Error parsing Experian credit response: {e}")
            return {'status': 'error', 'error': str(e)}
    
    @staticmethod
    def parse_identity_response(identity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Experian identity verification response."""
        try:
            parsed = {
                'status': 'success',
                'identity_verified': False,
                'confidence_score': 0,
                'verification_results': {},
                'address_verification': {},
                'phone_verification': {},
                'ssn_verification': {},
                'risk_indicators': []
            }
            
            # Extract overall verification result
            if 'verificationResults' in identity_data:
                results = identity_data['verificationResults']
                parsed['identity_verified'] = results.get('verified', False)
                parsed['confidence_score'] = results.get('confidenceScore', 0)
                
                # Individual verification components
                parsed['verification_results'] = {
                    'name_match': results.get('nameMatch', ''),
                    'address_match': results.get('addressMatch', ''),
                    'ssn_match': results.get('ssnMatch', ''),
                    'phone_match': results.get('phoneMatch', ''),
                    'date_of_birth_match': results.get('dobMatch', '')
                }
            
            # Extract address verification details
            if 'addressVerification' in identity_data:
                addr_verify = identity_data['addressVerification']
                parsed['address_verification'] = {
                    'deliverable': addr_verify.get('deliverable', False),
                    'standardized_address': addr_verify.get('standardizedAddress', {}),
                    'address_type': addr_verify.get('addressType', ''),
                    'occupancy_status': addr_verify.get('occupancyStatus', ''),
                    'length_of_residence': addr_verify.get('lengthOfResidence', '')
                }
            
            # Extract phone verification
            if 'phoneVerification' in identity_data:
                phone_verify = identity_data['phoneVerification']
                parsed['phone_verification'] = {
                    'valid': phone_verify.get('valid', False),
                    'line_type': phone_verify.get('lineType', ''),
                    'carrier': phone_verify.get('carrier', ''),
                    'associated_with_address': phone_verify.get('associatedWithAddress', False)
                }
            
            # Extract SSN verification
            if 'ssnVerification' in identity_data:
                ssn_verify = identity_data['ssnVerification']
                parsed['ssn_verification'] = {
                    'valid': ssn_verify.get('valid', False),
                    'issued_state': ssn_verify.get('issuedState', ''),
                    'issued_date_range': ssn_verify.get('issuedDateRange', ''),
                    'deceased_indicator': ssn_verify.get('deceasedIndicator', False)
                }
            
            # Extract risk indicators
            if 'riskIndicators' in identity_data:
                for indicator in identity_data['riskIndicators']:
                    risk_info = {
                        'type': indicator.get('type', ''),
                        'description': indicator.get('description', ''),
                        'severity': indicator.get('severity', ''),
                        'score': indicator.get('score', 0)
                    }
                    parsed['risk_indicators'].append(risk_info)
            
            return parsed
            
        except Exception as e:
            logger.error(f"Error parsing Experian identity response: {e}")
            return {'status': 'error', 'error': str(e)}
    
    @staticmethod
    def calculate_experian_risk(results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall risk assessment from Experian results."""
        try:
            risk_assessment = {
                'overall_risk_score': 0.0,
                'risk_level': 'unknown',
                'risk_factors': [],
                'recommendations': []
            }
            
            risk_score = 0.0
            risk_factors = []
            
            # Credit profile risk factors
            if 'credit_profile' in results and results['credit_profile'].get('status') == 'success':
                credit = results['credit_profile']
                
                # Credit score impact
                credit_score = credit.get('credit_score')
                if credit_score:
                    if credit_score >= 750:
                        risk_score += 0.1  # Low risk
                    elif credit_score >= 650:
                        risk_score += 0.3  # Medium risk
                    else:
                        risk_score += 0.6  # High risk
                        risk_factors.append('Low credit score')
                
                # Public records
                public_records = credit.get('public_records', [])
                if public_records:
                    risk_score += 0.4
                    risk_factors.append(f'{len(public_records)} public record(s) found')
                
                # Recent inquiries
                inquiries = credit.get('inquiries', [])
                recent_inquiries = [inq for inq in inquiries if self._is_recent_inquiry(inq)]
                if len(recent_inquiries) > 3:
                    risk_score += 0.2
                    risk_factors.append('Multiple recent credit inquiries')
                
                # Alerts
                alerts = credit.get('alerts', [])
                if alerts:
                    risk_score += 0.3
                    risk_factors.append('Credit alerts present')
            
            # Identity verification risk factors
            if 'identity_verification' in results and results['identity_verification'].get('status') == 'success':
                identity = results['identity_verification']
                
                if not identity.get('identity_verified', False):
                    risk_score += 0.5
                    risk_factors.append('Identity verification failed')
                
                confidence_score = identity.get('confidence_score', 0)
                if confidence_score < 70:
                    risk_score += 0.3
                    risk_factors.append('Low identity confidence score')
                
                # Risk indicators
                risk_indicators = identity.get('risk_indicators', [])
                high_risk_indicators = [ri for ri in risk_indicators if ri.get('severity') == 'high']
                if high_risk_indicators:
                    risk_score += 0.4
                    risk_factors.append('High-risk identity indicators found')
            
            # Fraud detection risk factors
            if 'fraud_detection' in results and results['fraud_detection'].get('status') == 'success':
                fraud = results['fraud_detection']
                
                fraud_score = fraud.get('fraud_score', 0)
                if fraud_score > 70:
                    risk_score += 0.6
                    risk_factors.append('High fraud risk score')
                elif fraud_score > 40:
                    risk_score += 0.3
                    risk_factors.append('Moderate fraud risk score')
            
            # Normalize risk score (0-1 scale)
            risk_assessment['overall_risk_score'] = min(risk_score, 1.0)
            risk_assessment['risk_factors'] = risk_factors
            
            # Determine risk level
            if risk_score <= 0.3:
                risk_assessment['risk_level'] = 'low'
                risk_assessment['recommendations'] = ['Standard monitoring procedures']
            elif risk_score <= 0.6:
                risk_assessment['risk_level'] = 'medium'
                risk_assessment['recommendations'] = [
                    'Enhanced due diligence recommended',
                    'Additional documentation may be required'
                ]
            else:
                risk_assessment['risk_level'] = 'high'
                risk_assessment['recommendations'] = [
                    'Comprehensive review required',
                    'Consider additional verification steps',
                    'Escalate to compliance team'
                ]
            
            return risk_assessment
            
        except Exception as e:
            logger.error(f"Error calculating Experian risk assessment: {e}")
            return {
                'overall_risk_score': 0.5,
                'risk_level': 'unknown',
                'risk_factors': ['Error in risk calculation'],
                'recommendations': ['Manual review required']
            }
    
    @staticmethod
    def _is_recent_inquiry(inquiry: Dict[str, Any]) -> bool:
        """Check if inquiry is recent (within last 6 months)."""
        try:
            inquiry_date = datetime.strptime(inquiry.get('inquiry_date', ''), '%Y-%m-%d')
            months_ago = (datetime.now() - inquiry_date).days / 30
            return months_ago <= 6
        except:
            return False
