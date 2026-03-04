"""
Deployment configuration for HR Employee Management Gateway
"""

from datetime import datetime

# Generate unique identifier for this deployment
DEPLOYMENT_ID = datetime.now().strftime('%Y%m%d-%H%M%S')

# AWS Configuration
REGION = "us-east-1"

# Lambda Configuration
LAMBDA_FUNCTION_NAME = f"hr-interceptor-lambda-{DEPLOYMENT_ID}"
LAMBDA_ROLE_NAME = f"hr-interceptor-lambda-role-{DEPLOYMENT_ID}"
TOOL_ROLE_NAME = f"hr-tool-lambda-role-{DEPLOYMENT_ID}"

# Gateway Configuration
GATEWAY_NAME = f"hr-gateway-{DEPLOYMENT_ID}"

# Cognito Configuration
USER_POOL_NAME = f"hr-gateway-pool-{DEPLOYMENT_ID}"
CLIENT_NAME = f"hr-gateway-client-{DEPLOYMENT_ID}"
RESOURCE_SERVER_ID = 'hr-gateway'
RESOURCE_SERVER_NAME = 'HR Gateway Resource Server'
SCOPES = [{'ScopeName': 'tools', 'ScopeDescription': 'Access to HR gateway tools'}]

# DynamoDB Configuration
EMPLOYEE_PERMISSIONS_TABLE_NAME = f"EmployeePermissions-{DEPLOYMENT_ID}"

# Bedrock Guardrails Configuration
GUARDRAIL_NAME = f"hr-pii-masking-guardrail-{DEPLOYMENT_ID}"

# PII Entity Types for Bedrock Guardrails (HR focused)
PII_ENTITY_TYPES = [
    # Personal Information (EMAIL excluded - should remain visible)
    'ADDRESS', 'NAME', 'PHONE', 'USERNAME', 'PASSWORD',
    
    # Financial Information
    'CREDIT_DEBIT_CARD_NUMBER', 'US_BANK_ACCOUNT_NUMBER', 'US_BANK_ROUTING_NUMBER',
    
    # Government IDs
    'US_INDIVIDUAL_TAX_IDENTIFICATION_NUMBER',
    'DRIVER_ID', 'US_PASSPORT_NUMBER',
    
    # Network & Technical
    'IP_ADDRESS', 'URL'
]

def get_sensitive_information_policy_config():
    """
    Generate sensitive information policy configuration for Bedrock Guardrails.
    
    Returns:
        dict: Policy configuration with all PII types set to ANONYMIZE
    """
    return {
        'piiEntitiesConfig': [
            {'type': pii_type, 'action': 'ANONYMIZE'} 
            for pii_type in PII_ENTITY_TYPES
        ]
    }

def print_config():
    """Print current deployment configuration."""
    print("HR Employee Management Gateway Configuration:")
    print(f"  Deployment ID: {DEPLOYMENT_ID}")
    print(f"  Region: {REGION}")
    print(f"  Lambda Function: {LAMBDA_FUNCTION_NAME}")
    print(f"  Gateway Name: {GATEWAY_NAME}")
    print(f"  Employee Permissions Table: {EMPLOYEE_PERMISSIONS_TABLE_NAME}")
    print(f"  Guardrail Name: {GUARDRAIL_NAME}")
    print(f"  PII Types: {len(PII_ENTITY_TYPES)} configured")