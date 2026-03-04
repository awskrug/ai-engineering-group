"""
Employee Search Tool - Search for specific employees from DynamoDB

This tool allows searching for individual employees by ID or name.
- HR Manager: Full access to all employee details including PII
- Regular Employee: Can search but sees limited info (PII masked by interceptor)
"""

import json
import os
import boto3
from boto3.dynamodb.conditions import Key, Attr

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
EMPLOYEES_TABLE_NAME = os.environ.get('EMPLOYEES_TABLE_NAME', 'Employees')


def lambda_handler(event, context):
    """Lambda handler for employee search tool."""
    print(f"Employee search tool received event: {json.dumps(event)}")
    
    # Parse input
    body = event if isinstance(event, dict) else json.loads(event)
    employee_id = body.get('employee_id')
    search_name = body.get('search_name')
    
    try:
        table = dynamodb.Table(EMPLOYEES_TABLE_NAME)
        
        # Search by employee ID (primary key)
        if employee_id:
            response = table.get_item(Key={'employee_id': employee_id})
            
            if 'Item' not in response:
                return {
                    "statusCode": 404,
                    "body": {
                        "tool": "employee_search_tool",
                        "error": f"No employee found with ID '{employee_id}'",
                        "success": False
                    }
                }
            
            # Remove leave entitlement fields (managed separately in LeaveRecords table)
            LEAVE_FIELDS = {'annual_leave_entitlement', 'sick_leave_entitlement', 'personal_leave_entitlement'}
            item = {k: v for k, v in response['Item'].items() if k not in LEAVE_FIELDS}
            
            result_data = {
                "query_type": "by_id",
                "search_query": employee_id,
                "results_count": 1,
                "employees": [item]
            }
        
        # Search by name (scan with filter)
        elif search_name:
            search_name_lower = search_name.lower().strip()
            
            # Scan with name filter
            response = table.scan(
                FilterExpression=Attr('name').contains(search_name) | 
                                Attr('name').contains(search_name.title()) |
                                Attr('name').contains(search_name.upper())
            )
            
            found_employees = response.get('Items', [])
            
            # Additional filtering for partial matches
            filtered_employees = []
            for emp in found_employees:
                emp_name_lower = emp.get('name', '').lower()
                if (search_name_lower in emp_name_lower or 
                    any(search_name_lower in part.lower() for part in emp.get('name', '').split())):
                    filtered_employees.append(emp)
            
            if not filtered_employees:
                return {
                    "statusCode": 404,
                    "body": {
                        "tool": "employee_search_tool",
                        "error": f"No employees found matching '{search_name}'",
                        "success": False,
                        "suggestion": "Try searching with a different name or use employee ID"
                    }
                }
            
            # Remove leave entitlement fields (managed separately in LeaveRecords table)
            LEAVE_FIELDS = {'annual_leave_entitlement', 'sick_leave_entitlement', 'personal_leave_entitlement'}
            filtered_employees = [{k: v for k, v in emp.items() if k not in LEAVE_FIELDS} for emp in filtered_employees]
            
            result_data = {
                "query_type": "by_name",
                "search_query": search_name,
                "results_count": len(filtered_employees),
                "employees": filtered_employees
            }
        
        else:
            return {
                "statusCode": 400,
                "body": {
                    "tool": "employee_search_tool",
                    "error": "Please provide either employee_id or search_name",
                    "success": False,
                    "examples": {
                        "by_id": {"employee_id": "EMP-001"},
                        "by_name": {"search_name": "Employee 1"}
                    }
                }
            }
        
        return {
            "statusCode": 200,
            "body": {
                "tool": "employee_search_tool",
                "result": result_data,
                "success": True,
                "note": "Data visibility depends on user role: HR sees full details, employees see limited info for others"
            }
        }
        
    except Exception as e:
        print(f"Error searching employees: {e}")
        return {
            "statusCode": 500,
            "body": {
                "tool": "employee_search_tool",
                "error": f"Failed to search employees: {str(e)}",
                "success": False
            }
        }


# MCP Tool Definition
TOOL_DEFINITION = {
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
                "description": "Search for employees by name (partial matches supported, e.g., 'Employee 1' or 'Employee')"
            }
        },
        "required": []
    }
}


if __name__ == "__main__":
    # Test the tool locally (requires AWS credentials and DynamoDB table)
    test_events = [
        {"employee_id": "EMP-001"},
        {"search_name": "Employee 2"},
        {"search_name": "Employee"},
        {}  # Test missing parameters
    ]

    for test_event in test_events:
        print(f"\n{'='*60}")
        print(f"Testing with: {test_event}")
        print(f"{'='*60}")
        result = lambda_handler(test_event, None)
        print(f"\nTest result:\n{json.dumps(result, indent=2, default=str)}")
