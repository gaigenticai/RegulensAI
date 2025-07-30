#!/usr/bin/env python3
"""
Production integration setup script for RegulensAI.
Sets up external data providers and GRC system integrations.
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


class ProductionIntegrationSetup:
    """
    Interactive setup for production integrations including external data providers
    and GRC systems.
    """
    
    def __init__(self):
        self.credential_manager = CredentialManager()
        self.service_setup = ServiceAccountSetup()
    
    async def run_interactive_setup(self):
        """Run interactive integration setup."""
        print("=" * 70)
        print("RegulensAI Production Integration Setup")
        print("=" * 70)
        print()
        
        # Get tenant ID
        tenant_id = input("Enter tenant ID (UUID): ").strip()
        if not tenant_id:
            print("Error: Tenant ID is required")
            return
        
        print(f"Setting up integrations for tenant: {tenant_id}")
        print()
        
        # Setup menu
        while True:
            print("Available integrations to configure:")
            print()
            print("External Data Providers:")
            print("1. OFAC Sanctions Lists")
            print("2. EU Sanctions Lists")
            print("3. UN Sanctions Lists")
            print("4. Refinitiv Market Data")
            print("5. Experian Credit Services")
            print()
            print("GRC Systems:")
            print("6. RSA Archer")
            print("7. ServiceNow GRC")
            print("8. MetricStream")
            print()
            print("Bulk Operations:")
            print("9. Setup all external data providers")
            print("10. Setup all GRC systems")
            print("11. Validate all integrations")
            print("12. Test all connections")
            print("13. Exit")
            print()
            
            choice = input("Select an option (1-13): ").strip()
            
            if choice == "1":
                await self._setup_ofac(tenant_id)
            elif choice == "2":
                await self._setup_eu_sanctions(tenant_id)
            elif choice == "3":
                await self._setup_un_sanctions(tenant_id)
            elif choice == "4":
                await self._setup_refinitiv(tenant_id)
            elif choice == "5":
                await self._setup_experian(tenant_id)
            elif choice == "6":
                await self._setup_archer(tenant_id)
            elif choice == "7":
                await self._setup_servicenow(tenant_id)
            elif choice == "8":
                await self._setup_metricstream(tenant_id)
            elif choice == "9":
                await self._setup_all_external_data(tenant_id)
            elif choice == "10":
                await self._setup_all_grc_systems(tenant_id)
            elif choice == "11":
                await self._validate_all_integrations(tenant_id)
            elif choice == "12":
                await self._test_all_connections(tenant_id)
            elif choice == "13":
                print("Exiting setup...")
                break
            else:
                print("Invalid choice. Please try again.")
            
            print()
    
    async def _setup_ofac(self, tenant_id: str):
        """Setup OFAC sanctions list integration."""
        print("\n--- OFAC Sanctions Setup ---")
        print("OFAC data is publicly available and requires no authentication.")
        
        cache_hours = input("Cache duration in hours [12]: ").strip() or "12"
        auto_update = input("Enable automatic updates? (y/n) [y]: ").strip().lower() != 'n'
        update_interval = input("Update interval in hours [4]: ").strip() or "4"
        
        credential_data = {
            'base_url': 'https://www.treasury.gov/ofac/downloads',
            'cache_hours': int(cache_hours),
            'auto_update': auto_update,
            'update_interval_hours': int(update_interval),
            'data_sources': [
                'sdn.xml',
                'consolidated.xml',
                'ssi.xml'
            ]
        }
        
        credential_id = await self.credential_manager.store_credential(
            tenant_id=tenant_id,
            service_name='ofac',
            credential_type='public_data_source',
            credential_data=credential_data,
            metadata={'provider_type': 'sanctions', 'data_classification': 'public'}
        )
        
        print(f"✅ OFAC integration configured!")
        print(f"   Credential ID: {credential_id}")
        print(f"   Cache Duration: {cache_hours} hours")
        print(f"   Auto Update: {'Enabled' if auto_update else 'Disabled'}")
    
    async def _setup_eu_sanctions(self, tenant_id: str):
        """Setup EU sanctions list integration."""
        print("\n--- EU Sanctions Setup ---")
        print("EU sanctions data is publicly available from the European Commission.")
        
        cache_hours = input("Cache duration in hours [24]: ").strip() or "24"
        auto_update = input("Enable automatic updates? (y/n) [y]: ").strip().lower() != 'n'
        update_interval = input("Update interval in hours [6]: ").strip() or "6"
        
        credential_data = {
            'consolidated_url': 'https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw',
            'financial_url': 'https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList/content?token=dG9rZW4tMjAxNw',
            'cache_hours': int(cache_hours),
            'auto_update': auto_update,
            'update_interval_hours': int(update_interval)
        }
        
        credential_id = await self.credential_manager.store_credential(
            tenant_id=tenant_id,
            service_name='eu_sanctions',
            credential_type='public_data_source',
            credential_data=credential_data,
            metadata={'provider_type': 'sanctions', 'data_classification': 'public'}
        )
        
        print(f"✅ EU Sanctions integration configured!")
        print(f"   Credential ID: {credential_id}")
    
    async def _setup_refinitiv(self, tenant_id: str):
        """Setup Refinitiv market data integration."""
        print("\n--- Refinitiv Market Data Setup ---")
        
        api_key = getpass.getpass("Enter Refinitiv API Key: ").strip()
        username = input("Enter Refinitiv Username: ").strip()
        password = getpass.getpass("Enter Refinitiv Password: ").strip()
        app_id = input("Enter Application ID [RegulensAI]: ").strip() or "RegulensAI"
        
        print("Testing Refinitiv connection...")
        
        async with self.service_setup:
            result = await self.service_setup.setup_refinitiv_account(
                tenant_id=tenant_id,
                api_key=api_key,
                app_id=app_id,
                username=username,
                password=password
            )
        
        if result['status'] == 'success':
            print(f"✅ Refinitiv integration successful!")
            print(f"   Credential ID: {result['credential_id']}")
            print(f"   Data Access: {result['data_access_test']['status']}")
            print(f"   Services: {', '.join(result['services_available'])}")
        else:
            print(f"❌ Refinitiv integration failed: {result['error']}")
    
    async def _setup_archer(self, tenant_id: str):
        """Setup RSA Archer integration."""
        print("\n--- RSA Archer Setup ---")
        
        base_url = input("Enter Archer Base URL: ").strip()
        username = input("Enter Archer Username: ").strip()
        password = getpass.getpass("Enter Archer Password: ").strip()
        instance_name = input("Enter Instance Name: ").strip()
        domain = input("Enter Domain (optional): ").strip()
        
        print("Testing Archer connection...")
        
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
            print(f"✅ Archer integration successful!")
            print(f"   Credential ID: {result['credential_id']}")
            print(f"   Applications Access: {result['applications_test']['status']}")
            print(f"   Services: {', '.join(result['services_available'])}")
        else:
            print(f"❌ Archer integration failed: {result['error']}")
    
    async def _setup_servicenow(self, tenant_id: str):
        """Setup ServiceNow GRC integration."""
        print("\n--- ServiceNow GRC Setup ---")
        
        instance_url = input("Enter ServiceNow Instance URL: ").strip()
        username = input("Enter ServiceNow Username: ").strip()
        password = getpass.getpass("Enter ServiceNow Password: ").strip()
        
        print("Testing ServiceNow connection...")
        
        async with self.service_setup:
            result = await self.service_setup.setup_servicenow_account(
                tenant_id=tenant_id,
                instance_url=instance_url,
                username=username,
                password=password
            )
        
        if result['status'] == 'success':
            print(f"✅ ServiceNow integration successful!")
            print(f"   Credential ID: {result['credential_id']}")
            print(f"   GRC Access: {result['grc_access_test']['status']}")
            print(f"   Services: {', '.join(result['services_available'])}")
        else:
            print(f"❌ ServiceNow integration failed: {result['error']}")
    
    async def _setup_metricstream(self, tenant_id: str):
        """Setup MetricStream integration."""
        print("\n--- MetricStream Setup ---")
        
        base_url = input("Enter MetricStream Base URL: ").strip()
        auth_type = input("Authentication type (api_key/oauth) [api_key]: ").strip() or "api_key"
        
        credential_data = {
            'metricstream_base_url': base_url,
            'metricstream_auth_type': auth_type
        }
        
        if auth_type == 'api_key':
            api_key = getpass.getpass("Enter MetricStream API Key: ").strip()
            credential_data['metricstream_api_key'] = api_key
        else:
            client_id = input("Enter OAuth Client ID: ").strip()
            client_secret = getpass.getpass("Enter OAuth Client Secret: ").strip()
            credential_data.update({
                'metricstream_client_id': client_id,
                'metricstream_client_secret': client_secret
            })
        
        credential_id = await self.credential_manager.store_credential(
            tenant_id=tenant_id,
            service_name='metricstream',
            credential_type='grc_system',
            credential_data=credential_data,
            metadata={'system_type': 'grc', 'auth_type': auth_type}
        )
        
        print(f"✅ MetricStream integration configured!")
        print(f"   Credential ID: {credential_id}")
        print(f"   Authentication: {auth_type}")
    
    async def _setup_all_external_data(self, tenant_id: str):
        """Setup all external data providers."""
        print("\n--- Setting up all external data providers ---")
        
        # Setup public data sources (no credentials needed)
        await self._setup_ofac(tenant_id)
        await self._setup_eu_sanctions(tenant_id)
        
        # Setup commercial data sources (require credentials)
        setup_refinitiv = input("\nSetup Refinitiv? (y/n): ").strip().lower() == 'y'
        if setup_refinitiv:
            await self._setup_refinitiv(tenant_id)
        
        setup_experian = input("Setup Experian? (y/n): ").strip().lower() == 'y'
        if setup_experian:
            await self._setup_experian(tenant_id)
        
        print("\n✅ External data provider setup completed!")
    
    async def _setup_all_grc_systems(self, tenant_id: str):
        """Setup all GRC systems."""
        print("\n--- Setting up all GRC systems ---")
        
        setup_archer = input("Setup RSA Archer? (y/n): ").strip().lower() == 'y'
        if setup_archer:
            await self._setup_archer(tenant_id)
        
        setup_servicenow = input("Setup ServiceNow GRC? (y/n): ").strip().lower() == 'y'
        if setup_servicenow:
            await self._setup_servicenow(tenant_id)
        
        setup_metricstream = input("Setup MetricStream? (y/n): ").strip().lower() == 'y'
        if setup_metricstream:
            await self._setup_metricstream(tenant_id)
        
        print("\n✅ GRC systems setup completed!")
    
    async def _validate_all_integrations(self, tenant_id: str):
        """Validate all configured integrations."""
        print("\n--- Validating All Integrations ---")
        
        async with self.service_setup:
            result = await self.service_setup.validate_all_credentials(tenant_id)
        
        print(f"Validation Results:")
        print(f"  Total Integrations: {result['total_credentials']}")
        print(f"  Valid: {result['valid_credentials']}")
        print(f"  Invalid: {result['invalid_credentials']}")
        print()
        
        for integration_result in result['results']:
            status = integration_result['test_result']['status']
            icon = "✅" if status == 'valid' else "❌" if status == 'error' else "⚠️"
            print(f"  {icon} {integration_result['service_name']}: {status}")
    
    async def _test_all_connections(self, tenant_id: str):
        """Test all integration connections."""
        print("\n--- Testing All Connections ---")
        
        # Get all credentials for tenant
        credentials = await self.credential_manager.list_credentials(tenant_id)
        
        if not credentials:
            print("No integrations found for this tenant.")
            return
        
        for cred in credentials:
            service_name = cred['service_name']
            print(f"\nTesting {service_name}...")
            
            try:
                # Retrieve credential data
                cred_data = await self.credential_manager.retrieve_credential(
                    tenant_id, service_name
                )
                
                if cred_data:
                    print(f"  ✅ {service_name}: Credentials retrieved successfully")
                    # Additional connection tests could be added here
                else:
                    print(f"  ❌ {service_name}: Failed to retrieve credentials")
                    
            except Exception as e:
                print(f"  ❌ {service_name}: Connection test failed - {e}")


async def main():
    """Main entry point."""
    try:
        setup = ProductionIntegrationSetup()
        await setup.run_interactive_setup()
    except KeyboardInterrupt:
        print("\nSetup interrupted by user.")
    except Exception as e:
        print(f"Setup failed: {e}")
        logger.error(f"Setup error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
