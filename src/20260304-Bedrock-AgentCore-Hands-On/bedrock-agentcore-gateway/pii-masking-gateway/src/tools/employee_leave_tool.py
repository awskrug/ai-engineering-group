"""
Employee Leave Tool - Retrieve leave records for a specific employee from DynamoDB

This tool allows querying leave information for a specific employee.
- HR Manager: Can view any employee's leave records
- Regular Employee: Can view their own leave records (enforced by interceptor)
"""

import json
import os
import boto3
from boto3.dynamodb.conditions import Key, Attr
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
    """Lambda handler for employee leave tool."""
    print(f"Employee leave tool received event: {json.dumps(event)}")
    
    # Parse input
    body = event if isinstance(event, dict) else json.loads(event)
    employee_id = body.get('employee_id')
    year = body.get('year')  # Optional filter by year
    leave_type = body.get('leave_type')  # Optional filter by type
    
    if not employee_id:
        return {
            "statusCode": 400,
            "body": {
                "tool": "employee_leave_tool",
                "error": "employee_id is required",
                "success": False,
                "example": {"employee_id": "EMP-001"}
            }
        }
    
    # Employee는 본인 휴가만 조회 가능 (HR Manager는 제한 없음)
    user_context = body.get('_user_context', {})
    if user_context:
        caller_role = user_context.get('role', '')
        caller_id = user_context.get('employee_id', '')
        if caller_role != 'hr-manager' and caller_id and employee_id.upper() != caller_id.upper():
            print(f"[BLOCKED] Employee {caller_id} tried to access leave of {employee_id}")
            return {
                "statusCode": 403,
                "body": {
                    "tool": "employee_leave_tool",
                    "error": f"접근 권한이 없습니다. 본인의 휴가 정보만 조회할 수 있습니다. (본인 ID: {caller_id})",
                    "requested_id": employee_id,
                    "your_id": caller_id,
                    "success": False
                }
            }
    
    try:
        # First, get employee entitlement from Employees table
        employees_table = dynamodb.Table(EMPLOYEES_TABLE_NAME)
        employee_response = employees_table.get_item(Key={'employee_id': employee_id})
        
        if 'Item' not in employee_response:
            return {
                "statusCode": 404,
                "body": {
                    "tool": "employee_leave_tool",
                    "error": f"Employee {employee_id} not found",
                    "success": False
                }
            }
        
        employee_data = employee_response['Item']
        annual_entitlement = int(employee_data.get('annual_leave_entitlement', 20))
        sick_entitlement = int(employee_data.get('sick_leave_entitlement', 10))
        personal_entitlement = int(employee_data.get('personal_leave_entitlement', 5))
        
        # Now get leave records
        table = dynamodb.Table(LEAVE_RECORDS_TABLE_NAME)
        
        # Query by employee_id (assuming it's a GSI or part of the key)
        # If employee_id is the partition key:
        try:
            response = table.query(
                KeyConditionExpression=Key('employee_id').eq(employee_id)
            )
        except:
            # If employee_id is not a key, use scan with filter
            response = table.scan(
                FilterExpression=Attr('employee_id').eq(employee_id)
            )
        
        leave_records = response.get('Items', [])
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            try:
                response = table.query(
                    KeyConditionExpression=Key('employee_id').eq(employee_id),
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
            except:
                response = table.scan(
                    FilterExpression=Attr('employee_id').eq(employee_id),
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
            leave_records.extend(response.get('Items', []))
        
        # Apply additional filters
        if year:
            leave_records = [r for r in leave_records if r.get('year') == int(year)]
        
        if leave_type:
            leave_records = [r for r in leave_records if r.get('leave_type') == leave_type]
        
        if not leave_records:
            return {
                "statusCode": 404,
                "body": {
                    "tool": "employee_leave_tool",
                    "error": f"No leave records found for employee {employee_id}",
                    "success": False,
                    "filters": {
                        "employee_id": employee_id,
                        "year": year,
                        "leave_type": leave_type
                    }
                }
            }
        
        # Calculate leave balance and statistics
        stats = {
            "total_records": len(leave_records),
            "by_type": {},
            "by_status": {},
            "total_days_taken": 0,
            "approved_days": 0,
            "pending_days": 0,
            "annual_entitlement": annual_entitlement,
            "sick_entitlement": sick_entitlement,
            "personal_entitlement": personal_entitlement
        }
        
        annual_taken = 0
        sick_taken = 0
        personal_taken = 0
        
        for record in leave_records:
            # Type statistics
            l_type = record.get('leave_type', 'Unknown')
            stats['by_type'][l_type] = stats['by_type'].get(l_type, 0) + 1
            
            # Status statistics
            l_status = record.get('status', 'Unknown')
            stats['by_status'][l_status] = stats['by_status'].get(l_status, 0) + 1
            
            # Days calculation
            days = record.get('days', 0)
            if isinstance(days, Decimal):
                days = float(days)
            
            stats['total_days_taken'] += days
            
            if l_status == 'Approved':
                stats['approved_days'] += days
                
                # Track by type for approved leaves
                if l_type == 'Annual':
                    annual_taken += days
                elif l_type == 'Sick':
                    sick_taken += days
                elif l_type == 'Personal':
                    personal_taken += days
                    
            elif l_status == 'Pending':
                stats['pending_days'] += days
        
        # Calculate remaining balance
        stats['annual_taken'] = annual_taken
        stats['annual_remaining'] = annual_entitlement - annual_taken
        stats['sick_taken'] = sick_taken
        stats['sick_remaining'] = sick_entitlement - sick_taken
        stats['personal_taken'] = personal_taken
        stats['personal_remaining'] = personal_entitlement - personal_taken
        
        result_data = {
            "query_type": "employee_leave",
            "employee_id": employee_id,
            "filters": {
                "year": year if year else "All",
                "leave_type": leave_type if leave_type else "All"
            },
            "statistics": stats,
            "leave_records": leave_records
        }
        
        return {
            "statusCode": 200,
            "body": {
                "tool": "employee_leave_tool",
                "result": result_data,
                "success": True,
                "note": "Employees can view their own records, HR managers can view any employee's records"
            }
        }
        
    except Exception as e:
        print(f"Error retrieving employee leave records: {e}")
        import traceback
        print(traceback.format_exc())
        return {
            "statusCode": 500,
            "body": {
                "tool": "employee_leave_tool",
                "error": f"Failed to retrieve leave records: {str(e)}",
                "success": False
            }
        }


# MCP Tool Definition
TOOL_DEFINITION = {
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


if __name__ == "__main__":
    # Test the tool locally (requires AWS credentials and DynamoDB table)
    test_events = [
        {"employee_id": "EMP-001"},
        {"employee_id": "EMP-002", "year": "2024"},
        {"employee_id": "EMP-001", "leave_type": "Annual"},
        {}  # Test missing employee_id
    ]

    for test_event in test_events:
        print(f"\n{'='*60}")
        print(f"Testing with: {test_event}")
        print(f"{'='*60}")
        result = lambda_handler(test_event, None)
        print(f"\nTest result:\n{json.dumps(result, indent=2, default=decimal_to_float)}")
