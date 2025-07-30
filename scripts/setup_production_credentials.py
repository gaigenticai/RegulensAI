#!/usr/bin/env python3
"""
Production credential setup script for RegulensAI.
Sets up secure credential management and external service accounts.
"""

import asyncio
import os
import sys
import json
import getpass
from pathlib import Path
from typing import Dict, Any, Optional
import structlog

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core_infra.services.security.credential_manager import CredentialManager
from core_infra.services.security.service_account_setup import ServiceAccountSetup

logger = structlog.get_logger(__name__)


class ProductionCredentialSetup:
    """
    Interactive setup for production credentials and external service accounts.
    """
    
    def __init__(self):
        self.credential_manager = CredentialManager()
        self.service_setup = ServiceAccountSetup()
    
    async def run_interactive_setup(self):
        """Run interactive credential setup."""
        print("=" * 60)
        print("RegulensAI Production Credential Setup")
        print("=" * 60)
        print()
        
        # Get tenant ID
        tenant_id = input("Enter tenant ID (UUID): ").strip()
        if not tenant_id:
            print("Error: Tenant ID is required")
            return
        
        print(f"Setting up credentials for tenant: {tenant_id}")
        print()
        
        # Setup menu
        while True:
            print("Available services to configure:")
            print("1. Experian (Credit & Identity Services)")
            print("2. Refinitiv (Market Data)")
            print("3. RSA Archer (GRC Platform)")
            print("4. ServiceNow (GRC & ITSM)")
            print("5. Twilio (Communications)")
            print("6. Core Banking Systems")
            print("7. Validate all existing credentials")
            print("8. List all credentials")
            print("9. Exit")
            print()
            
            choice = input("Select an option (1-9): ").strip()
            
            if choice == "1":
                await self._setup_experian(tenant_id)
            elif choice == "2":
                await self._setup_refinitiv(tenant_id)
            elif choice == "3":
                await self._setup_archer(tenant_id)
            elif choice == "4":
                await self._setup_servicenow(tenant_id)
            elif choice == "5":
                await self._setup_twilio(tenant_id)
            elif choice == "6":
                await self._setup_core_banking(tenant_id)
            elif choice == "7":
                await self._validate_all_credentials(tenant_id)
            elif choice == "8":
                await self._list_credentials(tenant_id)
            elif choice == "9":
                print("Exiting setup...")
                break
            else:
                print("Invalid choice. Please try again.")
            
            print()
    
    async def _setup_experian(self, tenant_id: str):
        """Setup Experian credentials."""
        print("\n--- Experian Setup ---")
        
        client_id = input("Enter Experian Client ID: ").strip()
        client_secret = getpass.getpass("Enter Experian Client Secret: ").strip()
        subscriber_code = input("Enter Subscriber Code: ").strip()
        sub_code = input("Enter Sub Code: ").strip()
        
        use_sandbox = input("Use sandbox environment? (y/n) [y]: ").strip().lower()
        use_sandbox = use_sandbox != 'n'
        
        print("Setting up Experian account...")
        
        async with self.service_setup:
            result = await self.service_setup.setup_experian_account(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
                subscriber_code=subscriber_code,
                sub_code=sub_code,
                use_sandbox=use_sandbox
            )
        
        if result['status'] == 'success':
            print(f"✅ Experian setup successful!")
            print(f"   Credential ID: {result['credential_id']}")
            print(f"   Environment: {result['environment']}")
            print(f"   Services: {', '.join(result['services_available'])}")
        else:
            print(f"❌ Experian setup failed: {result['error']}")
    
    async def _setup_refinitiv(self, tenant_id: str):
        """Setup Refinitiv credentials."""
        print("\n--- Refinitiv Setup ---")
        
        api_key = getpass.getpass("Enter Refinitiv API Key: ").strip()
        app_id = input("Enter Application ID: ").strip()
        username = input("Enter Username: ").strip()
        password = getpass.getpass("Enter Password: ").strip()
        
        print("Setting up Refinitiv account...")
        
        async with self.service_setup:
            result = await self.service_setup.setup_refinitiv_account(
                tenant_id=tenant_id,
                api_key=api_key,
                app_id=app_id,
                username=username,
                password=password
            )
        
        if result['status'] == 'success':
            print(f"✅ Refinitiv setup successful!")
            print(f"   Credential ID: {result['credential_id']}")
            print(f"   Data Access: {result['data_access_test']['status']}")
            print(f"   Services: {', '.join(result['services_available'])}")
        else:
            print(f"❌ Refinitiv setup failed: {result['error']}")
    
    async def _setup_archer(self, tenant_id: str):
        """Setup RSA Archer credentials."""
        print("\n--- RSA Archer Setup ---")
        
        base_url = input("Enter Archer Base URL: ").strip()
        username = input("Enter Username: ").strip()
        password = getpass.getpass("Enter Password: ").strip()
        instance_name = input("Enter Instance Name: ").strip()
        domain = input("Enter Domain (optional): ").strip()
        
        print("Setting up Archer account...")
        
        async with self.service_setup:
            result = await self.service_setup.setup_archer_account(
                tenant_id=tenant_id,
                base_url=base_url,
                username=username,
                password=password,
                instance_name=instance_name,
                domain=domain
            )
        
        if result['status'] == 'success':
            print(f"✅ Archer setup successful!")
            print(f"   Credential ID: {result['credential_id']}")
            print(f"   Applications Access: {result['applications_test']['status']}")
            print(f"   Services: {', '.join(result['services_available'])}")
        else:
            print(f"❌ Archer setup failed: {result['error']}")
    
    async def _setup_servicenow(self, tenant_id: str):
        """Setup ServiceNow credentials."""
        print("\n--- ServiceNow Setup ---")
        
        instance_url = input("Enter ServiceNow Instance URL: ").strip()
        username = input("Enter Username: ").strip()
        password = getpass.getpass("Enter Password: ").strip()
        
        print("Setting up ServiceNow account...")
        
        async with self.service_setup:
            result = await self.service_setup.setup_servicenow_account(
                tenant_id=tenant_id,
                instance_url=instance_url,
                username=username,
                password=password
            )
        
        if result['status'] == 'success':
            print(f"✅ ServiceNow setup successful!")
            print(f"   Credential ID: {result['credential_id']}")
            print(f"   GRC Access: {result['grc_access_test']['status']}")
            print(f"   Services: {', '.join(result['services_available'])}")
        else:
            print(f"❌ ServiceNow setup failed: {result['error']}")
    
    async def _setup_twilio(self, tenant_id: str):
        """Setup Twilio credentials."""
        print("\n--- Twilio Setup ---")
        
        account_sid = input("Enter Twilio Account SID: ").strip()
        auth_token = getpass.getpass("Enter Twilio Auth Token: ").strip()
        verify_service_sid = input("Enter Verify Service SID (optional): ").strip()
        
        credential_data = {
            'account_sid': account_sid,
            'auth_token': auth_token,
            'base_url': 'https://api.twilio.com'
        }
        
        if verify_service_sid:
            credential_data['verify_service_sid'] = verify_service_sid
        
        print("Storing Twilio credentials...")
        
        credential_id = await self.credential_manager.store_credential(
            tenant_id=tenant_id,
            service_name='twilio',
            credential_type='api_credentials',
            credential_data=credential_data,
            metadata={
                'services_available': ['sms', 'voice', 'verify'],
                'configured_at': '2024-01-29'
            }
        )
        
        print(f"✅ Twilio credentials stored!")
        print(f"   Credential ID: {credential_id}")
    
    async def _setup_core_banking(self, tenant_id: str):
        """Setup core banking system credentials."""
        print("\n--- Core Banking Systems Setup ---")
        print("1. Temenos T24")
        print("2. Oracle Flexcube")
        print("3. Infosys Finacle")
        
        choice = input("Select banking system (1-3): ").strip()
        
        if choice == "1":
            await self._setup_temenos(tenant_id)
        elif choice == "2":
            await self._setup_flexcube(tenant_id)
        elif choice == "3":
            await self._setup_finacle(tenant_id)
        else:
            print("Invalid choice.")
    
    async def _setup_temenos(self, tenant_id: str):
        """Setup Temenos T24 credentials."""
        print("\n--- Temenos T24 Setup ---")
        
        base_url = input("Enter T24 Base URL: ").strip()
        auth_type = input("Enter Auth Type (oauth/basic) [oauth]: ").strip() or "oauth"
        
        credential_data = {
            't24_base_url': base_url,
            't24_auth_type': auth_type
        }
        
        if auth_type == "oauth":
            client_id = input("Enter Client ID: ").strip()
            client_secret = getpass.getpass("Enter Client Secret: ").strip()
            credential_data.update({
                't24_client_id': client_id,
                't24_client_secret': client_secret
            })
        else:
            username = input("Enter Username: ").strip()
            password = getpass.getpass("Enter Password: ").strip()
            credential_data.update({
                't24_username': username,
                't24_password': password
            })
        
        credential_id = await self.credential_manager.store_credential(
            tenant_id=tenant_id,
            service_name='temenos_t24',
            credential_type='api_credentials',
            credential_data=credential_data,
            metadata={'banking_system': 'temenos_t24'}
        )
        
        print(f"✅ Temenos T24 credentials stored!")
        print(f"   Credential ID: {credential_id}")
    
    async def _setup_flexcube(self, tenant_id: str):
        """Setup Oracle Flexcube credentials."""
        print("\n--- Oracle Flexcube Setup ---")
        
        base_url = input("Enter Flexcube Base URL: ").strip()
        username = input("Enter Username: ").strip()
        password = getpass.getpass("Enter Password: ").strip()
        branch_code = input("Enter Branch Code: ").strip()
        
        credential_data = {
            'flexcube_base_url': base_url,
            'flexcube_username': username,
            'flexcube_password': password,
            'flexcube_branch_code': branch_code
        }
        
        credential_id = await self.credential_manager.store_credential(
            tenant_id=tenant_id,
            service_name='oracle_flexcube',
            credential_type='soap_credentials',
            credential_data=credential_data,
            metadata={'banking_system': 'oracle_flexcube'}
        )
        
        print(f"✅ Oracle Flexcube credentials stored!")
        print(f"   Credential ID: {credential_id}")
    
    async def _setup_finacle(self, tenant_id: str):
        """Setup Infosys Finacle credentials."""
        print("\n--- Infosys Finacle Setup ---")
        
        base_url = input("Enter Finacle Base URL: ").strip()
        username = input("Enter Username: ").strip()
        password = getpass.getpass("Enter Password: ").strip()
        branch_code = input("Enter Branch Code: ").strip()
        
        credential_data = {
            'finacle_base_url': base_url,
            'finacle_username': username,
            'finacle_password': password,
            'finacle_branch_code': branch_code
        }
        
        credential_id = await self.credential_manager.store_credential(
            tenant_id=tenant_id,
            service_name='infosys_finacle',
            credential_type='jwt_credentials',
            credential_data=credential_data,
            metadata={'banking_system': 'infosys_finacle'}
        )
        
        print(f"✅ Infosys Finacle credentials stored!")
        print(f"   Credential ID: {credential_id}")
    
    async def _validate_all_credentials(self, tenant_id: str):
        """Validate all credentials for the tenant."""
        print("\n--- Validating All Credentials ---")
        
        async with self.service_setup:
            result = await self.service_setup.validate_all_credentials(tenant_id)
        
        print(f"Validation Results:")
        print(f"  Total Credentials: {result['total_credentials']}")
        print(f"  Valid: {result['valid_credentials']}")
        print(f"  Invalid: {result['invalid_credentials']}")
        print()
        
        for cred_result in result['results']:
            status = cred_result['test_result']['status']
            icon = "✅" if status == 'valid' else "❌" if status == 'error' else "⚠️"
            print(f"  {icon} {cred_result['service_name']}: {status}")
    
    async def _list_credentials(self, tenant_id: str):
        """List all credentials for the tenant."""
        print("\n--- Current Credentials ---")
        
        credentials = await self.credential_manager.list_credentials(tenant_id)
        
        if not credentials:
            print("No credentials found for this tenant.")
            return
        
        for cred in credentials:
            status = "✅ Active" if not cred['is_expired'] else "❌ Expired"
            print(f"  {cred['service_name']} ({cred['credential_type']})")
            print(f"    ID: {cred['credential_id']}")
            print(f"    Status: {status}")
            print(f"    Created: {cred['created_at']}")
            if cred['expires_at']:
                print(f"    Expires: {cred['expires_at']}")
            print()


async def main():
    """Main entry point."""
    try:
        setup = ProductionCredentialSetup()
        await setup.run_interactive_setup()
    except KeyboardInterrupt:
        print("\nSetup interrupted by user.")
    except Exception as e:
        print(f"Setup failed: {e}")
        logger.error(f"Setup error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
