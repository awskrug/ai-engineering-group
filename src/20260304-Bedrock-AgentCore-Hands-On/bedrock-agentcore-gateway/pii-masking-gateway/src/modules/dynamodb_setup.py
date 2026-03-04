"""
DynamoDB setup module for client permissions management and user information
"""

from typing import Dict, List
from src.utils.aws_utils import create_dynamodb_table, batch_write_dynamodb





def setup_employee_permissions_table(table_name: str, region: str) -> str:
    """
    Create DynamoDB table for employee-level permissions management.
    Consolidates role, allowed tools, department, name per employee_id.

    Returns:
        Table name
    """
    print("\n" + "="*40)
    print("Setting up DynamoDB Employee Permissions Table")
    print("="*40)

    create_dynamodb_table(
        table_name=table_name,
        key_schema=[
            {'AttributeName': 'EmployeeID', 'KeyType': 'HASH'}
        ],
        attribute_definitions=[
            {'AttributeName': 'EmployeeID', 'AttributeType': 'S'}
        ],
        region=region
    )

    print(f"✓ DynamoDB employee permissions table created: {table_name}")
    return table_name






def load_employee_permissions(table_name: str, region: str) -> int:
    """
    Load employee-level permissions into DynamoDB table.
    Each record maps EmployeeID -> Role, AllowedTools, Name, Department, Username.

    Args:
        table_name: DynamoDB table name
        region: AWS region

    Returns:
        Number of employee permission records loaded
    """
    print("\n" + "="*40)
    print("Loading Employee Permissions")
    print("="*40)

    employee_permissions = [
        {
            'EmployeeID': 'EMP-001',
            'Role': 'hr-manager',
            'AllowedTools': ['all_employees_tool', 'employee_search_tool', 'all_leave_records_tool', 'employee_leave_tool', 'x_amz_bedrock_agentcore_search'],
            'Name': 'HR Manager',
            'Department': 'Human Resources',
            'Username': 'hr-manager'
        },
        {
            'EmployeeID': 'EMP-002',
            'Role': 'employee',
            'AllowedTools': ['employee_search_tool', 'employee_leave_tool', 'x_amz_bedrock_agentcore_search'],
            'Name': 'Employee 1',
            'Department': 'Engineering',
            'Username': 'employee1'
        },
        {
            'EmployeeID': 'EMP-003',
            'Role': 'employee',
            'AllowedTools': ['employee_search_tool', 'employee_leave_tool', 'x_amz_bedrock_agentcore_search'],
            'Name': 'Employee 2',
            'Department': 'Marketing',
            'Username': 'employee2'
        }
    ]

    count = batch_write_dynamodb(
        table_name=table_name,
        items=employee_permissions,
        region=region
    )

    print(f"✓ Loaded {count} employee permission records")
    for ep in employee_permissions:
        print(f"  {ep['EmployeeID']} ({ep['Username']}): {ep['Role']} - {len(ep['AllowedTools'])} tools")

    return count



def setup_employees_table(region: str) -> str:
    """
    Create DynamoDB table for employee data.
    
    Returns:
        Table name
    """
    print("\n" + "="*40)
    print("Setting up DynamoDB Employees Table")
    print("="*40)
    
    table_name = "Employees"
    
    # Create DynamoDB table
    create_dynamodb_table(
        table_name=table_name,
        key_schema=[
            {'AttributeName': 'employee_id', 'KeyType': 'HASH'}
        ],
        attribute_definitions=[
            {'AttributeName': 'employee_id', 'AttributeType': 'S'}
        ],
        region=region
    )
    
    print(f"✓ DynamoDB employees table created: {table_name}")
    return table_name


def setup_leave_records_table(region: str) -> str:
    """
    Create DynamoDB table for leave records.
    
    Returns:
        Table name
    """
    print("\n" + "="*40)
    print("Setting up DynamoDB Leave Records Table")
    print("="*40)
    
    table_name = "LeaveRecords"
    
    # Create DynamoDB table
    create_dynamodb_table(
        table_name=table_name,
        key_schema=[
            {'AttributeName': 'employee_id', 'KeyType': 'HASH'},
            {'AttributeName': 'leave_id', 'KeyType': 'RANGE'}
        ],
        attribute_definitions=[
            {'AttributeName': 'employee_id', 'AttributeType': 'S'},
            {'AttributeName': 'leave_id', 'AttributeType': 'S'}
        ],
        region=region
    )
    
    print(f"✓ DynamoDB leave records table created: {table_name}")
    return table_name


def load_employee_data(region: str) -> int:
    """
    Load sample employee data into DynamoDB table.
    
    Args:
        region: AWS region
        
    Returns:
        Number of employee records loaded
    """
    print("\n" + "="*40)
    print("Loading Employee Data")
    print("="*40)
    
    table_name = "Employees"
    
    # Sample employee data with leave entitlements
    employees = [
        {
            "employee_id": "EMP-001",
            "name": "Employee 1",
            "department": "Human Resources",
            "position": "HR Manager",
            "email": "employee1@company.com",
            "phone": "+1-555-0101",
            "address": "123 Oak Street, Boston, MA 02101",
            "salary": 85000,
            "hire_date": "2020-03-15",
            "status": "Active",
            "annual_leave_entitlement": 25,
            "sick_leave_entitlement": 10,
            "personal_leave_entitlement": 5
        },
        {
            "employee_id": "EMP-002",
            "name": "Employee 2",
            "department": "Engineering",
            "position": "Senior Developer",
            "email": "employee2@company.com",
            "phone": "+1-555-0102",
            "address": "456 Pine Avenue, Cambridge, MA 02139",
            "salary": 95000,
            "hire_date": "2019-07-22",
            "status": "Active",
            "annual_leave_entitlement": 22,
            "sick_leave_entitlement": 10,
            "personal_leave_entitlement": 5
        },
        {
            "employee_id": "EMP-003",
            "name": "Employee 3",
            "department": "Marketing",
            "position": "Marketing Specialist",
            "email": "employee3@company.com",
            "phone": "+1-555-0103",
            "address": "789 Elm Drive, Somerville, MA 02144",
            "salary": 65000,
            "hire_date": "2021-01-10",
            "status": "Active",
            "annual_leave_entitlement": 20,
            "sick_leave_entitlement": 10,
            "personal_leave_entitlement": 5
        },
        {
            "employee_id": "EMP-004",
            "name": "Employee 4",
            "department": "Finance",
            "position": "Financial Analyst",
            "email": "employee4@company.com",
            "phone": "+1-555-0104",
            "address": "321 Maple Lane, Arlington, MA 02474",
            "salary": 70000,
            "hire_date": "2020-11-05",
            "status": "Active",
            "annual_leave_entitlement": 20,
            "sick_leave_entitlement": 10,
            "personal_leave_entitlement": 5
        },
        {
            "employee_id": "EMP-005",
            "name": "Employee 5",
            "department": "Human Resources",
            "position": "HR Specialist",
            "email": "employee5@company.com",
            "phone": "+1-555-0105",
            "address": "654 Cedar Court, Medford, MA 02155",
            "salary": 58000,
            "hire_date": "2022-02-14",
            "status": "Active",
            "annual_leave_entitlement": 18,
            "sick_leave_entitlement": 10,
            "personal_leave_entitlement": 3
        },
        {
            "employee_id": "EMP-006",
            "name": "Employee 6",
            "department": "Engineering",
            "position": "DevOps Engineer",
            "email": "employee6@company.com",
            "phone": "+1-555-0106",
            "address": "987 Birch Boulevard, Watertown, MA 02472",
            "salary": 88000,
            "hire_date": "2021-08-30",
            "status": "Active",
            "annual_leave_entitlement": 20,
            "sick_leave_entitlement": 10,
            "personal_leave_entitlement": 5
        }
    ]
    
    # Load employee data to DynamoDB
    count = batch_write_dynamodb(
        table_name=table_name,
        items=employees,
        region=region
    )
    
    print(f"✓ Loaded {count} employee records")
    return count


def load_leave_records(region: str) -> int:
    """
    Load sample leave records into DynamoDB table.
    
    Args:
        region: AWS region
        
    Returns:
        Number of leave records loaded
    """
    print("\n" + "="*40)
    print("Loading Leave Records")
    print("="*40)
    
    table_name = "LeaveRecords"
    
    # Sample leave records for all 6 employees
    leave_records = [
        # EMP-001 (Employee 1 - HR Manager)
        {
            "employee_id": "EMP-001",
            "leave_id": "LEAVE-2024-001",
            "leave_type": "Annual",
            "start_date": "2024-07-01",
            "end_date": "2024-07-05",
            "days": 5,
            "status": "Approved",
            "year": 2024,
            "reason": "Summer vacation",
            "approved_by": "System",
            "approved_date": "2024-06-15"
        },
        {
            "employee_id": "EMP-001",
            "leave_id": "LEAVE-2024-002",
            "leave_type": "Sick",
            "start_date": "2024-09-10",
            "end_date": "2024-09-11",
            "days": 2,
            "status": "Approved",
            "year": 2024,
            "reason": "Medical appointment"
        },
        {
            "employee_id": "EMP-001",
            "leave_id": "LEAVE-2024-011",
            "leave_type": "Annual",
            "start_date": "2024-12-20",
            "end_date": "2024-12-27",
            "days": 8,
            "status": "Approved",
            "year": 2024,
            "reason": "Year-end holiday",
            "approved_by": "System",
            "approved_date": "2024-11-15"
        },
        
        # EMP-002 (Employee 2 - Senior Developer)
        {
            "employee_id": "EMP-002",
            "leave_id": "LEAVE-2024-003",
            "leave_type": "Annual",
            "start_date": "2024-08-15",
            "end_date": "2024-08-22",
            "days": 8,
            "status": "Approved",
            "year": 2024,
            "reason": "Family vacation",
            "approved_by": "EMP-001",
            "approved_date": "2024-07-20"
        },
        {
            "employee_id": "EMP-002",
            "leave_id": "LEAVE-2024-004",
            "leave_type": "Personal",
            "start_date": "2024-10-05",
            "end_date": "2024-10-05",
            "days": 1,
            "status": "Pending",
            "year": 2024,
            "reason": "Personal matter"
        },
        {
            "employee_id": "EMP-002",
            "leave_id": "LEAVE-2024-012",
            "leave_type": "Sick",
            "start_date": "2024-11-12",
            "end_date": "2024-11-13",
            "days": 2,
            "status": "Approved",
            "year": 2024,
            "reason": "Flu",
            "approved_by": "EMP-001",
            "approved_date": "2024-11-12"
        },
        
        # EMP-003 (Employee 3 - Marketing Specialist)
        {
            "employee_id": "EMP-003",
            "leave_id": "LEAVE-2024-005",
            "leave_type": "Annual",
            "start_date": "2024-06-10",
            "end_date": "2024-06-14",
            "days": 5,
            "status": "Approved",
            "year": 2024,
            "reason": "Beach vacation",
            "approved_by": "EMP-001",
            "approved_date": "2024-05-25"
        },
        {
            "employee_id": "EMP-003",
            "leave_id": "LEAVE-2024-013",
            "leave_type": "Annual",
            "start_date": "2024-09-02",
            "end_date": "2024-09-06",
            "days": 5,
            "status": "Approved",
            "year": 2024,
            "reason": "Long weekend trip",
            "approved_by": "EMP-001",
            "approved_date": "2024-08-15"
        },
        
        # EMP-004 (Employee 4 - Financial Analyst)
        {
            "employee_id": "EMP-004",
            "leave_id": "LEAVE-2024-006",
            "leave_type": "Annual",
            "start_date": "2024-05-20",
            "end_date": "2024-05-24",
            "days": 5,
            "status": "Approved",
            "year": 2024,
            "reason": "Spring break",
            "approved_by": "EMP-001",
            "approved_date": "2024-05-01"
        },
        {
            "employee_id": "EMP-004",
            "leave_id": "LEAVE-2024-007",
            "leave_type": "Sick",
            "start_date": "2024-07-15",
            "end_date": "2024-07-16",
            "days": 2,
            "status": "Approved",
            "year": 2024,
            "reason": "Cold",
            "approved_by": "EMP-001",
            "approved_date": "2024-07-15"
        },
        {
            "employee_id": "EMP-004",
            "leave_id": "LEAVE-2024-014",
            "leave_type": "Annual",
            "start_date": "2024-11-25",
            "end_date": "2024-11-29",
            "days": 5,
            "status": "Approved",
            "year": 2024,
            "reason": "Thanksgiving holiday",
            "approved_by": "EMP-001",
            "approved_date": "2024-10-20"
        },
        
        # EMP-005 (Employee 5 - HR Specialist)
        {
            "employee_id": "EMP-005",
            "leave_id": "LEAVE-2024-008",
            "leave_type": "Annual",
            "start_date": "2024-04-08",
            "end_date": "2024-04-12",
            "days": 5,
            "status": "Approved",
            "year": 2024,
            "reason": "Family visit",
            "approved_by": "EMP-001",
            "approved_date": "2024-03-25"
        },
        {
            "employee_id": "EMP-005",
            "leave_id": "LEAVE-2024-009",
            "leave_type": "Personal",
            "start_date": "2024-08-05",
            "end_date": "2024-08-05",
            "days": 1,
            "status": "Approved",
            "year": 2024,
            "reason": "Moving day",
            "approved_by": "EMP-001",
            "approved_date": "2024-07-30"
        },
        {
            "employee_id": "EMP-005",
            "leave_id": "LEAVE-2024-015",
            "leave_type": "Sick",
            "start_date": "2024-10-22",
            "end_date": "2024-10-22",
            "days": 1,
            "status": "Approved",
            "year": 2024,
            "reason": "Doctor appointment",
            "approved_by": "EMP-001",
            "approved_date": "2024-10-22"
        },
        
        # EMP-006 (Employee 6 - DevOps Engineer)
        {
            "employee_id": "EMP-006",
            "leave_id": "LEAVE-2024-010",
            "leave_type": "Annual",
            "start_date": "2024-03-18",
            "end_date": "2024-03-22",
            "days": 5,
            "status": "Approved",
            "year": 2024,
            "reason": "Ski trip",
            "approved_by": "EMP-001",
            "approved_date": "2024-03-01"
        },
        {
            "employee_id": "EMP-006",
            "leave_id": "LEAVE-2024-016",
            "leave_type": "Annual",
            "start_date": "2024-10-14",
            "end_date": "2024-10-18",
            "days": 5,
            "status": "Approved",
            "year": 2024,
            "reason": "Conference attendance",
            "approved_by": "EMP-001",
            "approved_date": "2024-09-20"
        },
        {
            "employee_id": "EMP-006",
            "leave_id": "LEAVE-2024-017",
            "leave_type": "Personal",
            "start_date": "2024-12-02",
            "end_date": "2024-12-02",
            "days": 1,
            "status": "Pending",
            "year": 2024,
            "reason": "Personal appointment"
        }
    ]
    
    # Load leave records to DynamoDB
    count = batch_write_dynamodb(
        table_name=table_name,
        items=leave_records,
        region=region
    )
    
    print(f"✓ Loaded {count} leave records")
    return count


