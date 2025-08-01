#!/usr/bin/env python3
"""
RegulensAI API Documentation Test
Tests API documentation endpoints and validates documentation completeness.
"""

import asyncio
import requests
import json
import time
from typing import Dict, List, Any
import sys

class APIDocumentationTester:
    """Tests API documentation completeness and functionality."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = {
            'swagger_ui': False,
            'redoc': False,
            'openapi_json': False,
            'endpoints_documented': 0,
            'total_endpoints': 0,
            'schemas_complete': False,
            'auth_documented': False,
            'try_it_out_functional': False,
            'errors': []
        }
    
    def test_swagger_ui(self) -> bool:
        """Test Swagger UI accessibility."""
        try:
            response = requests.get(f"{self.base_url}/docs", timeout=10)
            if response.status_code == 200 and "swagger" in response.text.lower():
                print("✓ Swagger UI is accessible")
                return True
            else:
                self.results['errors'].append(f"Swagger UI returned status {response.status_code}")
                return False
        except Exception as e:
            self.results['errors'].append(f"Swagger UI test failed: {str(e)}")
            return False
    
    def test_redoc(self) -> bool:
        """Test ReDoc accessibility."""
        try:
            response = requests.get(f"{self.base_url}/redoc", timeout=10)
            if response.status_code == 200 and "redoc" in response.text.lower():
                print("✓ ReDoc is accessible")
                return True
            else:
                self.results['errors'].append(f"ReDoc returned status {response.status_code}")
                return False
        except Exception as e:
            self.results['errors'].append(f"ReDoc test failed: {str(e)}")
            return False
    
    def test_openapi_json(self) -> bool:
        """Test OpenAPI JSON schema accessibility."""
        try:
            response = requests.get(f"{self.base_url}/openapi.json", timeout=10)
            if response.status_code == 200:
                try:
                    openapi_spec = response.json()
                    if "openapi" in openapi_spec and "paths" in openapi_spec:
                        print("✓ OpenAPI JSON schema is accessible and valid")
                        return True, openapi_spec
                    else:
                        self.results['errors'].append("OpenAPI JSON schema is invalid")
                        return False, None
                except json.JSONDecodeError:
                    self.results['errors'].append("OpenAPI JSON is not valid JSON")
                    return False, None
            else:
                self.results['errors'].append(f"OpenAPI JSON returned status {response.status_code}")
                return False, None
        except Exception as e:
            self.results['errors'].append(f"OpenAPI JSON test failed: {str(e)}")
            return False, None
    
    def analyze_openapi_spec(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze OpenAPI specification for completeness."""
        analysis = {
            'total_paths': 0,
            'documented_paths': 0,
            'has_auth': False,
            'has_schemas': False,
            'missing_descriptions': [],
            'missing_examples': [],
            'endpoints': []
        }
        
        # Analyze paths
        if "paths" in spec:
            for path, methods in spec["paths"].items():
                analysis['total_paths'] += 1
                for method, details in methods.items():
                    if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                        endpoint_info = {
                            'path': path,
                            'method': method.upper(),
                            'has_description': 'description' in details,
                            'has_summary': 'summary' in details,
                            'has_responses': 'responses' in details,
                            'has_examples': False
                        }
                        
                        # Check for examples in responses
                        if 'responses' in details:
                            for response_code, response_details in details['responses'].items():
                                if 'content' in response_details:
                                    for content_type, content_details in response_details['content'].items():
                                        if 'examples' in content_details or 'example' in content_details:
                                            endpoint_info['has_examples'] = True
                                            break
                        
                        analysis['endpoints'].append(endpoint_info)
                        
                        if endpoint_info['has_description'] and endpoint_info['has_summary']:
                            analysis['documented_paths'] += 1
                        else:
                            analysis['missing_descriptions'].append(f"{method.upper()} {path}")
        
        # Check for authentication
        if "components" in spec and "securitySchemes" in spec["components"]:
            analysis['has_auth'] = True
        
        # Check for schemas
        if "components" in spec and "schemas" in spec["components"]:
            analysis['has_schemas'] = len(spec["components"]["schemas"]) > 0
        
        return analysis
    
    def test_health_endpoint(self) -> bool:
        """Test if health endpoint is accessible."""
        try:
            response = requests.get(f"{self.base_url}/v1/health", timeout=10)
            if response.status_code == 200:
                print("✓ Health endpoint is accessible")
                return True
            else:
                self.results['errors'].append(f"Health endpoint returned status {response.status_code}")
                return False
        except Exception as e:
            self.results['errors'].append(f"Health endpoint test failed: {str(e)}")
            return False
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive API documentation tests."""
        print("Starting API Documentation Audit...")
        print("=" * 50)
        
        # Test basic endpoints
        self.results['swagger_ui'] = self.test_swagger_ui()
        self.results['redoc'] = self.test_redoc()
        
        # Test OpenAPI specification
        openapi_valid, openapi_spec = self.test_openapi_json()
        self.results['openapi_json'] = openapi_valid
        
        if openapi_valid and openapi_spec:
            # Analyze specification
            analysis = self.analyze_openapi_spec(openapi_spec)
            
            self.results['total_endpoints'] = len(analysis['endpoints'])
            self.results['endpoints_documented'] = analysis['documented_paths']
            self.results['schemas_complete'] = analysis['has_schemas']
            self.results['auth_documented'] = analysis['has_auth']
            
            print(f"✓ Found {analysis['total_paths']} API paths")
            print(f"✓ {analysis['documented_paths']} paths have complete documentation")
            print(f"✓ Authentication schemes: {'Yes' if analysis['has_auth'] else 'No'}")
            print(f"✓ Schema definitions: {'Yes' if analysis['has_schemas'] else 'No'}")
            
            if analysis['missing_descriptions']:
                print(f"⚠️  Endpoints missing descriptions: {len(analysis['missing_descriptions'])}")
                for endpoint in analysis['missing_descriptions'][:5]:  # Show first 5
                    print(f"   - {endpoint}")
        
        # Test health endpoint
        health_ok = self.test_health_endpoint()
        
        # Calculate overall score
        total_tests = 5  # swagger, redoc, openapi, health, completeness
        passed_tests = sum([
            self.results['swagger_ui'],
            self.results['redoc'], 
            self.results['openapi_json'],
            health_ok,
            self.results['endpoints_documented'] > 0
        ])
        
        score = (passed_tests / total_tests) * 100
        
        print("\n" + "=" * 50)
        print("API DOCUMENTATION AUDIT RESULTS")
        print("=" * 50)
        print(f"Overall Score: {score:.1f}%")
        print(f"Swagger UI: {'✓' if self.results['swagger_ui'] else '✗'}")
        print(f"ReDoc: {'✓' if self.results['redoc'] else '✗'}")
        print(f"OpenAPI JSON: {'✓' if self.results['openapi_json'] else '✗'}")
        print(f"Health Endpoint: {'✓' if health_ok else '✗'}")
        print(f"Documentation Coverage: {self.results['endpoints_documented']}/{self.results['total_endpoints']} endpoints")
        
        if self.results['errors']:
            print("\nErrors encountered:")
            for error in self.results['errors']:
                print(f"  ✗ {error}")
        
        self.results['overall_score'] = score
        self.results['health_endpoint'] = health_ok
        
        return self.results

def main():
    """Main function to run API documentation tests."""
    # Test different possible ports
    ports = [8000, 8001, 3000]
    
    for port in ports:
        base_url = f"http://localhost:{port}"
        print(f"Testing API documentation at {base_url}...")
        
        try:
            # Quick connectivity test
            response = requests.get(f"{base_url}/docs", timeout=5)
            if response.status_code == 200:
                print(f"✓ Found API server at port {port}")
                tester = APIDocumentationTester(base_url)
                results = tester.run_comprehensive_test()
                
                if results['overall_score'] >= 80:
                    print(f"\n🎉 API Documentation Audit: PASSED ({results['overall_score']:.1f}%)")
                    return 0
                else:
                    print(f"\n⚠️  API Documentation Audit: NEEDS IMPROVEMENT ({results['overall_score']:.1f}%)")
                    return 1
                    
        except requests.exceptions.RequestException:
            print(f"✗ No API server found at port {port}")
            continue
    
    print("✗ No accessible API server found on any tested port")
    print("Please ensure the API server is running on port 8000, 8001, or 3000")
    return 1

if __name__ == "__main__":
    sys.exit(main())
