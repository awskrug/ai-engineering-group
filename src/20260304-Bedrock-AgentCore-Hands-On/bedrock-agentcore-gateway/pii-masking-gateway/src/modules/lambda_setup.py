"""
Lambda setup module for interceptors and tools
"""

import json
import time
from pathlib import Path
from typing import Dict, List
from src.utils.aws_utils import *


def setup_request_interceptor_lambda(lambda_function_name: str, lambda_role_arn: str,
                                    deployment_id: str, region: str,
                                    employee_permissions_table_name: str) -> str:
    """
    Setup Request Interceptor Lambda for pre-validation of tool access.
    
    Args:
        lambda_function_name: Name for the request interceptor Lambda
        lambda_role_arn: ARN of the IAM role for Lambda
        deployment_id: Deployment identifier
        region: AWS region
        employee_permissions_table_name: DynamoDB employee permissions table name
        
    Returns:
        Lambda ARN
    """
    print("\n" + "="*40)
    print("Setting up Request Interceptor Lambda")
    print("="*40)
    
    # Deploy request interceptor Lambda
    lambda_env_vars = {
        'EMPLOYEE_PERMISSIONS_TABLE_NAME': employee_permissions_table_name,
        'DEPLOYMENT_ID': deployment_id,
        'REGION': region
    }
    
    project_root = Path(__file__).parent.parent.parent
    interceptor_code_path = project_root / 'src' / 'interceptors' / 'request_interceptor.py'
    
    lambda_arn = deploy_lambda_function(
        function_name=lambda_function_name,
        role_arn=lambda_role_arn,
        lambda_code_path=str(interceptor_code_path),
        description='AgentCore Request Interceptor for pre-validation of tool access',
        timeout=30,
        memory_size=256,
        environment_vars=lambda_env_vars,
        region=region
    )
    
    print(f"✓ Request Interceptor Lambda deployed: {lambda_arn}")
    
    # Grant Gateway permission to invoke Lambda
    print("Granting Gateway permission to invoke Request Interceptor...")
    grant_gateway_invoke_permission(lambda_function_name, region)
    
    return lambda_arn


def setup_interceptor_lambda(lambda_function_name: str, lambda_role_name: str, 
                           guardrail_id: str, guardrail_version: str,
                           region: str,
                           employee_permissions_table_name: str) -> str:
    """
    Setup Lambda interceptor with both PII masking and FGAC capabilities.
    
    Returns:
        Lambda ARN
    """
    print("\n" + "="*40)
    print("Setting up Lambda Interceptor")
    print("="*40)
    
    # Create IAM role for Lambda interceptor
    lambda_role_arn = create_lambda_role(
        lambda_role_name,
        'Role for AgentCore Lambda Interceptor with PII masking and FGAC'
    )
    
    # Add additional permissions for Bedrock Guardrails and DynamoDB
    print("Adding additional permissions to Lambda role...")
    iam_client = boto3.client('iam')
    
    # Bedrock Guardrails permissions
    bedrock_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": ["bedrock:ApplyGuardrail"],
            "Resource": "*"
        }]
    }
    
    # DynamoDB permissions (EmployeePermissions only)
    sts_client = boto3.client('sts')
    account_id = sts_client.get_caller_identity()['Account']
    
    employee_permissions_table_arn = f"arn:aws:dynamodb:{region}:{account_id}:table/{employee_permissions_table_name}"
    
    dynamodb_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": ["dynamodb:Query", "dynamodb:GetItem"],
            "Resource": [employee_permissions_table_arn]
        }]
    }
    
    try:
        iam_client.put_role_policy(
            RoleName=lambda_role_name,
            PolicyName='BedrockGuardrailsPolicy',
            PolicyDocument=json.dumps(bedrock_policy)
        )
        print("✓ Bedrock Guardrails permissions added")
        
        iam_client.put_role_policy(
            RoleName=lambda_role_name,
            PolicyName='DynamoDBPermissionsPolicy',
            PolicyDocument=json.dumps(dynamodb_policy)
        )
        print("✓ DynamoDB permissions added")
        
    except Exception as e:
        print(f"⚠ Failed to add additional permissions: {e}")
    
    # Wait for Bedrock Guardrail to be ready
    print("Waiting for Bedrock Guardrail to propagate...")
    time.sleep(10)
    
    # Deploy interceptor Lambda
    lambda_env_vars = {
        'GUARDRAIL_ID': guardrail_id,
        'GUARDRAIL_VERSION': guardrail_version,
        'EMPLOYEE_PERMISSIONS_TABLE_NAME': employee_permissions_table_name,
        'DYNAMODB_REGION': region
    }
    
    project_root = Path(__file__).parent.parent.parent
    interceptor_code_path = project_root / 'src' / 'interceptors' / 'combined_interceptor.py'
    
    lambda_arn = deploy_lambda_function(
        function_name=lambda_function_name,
        role_arn=lambda_role_arn,
        lambda_code_path=str(interceptor_code_path),
        description='AgentCore Lambda Interceptor with PII masking and FGAC',
        timeout=30,
        memory_size=256,
        environment_vars=lambda_env_vars,
        region=region
    )
    
    print(f"✓ Interceptor Lambda deployed: {lambda_arn}")
    
    # Grant Gateway permission to invoke Lambda
    print("Granting Gateway permission to invoke Lambda...")
    grant_gateway_invoke_permission(lambda_function_name, region)
    
    return lambda_arn


def setup_tool_lambdas(deployment_id: str, region: str) -> List[Dict]:
    """
    Setup HR tool Lambda functions.
    
    Returns:
        List of deployed tool information
    """
    print("\n" + "="*40)
    print("Setting up HR Tool Lambda Functions")
    print("="*40)
    
    # Create IAM role for tool Lambdas
    tool_role_name = f"hr-tool-lambda-role-{deployment_id}"
    tool_role_arn = create_lambda_role(
        tool_role_name,
        'Role for HR tool Lambda functions'
    )
    
    # Add DynamoDB permissions for Employees and LeaveRecords tables
    print("Adding DynamoDB permissions to tool Lambda role...")
    iam_client = boto3.client('iam')
    sts_client = boto3.client('sts')
    account_id = sts_client.get_caller_identity()['Account']
    
    # DynamoDB table ARNs
    employees_table_arn = f"arn:aws:dynamodb:{region}:{account_id}:table/Employees"
    leave_records_table_arn = f"arn:aws:dynamodb:{region}:{account_id}:table/LeaveRecords"
    
    dynamodb_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": [
                "dynamodb:Scan",
                "dynamodb:Query",
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem"
            ],
            "Resource": [
                employees_table_arn,
                leave_records_table_arn,
                f"{employees_table_arn}/index/*",
                f"{leave_records_table_arn}/index/*"
            ]
        }]
    }
    
    try:
        iam_client.put_role_policy(
            RoleName=tool_role_name,
            PolicyName='HRToolDynamoDBPolicy',
            PolicyDocument=json.dumps(dynamodb_policy)
        )
        print("✓ DynamoDB permissions added to tool Lambda role")
        print(f"  - Employees table: {employees_table_arn}")
        print(f"  - LeaveRecords table: {leave_records_table_arn}")
    except Exception as e:
        print(f"⚠ Failed to add DynamoDB permissions: {e}")
    
    # Wait for IAM policy to propagate
    print("Waiting for IAM policy to propagate...")
    time.sleep(5)
    
    # Import and deploy tool Lambda functions
    project_root = Path(__file__).parent.parent.parent
    
    # Define HR tools to deploy
    tools_config = [
        {
            'name': 'all_employees_tool',
            'file': 'all_employees_tool.py',
            'description': 'Retrieve all employees from DynamoDB (HR Manager only)'
        },
        {
            'name': 'employee_search_tool',
            'file': 'employee_search_tool.py',
            'description': 'Search for specific employees by ID or name from DynamoDB'
        },
        {
            'name': 'all_leave_records_tool', 
            'file': 'all_leave_records_tool.py',
            'description': 'Retrieve all leave records from DynamoDB (HR Manager only)'
        },
        {
            'name': 'employee_leave_tool',
            'file': 'employee_leave_tool.py', 
            'description': 'Retrieve leave records for a specific employee from DynamoDB'
        }
    ]
    
    deployed_tools = []
    
    for tool_config in tools_config:
        tool_name = tool_config['name']
        print(f"  Deploying {tool_name}...")
        
        function_name = f"{tool_name.replace('_', '-')}-{deployment_id}"
        tool_code_path = project_root / 'src' / 'tools' / tool_config['file']
        
        # Check if tool file exists, if not create a basic one
        if not tool_code_path.exists():
            create_basic_hr_tool(tool_code_path, tool_name, tool_config['description'])
        
        lambda_arn = deploy_lambda_function(
            function_name=function_name,
            role_arn=tool_role_arn,
            lambda_code_path=str(tool_code_path),
            environment_vars={'TOOL_NAME': tool_name},
            description=tool_config['description'],
            region=region
        )
        
        # Get tool definition
        tool_definition = get_hr_tool_definition(tool_name)
        
        deployed_tools.append({
            'tool_name': tool_name,
            'function_name': function_name,
            'lambda_arn': lambda_arn,
            'tool_definition': tool_definition
        })
    
    print(f"✓ Deployed {len(deployed_tools)} HR tool Lambdas")
    return deployed_tools


def create_basic_hr_tool(file_path: Path, tool_name: str, description: str):
    """Create a basic HR tool file if it doesn't exist."""
    basic_tool_code = f'''"""
{description}
"""

import json


def lambda_handler(event, context):
    """Lambda handler for {tool_name}."""
    print(f"{tool_name} received event: {{json.dumps(event)}}")
    
    # Parse input
    body = event if isinstance(event, dict) else json.loads(event)
    
    # Generate mock response
    result = {{
        "tool": "{tool_name}",
        "status": "success",
        "data": f"Mock response from {tool_name}",
        "timestamp": "2024-01-01T00:00:00Z"
    }}
    
    return {{
        "statusCode": 200,
        "body": {{
            "tool": "{tool_name}",
            "result": result,
            "success": True
        }}
    }}


# MCP Tool Definition
TOOL_DEFINITION = {{
    "name": "{tool_name}",
    "description": "{description}",
    "inputSchema": {{
        "type": "object",
        "properties": {{
            "query": {{
                "type": "string",
                "description": "Query or input for the tool"
            }}
        }},
        "required": []
    }}
}}
'''
    
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w') as f:
        f.write(basic_tool_code)


def get_hr_tool_definition(tool_name: str) -> Dict:
    """Get tool definition for HR tools."""
    definitions = {
        'all_employees_tool': {
            "name": "all_employees_tool",
            "description": "Retrieve the complete list of all employees in the organization from DynamoDB. This tool is restricted to HR Manager role only. Returns full employee details including PII. Optionally filter by department or status.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "department": {
                        "type": "string",
                        "description": "Optional: Filter employees by department (e.g., 'Engineering', 'Human Resources', 'Marketing', 'Finance')"
                    },
                    "status": {
                        "type": "string",
                        "description": "Optional: Filter by employee status (default: 'Active'). Options: 'Active', 'Inactive', 'On Leave'"
                    }
                },
                "required": []
            }
        },
        'employee_search_tool': {
            "name": "employee_search_tool",
            "description": "Search for specific employees by ID or name from DynamoDB. Returns detailed employee information. HR managers see full details including PII, regular employees see limited info for other employees.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "employee_id": {
                        "type": "string",
                        "description": "Search for a specific employee by their ID (e.g., 'EMP-001')"
                    },
                    "search_name": {
                        "type": "string",
                        "description": "Search for employees by name (partial matches supported, e.g., 'Alice' or 'Johnson')"
                    }
                },
                "required": []
            }
        },
        'all_leave_records_tool': {
            "name": "all_leave_records_tool",
            "description": "Retrieve all employee leave records from DynamoDB. This tool is restricted to HR Manager role only. Returns complete leave history with statistics. Optionally filter by leave type, status, or year.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "leave_type": {
                        "type": "string",
                        "description": "Optional: Filter by leave type. Options: 'Annual', 'Sick', 'Personal', 'Unpaid'"
                    },
                    "status": {
                        "type": "string",
                        "description": "Optional: Filter by approval status. Options: 'Approved', 'Pending', 'Rejected'"
                    },
                    "year": {
                        "type": "string",
                        "description": "Optional: Filter by year (e.g., '2024', '2025')"
                    }
                },
                "required": []
            }
        },
        'employee_leave_tool': {
            "name": "employee_leave_tool",
            "description": "Retrieve leave records for a specific employee from DynamoDB. Employees can view their own records, HR managers can view any employee's records. Returns leave history with balance calculations. Optionally filter by year or leave type.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "employee_id": {
                        "type": "string",
                        "description": "Required: Employee ID to query leave records for (e.g., 'EMP-001')"
                    },
                    "year": {
                        "type": "string",
                        "description": "Optional: Filter by year (e.g., '2024', '2025')"
                    },
                    "leave_type": {
                        "type": "string",
                        "description": "Optional: Filter by leave type. Options: 'Annual', 'Sick', 'Personal', 'Unpaid'"
                    }
                },
                "required": ["employee_id"]
            }
        }
    }
    
    return definitions.get(tool_name, {
        "name": tool_name,
        "description": f"{tool_name} function",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    })