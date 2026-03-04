"""
새로운 사용자 추가 테스트 스크립트

사용법:
    python pii-masking-gateway/scripts/add_new_user.py

이 스크립트는 다음 3가지를 수행합니다:
1. EmployeePermissions 테이블에 권한 추가
2. Employees 테이블에 직원 데이터 추가
3. 웹 데모 backend/services.py의 USERS_DB에 추가할 코드 안내

실행 전 01-pii-gateway-setup.ipynb를 먼저 완료해야 합니다.
"""

import json
import boto3
from pathlib import Path


def load_deployment_info():
    """deployment_info.json에서 배포 정보를 로드합니다."""
    deployment_file = Path(__file__).parent.parent / 'deployment_info.json'
    if not deployment_file.exists():
        print("❌ deployment_info.json을 찾을 수 없습니다.")
        print("   먼저 01-pii-gateway-setup.ipynb를 실행해주세요.")
        return None
    with open(deployment_file, 'r') as f:
        return json.load(f)


def add_employee_permission(table_name, region, employee_id, username, role, name, department, allowed_tools):
    """EmployeePermissions 테이블에 권한을 추가합니다."""
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)

    item = {
        'EmployeeID': employee_id,
        'Username': username,
        'Role': role,
        'Name': name,
        'Department': department,
        'AllowedTools': allowed_tools
    }

    table.put_item(Item=item)
    print(f"✓ EmployeePermissions에 추가 완료: {employee_id} ({role})")
    return item


def add_employee_data(region, employee):
    """Employees 테이블에 직원 데이터를 추가합니다."""
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table('Employees')

    table.put_item(Item=employee)
    print(f"✓ Employees 테이블에 추가 완료: {employee['employee_id']}")
    return employee


def add_leave_records(region, employee_id, leave_records):
    """LeaveRecords 테이블에 휴가 데이터를 추가합니다."""
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table('LeaveRecords')

    for record in leave_records:
        record['employee_id'] = employee_id
        table.put_item(Item=record)

    print(f"✓ LeaveRecords 테이블에 {len(leave_records)}건 추가 완료: {employee_id}")
    return leave_records


def add_user_to_services_py(username, user_data):
    """hr-web-demo/backend/services.py의 USERS_DB에 새 사용자를 자동 추가합니다."""
    services_file = Path(__file__).parent.parent.parent / 'hr-web-demo' / 'backend' / 'services.py'
    if not services_file.exists():
        print(f"⚠ services.py를 찾을 수 없습니다: {services_file}")
        return False

    content = services_file.read_text()

    # 이미 추가되어 있는지 확인
    if f'"{username}"' in content:
        print(f"⚠ services.py에 이미 '{username}' 사용자가 있습니다")
        return True

    # USERS_DB 딕셔너리의 마지막 닫는 중괄호(})를 찾아서 그 앞에 삽입
    # USERS_DB = { ... } 패턴에서 마지막 } 앞에 추가
    import re
    entry = json.dumps(user_data, indent=8, ensure_ascii=False)
    new_entry = f'    "{username}": {entry},\n'

    # "USERS_DB = {" 이후의 마지막 "}" 를 찾아서 그 앞에 삽입
    # 마지막 사용자 블록의 닫는 중괄호(},) 뒤에 새 항목 삽입
    marker = '\n}\n\n\nclass HRGatewayService'
    if marker in content:
        # 마지막 항목의 trailing comma 유무에 관계없이 올바르게 삽입
        # marker 직전의 공백/줄바꿈을 포함해서 찾기
        insert_pos = content.index(marker)
        # marker 직전 문자가 ',' 이면 추가 comma 불필요
        before = content[:insert_pos].rstrip()
        if before.endswith(','):
            content = before + f'\n{new_entry}' + content[insert_pos:]
        else:
            content = before + f',\n{new_entry}' + content[insert_pos:]
        services_file.write_text(content)
        print(f"✓ services.py USERS_DB에 '{username}' 추가 완료")
        return True
    else:
        print(f"⚠ services.py에서 삽입 위치를 찾을 수 없습니다. 수동으로 추가해주세요.")
        return False


def verify_data(table_name, region, employee_id):
    """추가된 데이터를 조회하여 확인합니다."""
    dynamodb = boto3.resource('dynamodb', region_name=region)

    # EmployeePermissions 확인
    perm_table = dynamodb.Table(table_name)
    perm_response = perm_table.get_item(Key={'EmployeeID': employee_id})
    perm_item = perm_response.get('Item')

    # Employees 확인
    emp_table = dynamodb.Table('Employees')
    emp_response = emp_table.get_item(Key={'employee_id': employee_id})
    emp_item = emp_response.get('Item')

    return perm_item, emp_item


def main():
    print("=" * 60)
    print("새로운 사용자 추가 테스트")
    print("=" * 60)

    # 1. 배포 정보 로드
    info = load_deployment_info()
    if not info:
        return

    region = info['region']
    perm_table_name = info['employee_permissions_table_name']

    print(f"\n배포 정보:")
    print(f"  Region: {region}")
    print(f"  Permissions Table: {perm_table_name}")

    # ──────────────────────────────────────────────
    # 여기서 새 사용자 정보를 수정하세요
    # ──────────────────────────────────────────────
    NEW_EMPLOYEE_ID = "EMP-007"
    NEW_USERNAME = "employee7"
    NEW_ROLE = "employee"  # "hr-manager" 또는 "employee"
    NEW_NAME = "Employee 7"
    NEW_DEPARTMENT = "Finance"
    NEW_POSITION = "Financial Analyst"
    NEW_PASSWORD = "finance2024!"

    # employee 역할의 기본 도구
    EMPLOYEE_TOOLS = ["employee_search_tool", "employee_leave_tool", "x_amz_bedrock_agentcore_search"]
    # hr-manager 역할의 전체 도구
    HR_MANAGER_TOOLS = ["all_employees_tool", "employee_search_tool", "all_leave_records_tool", "employee_leave_tool", "x_amz_bedrock_agentcore_search"]

    allowed_tools = HR_MANAGER_TOOLS if NEW_ROLE == "hr-manager" else EMPLOYEE_TOOLS

    # 2. EmployeePermissions 추가
    print(f"\n--- Step 1: EmployeePermissions 추가 ---")
    add_employee_permission(
        table_name=perm_table_name,
        region=region,
        employee_id=NEW_EMPLOYEE_ID,
        username=NEW_USERNAME,
        role=NEW_ROLE,
        name=NEW_NAME,
        department=NEW_DEPARTMENT,
        allowed_tools=allowed_tools
    )

    # 3. Employees 테이블 추가
    print(f"\n--- Step 2: Employees 테이블 추가 ---")
    employee_data = {
        'employee_id': NEW_EMPLOYEE_ID,
        'name': NEW_NAME,
        'department': NEW_DEPARTMENT,
        'position': NEW_POSITION,
        'email': f'{NEW_USERNAME}@company.com',
        'phone': '+1-555-0107',
        'address': '321 Maple Lane, Arlington, MA 02474',
        'salary': 70000,
        'hire_date': '2020-11-05',
        'status': 'Active'
    }
    add_employee_data(region, employee_data)

    # 4. LeaveRecords 추가
    print(f"\n--- Step 3: LeaveRecords 추가 ---")
    sample_leave_records = [
        {
            "leave_id": f"LEAVE-2024-{NEW_EMPLOYEE_ID.split('-')[1]}01",
            "leave_type": "Annual",
            "start_date": "2024-08-05",
            "end_date": "2024-08-09",
            "days": 5,
            "status": "Approved",
            "year": 2024,
            "reason": "Summer vacation",
            "approved_by": "EMP-001",
            "approved_date": "2024-07-20"
        },
        {
            "leave_id": f"LEAVE-2024-{NEW_EMPLOYEE_ID.split('-')[1]}02",
            "leave_type": "Sick",
            "start_date": "2024-10-15",
            "end_date": "2024-10-16",
            "days": 2,
            "status": "Approved",
            "year": 2024,
            "reason": "Medical appointment",
            "approved_by": "EMP-001",
            "approved_date": "2024-10-15"
        },
        {
            "leave_id": f"LEAVE-2024-{NEW_EMPLOYEE_ID.split('-')[1]}03",
            "leave_type": "Personal",
            "start_date": "2024-12-23",
            "end_date": "2024-12-24",
            "days": 2,
            "status": "Pending",
            "year": 2024,
            "reason": "Year-end personal matter"
        }
    ]
    add_leave_records(region, NEW_EMPLOYEE_ID, sample_leave_records)

    # 5. 데이터 확인
    print(f"\n--- Step 4: 데이터 확인 ---")
    perm_item, emp_item = verify_data(perm_table_name, region, NEW_EMPLOYEE_ID)

    if perm_item:
        print(f"✓ EmployeePermissions 확인:")
        print(f"  Role: {perm_item.get('Role')}")
        print(f"  AllowedTools: {perm_item.get('AllowedTools')}")
    else:
        print("❌ EmployeePermissions 데이터를 찾을 수 없습니다")

    if emp_item:
        print(f"✓ Employees 확인:")
        print(f"  Name: {emp_item.get('name')}")
        print(f"  Department: {emp_item.get('department')}")
        print(f"  Email: {emp_item.get('email')}")
    else:
        print("❌ Employees 데이터를 찾을 수 없습니다")

    # 6. 웹 데모 services.py 자동 업데이트
    print(f"\n--- Step 5: 웹 데모 USERS_DB 업데이트 ---")
    users_db_entry = {
        "password": NEW_PASSWORD,
        "role": NEW_ROLE,
        "name": NEW_NAME,
        "employee_id": NEW_EMPLOYEE_ID,
        "department": NEW_DEPARTMENT,
        "position": NEW_POSITION
    }
    add_user_to_services_py(NEW_USERNAME, users_db_entry)

    print(f"\n{'=' * 60}")
    print(f"✓ 완료! {NEW_NAME} ({NEW_EMPLOYEE_ID}) 사용자가 추가되었습니다.")
    print(f"  Gateway 테스트: {NEW_ROLE} 권한으로 도구 호출 가능")
    print(f"  휴가 기록: {len(sample_leave_records)}건 추가됨")
    print(f"  웹 데모: {NEW_USERNAME} / {NEW_PASSWORD} 로 로그인")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
