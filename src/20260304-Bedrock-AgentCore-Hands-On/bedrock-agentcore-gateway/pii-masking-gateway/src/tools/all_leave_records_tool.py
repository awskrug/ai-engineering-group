"""
All Leave Records Tool - Retrieve all employee leave records from DynamoDB (HR Manager only)

This tool returns complete leave records for all employees.
This is typically restricted to HR Manager role only through FGAC.
"""

import json
import os
import boto3
from boto3.dynamodb.conditions import Attr
from decimal import Decimal

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
LEAVE_RECORDS_TABLE_NAME = os.environ.get('LEAVE_RECORDS_TABLE_NAME', 'LeaveRecords')
EMPLOYEES_TABLE_NAME = os.environ.get('EMPLOYEES_TABLE_NAME', 'Employees')


def decimal_to_float(obj):
    """Convert Decimal to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def lambda_handler(event, context):
    """Lambda handler for all leave records tool."""
    print(f"All leave records tool received event: {json.dumps(event)}")
    
    # Parse input
    body = event if isinstance(event, dict) else json.loads(event)
    leave_type = body.get('leave_type')  # Optional filter: 'Annual', 'Sick', 'Personal'
    status = body.get('status')  # Optional filter: 'Approved', 'Pending', 'Rejected'
    year = body.get('year')  # Optional filter by year
    
    try:
        # First, get all employees to retrieve their entitlements
        employees_table = dynamodb.Table(EMPLOYEES_TABLE_NAME)
        employees_response = employees_table.scan()
        employees_data = employees_response.get('Items', [])
        
        # Handle pagination for employees
        while 'LastEvaluatedKey' in employees_response:
            employees_response = employees_table.scan(
                ExclusiveStartKey=employees_response['LastEvaluatedKey']
            )
            employees_data.extend(employees_response.get('Items', []))
        
        # Create employee entitlement map
        employee_entitlements = {}
        for emp in employees_data:
            emp_id = emp.get('employee_id')
            employee_entitlements[emp_id] = {
                'annual_entitlement': int(emp.get('annual_leave_entitlement', 20)),
                'sick_entitlement': int(emp.get('sick_leave_entitlement', 10)),
                'personal_entitlement': int(emp.get('personal_leave_entitlement', 5)),
                'name': emp.get('name', 'Unknown'),
                'department': emp.get('department', 'Unknown'),
                'position': emp.get('position', 'Unknown')
            }
        
        # Now get leave records
        table = dynamodb.Table(LEAVE_RECORDS_TABLE_NAME)
        
        # Build filter expression
        filter_expressions = []
        
        if leave_type:
            filter_expressions.append(Attr('leave_type').eq(leave_type))
        
        if status:
            filter_expressions.append(Attr('status').eq(status))
        
        if year:
            filter_expressions.append(Attr('year').eq(int(year)))
        
        # Scan with filters
        if filter_expressions:
            combined_filter = filter_expressions[0]
            for expr in filter_expressions[1:]:
                combined_filter = combined_filter & expr
            
            response = table.scan(FilterExpression=combined_filter)
        else:
            response = table.scan()
        
        leave_records = response.get('Items', [])
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            if filter_expressions:
                response = table.scan(
                    FilterExpression=combined_filter,
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
            else:
                response = table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
            leave_records.extend(response.get('Items', []))
        
        if not leave_records:
            return {
                "statusCode": 404,
                "body": {
                    "tool": "all_leave_records_tool",
                    "error": "No leave records found matching the criteria",
                    "success": False,
                    "filters": {
                        "leave_type": leave_type,
                        "status": status,
                        "year": year
                    }
                }
            }
        
        # Calculate statistics
        stats = {
            "total_records": len(leave_records),
            "by_type": {},
            "by_status": {},
            "total_days": 0
        }
        
        # Calculate per-employee summary
        employee_summaries = {}
        
        for record in leave_records:
            # Type statistics
            l_type = record.get('leave_type', 'Unknown')
            stats['by_type'][l_type] = stats['by_type'].get(l_type, 0) + 1
            
            # Status statistics
            l_status = record.get('status', 'Unknown')
            stats['by_status'][l_status] = stats['by_status'].get(l_status, 0) + 1
            
            # Total days
            days = record.get('days', 0)
            if isinstance(days, Decimal):
                days = float(days)
            stats['total_days'] += days
            
            # Per-employee summary
            emp_id = record.get('employee_id', 'Unknown')
            if emp_id not in employee_summaries:
                # Get entitlement from employee data
                entitlement = employee_entitlements.get(emp_id, {
                    'annual_entitlement': 20,
                    'sick_entitlement': 10,
                    'personal_entitlement': 5,
                    'name': 'Unknown',
                    'department': 'Unknown',
                    'position': 'Unknown'
                })
                
                employee_summaries[emp_id] = {
                    "employee_id": emp_id,
                    "name": entitlement['name'],
                    "department": entitlement['department'],
                    "position": entitlement['position'],
                    "total_records": 0,
                    "annual_entitlement": entitlement['annual_entitlement'],
                    "sick_entitlement": entitlement['sick_entitlement'],
                    "personal_entitlement": entitlement['personal_entitlement'],
                    "annual_taken": 0,
                    "sick_taken": 0,
                    "personal_taken": 0,
                    "total_days_taken": 0,
                    "pending_days": 0,
                    "annual_remaining": entitlement['annual_entitlement'],
                    "sick_remaining": entitlement['sick_entitlement'],
                    "personal_remaining": entitlement['personal_entitlement']
                }
            
            employee_summaries[emp_id]["total_records"] += 1
            
            if l_status == 'Approved':
                employee_summaries[emp_id]["total_days_taken"] += days
                
                if l_type == 'Annual':
                    employee_summaries[emp_id]["annual_taken"] += days
                elif l_type == 'Sick':
                    employee_summaries[emp_id]["sick_taken"] += days
                elif l_type == 'Personal':
                    employee_summaries[emp_id]["personal_taken"] += days
            
            elif l_status == 'Pending':
                employee_summaries[emp_id]["pending_days"] += days
        
        # Calculate remaining leave for each employee
        for emp_id, summary in employee_summaries.items():
            summary["annual_remaining"] = summary["annual_entitlement"] - summary["annual_taken"]
            summary["sick_remaining"] = summary["sick_entitlement"] - summary["sick_taken"]
            summary["personal_remaining"] = summary["personal_entitlement"] - summary["personal_taken"]
        
        result_data = {
            "query_type": "all_leave_records",
            "filters": {
                "leave_type": leave_type if leave_type else "All",
                "status": status if status else "All",
                "year": year if year else "All"
            },
            "statistics": stats,
            "employee_summaries": list(employee_summaries.values()),
            "leave_records": leave_records
        }
        
        return {
            "statusCode": 200,
            "body": {
                "tool": "all_leave_records_tool",
                "result": result_data,
                "success": True,
                "note": "This tool is restricted to HR Manager role. Returns all leave records with full details."
            }
        }
        
    except Exception as e:
        print(f"Error retrieving leave records: {e}")
        import traceback
        print(traceback.format_exc())
        return {
            "statusCode": 500,
            "body": {
                "tool": "all_leave_records_tool",
                "error": f"Failed to retrieve leave records: {str(e)}",
                "success": False
            }
        }


# MCP Tool Definition
TOOL_DEFINITION = {
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
}


if __name__ == "__main__":
    # Test the tool locally (requires AWS credentials and DynamoDB table)
    test_events = [
        {},  # All leave records
        {"leave_type": "Annual"},
        {"status": "Approved"},
        {"year": "2024"},
        {"leave_type": "Sick", "status": "Approved"}
    ]

    for test_event in test_events:
        print(f"\n{'='*60}")
        print(f"Testing with: {test_event}")
        print(f"{'='*60}")
        result = lambda_handler(test_event, None)
        print(f"\nTest result:\n{json.dumps(result, indent=2, default=decimal_to_float)}")
