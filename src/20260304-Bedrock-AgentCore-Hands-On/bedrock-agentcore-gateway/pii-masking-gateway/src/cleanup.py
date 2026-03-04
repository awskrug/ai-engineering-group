#!/usr/bin/env python3
"""
Cleanup script for PII Masking Gateway

This script deletes all AWS resources created by the setup script:
- Gateway and targets
- Lambda functions
- IAM roles
- Cognito user pool
- Bedrock Guardrails
"""

import sys
import json
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import boto3
from src.utils.aws_utils import *


def load_deployment_info():
    """Load deployment information from file."""
    deployment_file = project_root / 'deployment_info.json'
    
    if not deployment_file.exists():
        print("⚠ Deployment info not found. Manual cleanup may be required.")
        return None
    
    with open(deployment_file, 'r') as f:
        return json.load(f)


def cleanup_resources(deployment_info):
    """Clean up all deployed resources."""
    print("="*80)
    print("Cleaning up Combined PII Masking and FGAC Gateway Resources")
    print("="*80)
    
    if not deployment_info:
        print("No deployment info available. Skipping cleanup.")
        return
    
    region = deployment_info.get('region', 'us-east-1')
    gateway_client = boto3.client('bedrock-agentcore-control', region_name=region)
    
    # Step 1: Delete Gateway Targets
    print("\nStep 1: Deleting Gateway Targets")
    print("-" * 40)
    
    gateway_id = deployment_info.get('gateway_id')
    target_ids = deployment_info.get('target_ids', [])
    
    if gateway_id and target_ids:
        try:
            delete_gateway_targets(gateway_client, gateway_id, target_ids)
            # Wait for target deletions to complete
            time.sleep(5)
        except Exception as e:
            print(f"⚠ Error deleting targets: {e}")
    
    # Step 2: Delete Gateway
    print("\nStep 2: Deleting Gateway")
    print("-" * 40)
    
    if gateway_id:
        try:
            delete_gateway(gateway_client, gateway_id)
            print("✓ Deleted gateway")
        except Exception as e:
            print(f"⚠ Error deleting gateway: {e}")
    
    # Step 3: Delete Lambda Functions
    print("\nStep 3: Deleting Lambda Functions")
    print("-" * 40)
    
    lambda_functions_to_delete = []
    
    # Response Interceptor Lambda
    lambda_function_name = deployment_info.get('lambda_function_name')
    if lambda_function_name:
        lambda_functions_to_delete.append(lambda_function_name)
    
    # Request Interceptor Lambda
    request_interceptor_name = deployment_info.get('request_interceptor_name')
    if request_interceptor_name:
        lambda_functions_to_delete.append(request_interceptor_name)
    
    # Tool Lambdas
    deployed_tools = deployment_info.get('deployed_tools', [])
    lambda_functions_to_delete.extend(deployed_tools)
    
    if lambda_functions_to_delete:
        delete_lambda_functions(lambda_functions_to_delete, region)
    
    # Step 4: Delete IAM Roles
    print("\nStep 4: Deleting IAM Roles")
    print("-" * 40)
    
    roles_to_delete = []
    
    lambda_role_name = deployment_info.get('lambda_role_name')
    tool_role_name = deployment_info.get('tool_role_name')
    gateway_name = deployment_info.get('gateway_name')
    
    if lambda_role_name:
        roles_to_delete.append(lambda_role_name)
    if tool_role_name:
        roles_to_delete.append(tool_role_name)
    if gateway_name:
        roles_to_delete.append(f"agentcore-{gateway_name}-role")
    
    for role_name in roles_to_delete:
        delete_iam_role(role_name)
    
    # Step 5: Delete DynamoDB Tables
    print("\nStep 5: Deleting DynamoDB Tables")
    print("-" * 40)
    
    employee_permissions_table_name = deployment_info.get('employee_permissions_table_name')
    if employee_permissions_table_name:
        delete_dynamodb_table(employee_permissions_table_name, region)
    
    employees_table_name = deployment_info.get('employees_table_name', 'Employees')
    if employees_table_name:
        delete_dynamodb_table(employees_table_name, region)
    
    leave_records_table_name = deployment_info.get('leave_records_table_name', 'LeaveRecords')
    if leave_records_table_name:
        delete_dynamodb_table(leave_records_table_name, region)
    
    # Step 6: Delete Cognito User Pool
    print("\nStep 6: Deleting Cognito User Pool")
    print("-" * 40)
    
    user_pool_id = deployment_info.get('user_pool_id')
    if user_pool_id:
        delete_cognito_user_pool(user_pool_id, region)
    
    # Step 7: Delete Bedrock Guardrail
    print("\nStep 7: Deleting Bedrock Guardrail")
    print("-" * 40)
    
    guardrail_id = deployment_info.get('guardrail_id')
    if guardrail_id:
        delete_bedrock_guardrail(guardrail_id, region)
    
    print("\n✓ Cleanup complete!")


def delete_deployment_file():
    """Delete the deployment info file."""
    deployment_file = project_root / 'deployment_info.json'
    
    if deployment_file.exists():
        deployment_file.unlink()
        print(f"✓ Deleted deployment info file: {deployment_file}")


def main():
    """Main cleanup function."""
    print("PII Masking Gateway Cleanup")
    
    # Confirm cleanup
    response = input("\n⚠️  WARNING: This will DELETE all deployed resources!\nContinue? (yes/no): ")
    
    if response.lower() not in ['yes', 'y']:
        print("Cleanup cancelled.")
        return
    
    # Load deployment info
    deployment_info = load_deployment_info()
    
    if deployment_info:
        print(f"\nCleaning up deployment: {deployment_info['deployment_id']}")
    
    # Clean up resources
    cleanup_resources(deployment_info)
    
    # Delete deployment file
    delete_deployment_file()
    
    print("\n🧹 All resources have been cleaned up!")
    print("\nIf you encounter any errors, you may need to manually delete:")
    print("  - Lambda functions starting with your deployment ID")
    print("  - IAM roles starting with 'interceptor-lambda-role-' or 'agentcore-'")
    print("  - Cognito user pools starting with 'gateway-pool-'")
    print("  - Bedrock Guardrails starting with 'pii-masking-guardrail-'")
    print("  - AgentCore Gateways starting with 'interceptor-gateway-'")


if __name__ == "__main__":
    main()