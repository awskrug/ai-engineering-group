"""
All Employees Tool - Retrieve complete employee directory from DynamoDB (HR Manager only)

This tool returns the complete list of all employees in the organization.
This is typically restricted to HR Manager role only through FGAC.
"""

import json
import os
import boto3
from boto3.dynamodb.conditions import Attr

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
EMPLOYEES_TABLE_NAME = os.environ.get('EMPLOYEES_TABLE_NAME', 'Employees')


def lambda_handler(event, context):
    """Lambda handler for all employees tool."""
    print(f"All employees tool received event: {json.dumps(event)}")
    
    # Parse input
    body = event if isinstance(event, dict) else json.loads(event)
    department = body.get('department')  # Optional filter
    status = body.get('status', 'Active')  # Default to Active employees
    
    try:
        table = dynamodb.Table(EMPLOYEES_TABLE_NAME)
        
        # Scan all employees
        if department:
            response = table.scan(
                FilterExpression=Attr('department').eq(department) & Attr('status').eq(status)
            )
        else:
            response = table.scan(
                FilterExpression=Attr('status').eq(status)
            )
        
        employees = response.get('Items', [])
        
        # Handle pagination if needed
        while 'LastEvaluatedKey' in response:
            if department:
                response = table.scan(
                    FilterExpression=Attr('department').eq(department) & Attr('status').eq(status),
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
            else:
                response = table.scan(
                    FilterExpression=Attr('status').eq(status),
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
            employees.extend(response.get('Items', []))
        
        # Remove leave entitlement fields (managed separately in LeaveRecords table)
        LEAVE_FIELDS = {'annual_leave_entitlement', 'sick_leave_entitlement', 'personal_leave_entitlement'}
        employees = [{k: v for k, v in emp.items() if k not in LEAVE_FIELDS} for emp in employees]
        
        if not employees:
            if department:
                return {
                    "statusCode": 404,
                    "body": {
                        "tool": "all_employees_tool",
                        "error": f"No {status.lower()} employees found in department '{department}'",
                        "success": False
                    }
                }
            else:
                return {
                    "statusCode": 404,
                    "body": {
                        "tool": "all_employees_tool",
                        "error": f"No {status.lower()} employees found",
                        "success": False
                    }
                }
        
        # Calculate department statistics
        dept_stats = {}
        for emp in employees:
            dept = emp.get('department', 'Unknown')
            if dept not in dept_stats:
                dept_stats[dept] = 0
            dept_stats[dept] += 1
        
        result_data = {
            "query_type": "all_employees",
            "total_employees": len(employees),
            "status_filter": status,
            "department_filter": department if department else "All",
            "department_statistics": dept_stats,
            "employees": employees
        }
        
        return {
            "statusCode": 200,
            "body": {
                "tool": "all_employees_tool",
                "result": result_data,
                "success": True,
                "note": "This tool is restricted to HR Manager role. Full employee details including PII are returned."
            }
        }
        
    except Exception as e:
        print(f"Error retrieving employees: {e}")
        return {
            "statusCode": 500,
            "body": {
                "tool": "all_employees_tool",
                "error": f"Failed to retrieve employees: {str(e)}",
                "success": False
            }
        }


# MCP Tool Definition
TOOL_DEFINITION = {
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
}


if __name__ == "__main__":
    # Test the tool locally (requires AWS credentials and DynamoDB table)
    test_events = [
        {},  # All active employees
        {"department": "Engineering"},
        {"status": "Active"},
        {"department": "Human Resources", "status": "Active"}
    ]

    for test_event in test_events:
        print(f"\n{'='*60}")
        print(f"Testing with: {test_event}")
        print(f"{'='*60}")
        result = lambda_handler(test_event, None)
        print(f"\nTest result:\n{json.dumps(result, indent=2, default=str)}")
