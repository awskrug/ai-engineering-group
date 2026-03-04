"""
새로운 MCP Tool 추가 스크립트

사용법:
    python pii-masking-gateway/scripts/add_new_tool.py

이 스크립트는 다음 4가지를 수행합니다:
1. 새 도구 Lambda 코드 파일 생성
2. Lambda 함수 배포
3. Gateway Target으로 등록
4. EmployeePermissions에 도구 권한 추가

웹 데모의 agent_service.py는 MCPClient를 통해 Gateway에서 도구를 자동 발견하므로,
별도의 코드 수정 없이 새 도구가 AI Chat에서 바로 사용 가능합니다.

실행 전 01-pii-gateway-setup.ipynb를 먼저 완료해야 합니다.
"""

import sys
import json
import time
import boto3
from pathlib import Path

# 프로젝트 모듈 로드
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.aws_utils import deploy_lambda_function, grant_gateway_invoke_permission


def load_deployment_info():
    """deployment_info.json에서 배포 정보를 로드합니다."""
    deployment_file = project_root / 'deployment_info.json'
    if not deployment_file.exists():
        print("❌ deployment_info.json을 찾을 수 없습니다.")
        print("   먼저 01-pii-gateway-setup.ipynb를 실행해주세요.")
        return None
    with open(deployment_file, 'r') as f:
        return json.load(f)


# ──────────────────────────────────────────────
# 새 도구 설정 (여기를 수정하세요)
# ──────────────────────────────────────────────
NEW_TOOL_NAME = "department_stats_tool"
NEW_TOOL_DESCRIPTION = "부서별 통계 정보를 조회합니다 (직원 수, 평균 근속 연수 등)"

NEW_TOOL_DEFINITION = {
    "name": NEW_TOOL_NAME,
    "description": NEW_TOOL_DESCRIPTION,
    "inputSchema": {
        "type": "object",
        "properties": {
            "department": {
                "type": "string",
                "description": "조회할 부서명 (예: Engineering, Marketing, Finance)"
            }
        },
        "required": ["department"]
    }
}

# 이 도구를 사용할 수 있는 직원 ID 목록
GRANT_TO_EMPLOYEES = ["EMP-001"]  # hr-manager에게 권한 부여


def create_tool_lambda_code(tool_name, description):
    """새 도구의 Lambda 코드를 생성합니다."""
    return f'''"""
{description}
"""

import json
import os
import boto3
from boto3.dynamodb.conditions import Attr
from collections import Counter
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
EMPLOYEES_TABLE_NAME = os.environ.get('EMPLOYEES_TABLE_NAME', 'Employees')


def lambda_handler(event, context):
    """Lambda handler for {tool_name}."""
    print(f"{tool_name} received event: {{json.dumps(event)}}")

    body = event if isinstance(event, dict) else json.loads(event)
    department = body.get('department')

    if not department:
        return {{
            "statusCode": 400,
            "body": {{
                "tool": "{tool_name}",
                "error": "department 파라미터가 필요합니다",
                "success": False,
                "examples": {{"department": "Engineering"}}
            }}
        }}

    try:
        table = dynamodb.Table(EMPLOYEES_TABLE_NAME)

        response = table.scan(
            FilterExpression=Attr('department').eq(department)
        )
        employees = response.get('Items', [])

        if not employees:
            return {{
                "statusCode": 404,
                "body": {{
                    "tool": "{tool_name}",
                    "error": f"'{{department}}' 부서를 찾을 수 없습니다",
                    "success": False
                }}
            }}

        # 통계 계산
        total = len(employees)
        positions = Counter(emp.get('position', 'Unknown') for emp in employees)
        statuses = Counter(emp.get('status', 'Unknown') for emp in employees)

        result = {{
            "department": department,
            "total_employees": total,
            "positions": dict(positions),
            "statuses": dict(statuses),
            "employee_names": [emp.get('name', 'Unknown') for emp in employees]
        }}

        return {{
            "statusCode": 200,
            "body": {{
                "tool": "{tool_name}",
                "result": result,
                "success": True
            }}
        }}

    except Exception as e:
        print(f"Error: {{e}}")
        return {{
            "statusCode": 500,
            "body": {{
                "tool": "{tool_name}",
                "error": str(e),
                "success": False
            }}
        }}
'''


def step1_create_lambda_code(tool_name, description):
    """Step 1: Lambda 코드 파일 생성"""
    print("\n--- Step 1: Lambda 코드 파일 생성 ---")

    tool_file = project_root / 'src' / 'tools' / f'{tool_name}.py'
    code = create_tool_lambda_code(tool_name, description)

    tool_file.parent.mkdir(parents=True, exist_ok=True)
    with open(tool_file, 'w') as f:
        f.write(code)

    print(f"✓ Lambda 코드 생성: {tool_file}")
    return tool_file


def step2_deploy_lambda(tool_name, tool_file, deployment_id, region, tool_role_name):
    """Step 2: Lambda 함수 배포"""
    print("\n--- Step 2: Lambda 함수 배포 ---")

    sts_client = boto3.client('sts')
    account_id = sts_client.get_caller_identity()['Account']
    tool_role_arn = f"arn:aws:iam::{account_id}:role/{tool_role_name}"

    function_name = f"{tool_name.replace('_', '-')}-{deployment_id}"

    lambda_arn = deploy_lambda_function(
        function_name=function_name,
        role_arn=tool_role_arn,
        lambda_code_path=str(tool_file),
        environment_vars={'TOOL_NAME': tool_name},
        description=NEW_TOOL_DESCRIPTION,
        region=region
    )

    # Gateway 호출 권한 부여
    grant_gateway_invoke_permission(function_name, region)

    print(f"✓ Lambda 배포 완료: {function_name}")
    print(f"  ARN: {lambda_arn}")
    return lambda_arn, function_name


def step3_register_target(gateway_id, tool_name, lambda_arn, tool_definition, region):
    """Step 3: Gateway Target 등록"""
    print("\n--- Step 3: Gateway Target 등록 ---")

    gateway_client = boto3.client('bedrock-agentcore-control', region_name=region)

    target_name = f"{tool_name.replace('_', '-')}-target"

    response = gateway_client.create_gateway_target(
        gatewayIdentifier=gateway_id,
        name=target_name,
        targetConfiguration={
            "mcp": {
                "lambda": {
                    "lambdaArn": lambda_arn,
                    "toolSchema": {"inlinePayload": [tool_definition]}
                }
            }
        },
        credentialProviderConfigurations=[{
            "credentialProviderType": "GATEWAY_IAM_ROLE"
        }]
    )

    target_id = response['targetId']
    print(f"✓ Target 생성: {target_id}")

    # Target READY 대기
    print("  Target 준비 대기 중...")
    for attempt in range(18):
        status_response = gateway_client.get_gateway_target(
            gatewayIdentifier=gateway_id,
            targetId=target_id
        )
        status = status_response.get('status')
        if status == 'READY':
            print(f"  ✓ Target READY")
            return target_id
        elif status == 'FAILED':
            print(f"  ❌ Target FAILED")
            return None
        time.sleep(10)

    print("  ⚠ Target 준비 타임아웃")
    return target_id


def step4_grant_permissions(perm_table_name, region, tool_name, employee_ids):
    """Step 4: EmployeePermissions에 도구 권한 추가"""
    print("\n--- Step 4: 직원 권한에 도구 추가 ---")

    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table(perm_table_name)

    for emp_id in employee_ids:
        try:
            # 현재 권한 조회
            response = table.get_item(Key={'EmployeeID': emp_id})
            item = response.get('Item')

            if not item:
                print(f"  ⚠ {emp_id}: 직원을 찾을 수 없습니다")
                continue

            current_tools = item.get('AllowedTools', [])
            if tool_name in current_tools:
                print(f"  ⚠ {emp_id}: 이미 {tool_name} 권한이 있습니다")
                continue

            # 도구 추가
            table.update_item(
                Key={'EmployeeID': emp_id},
                UpdateExpression='SET AllowedTools = list_append(AllowedTools, :new_tool)',
                ExpressionAttributeValues={':new_tool': [tool_name]}
            )
            print(f"  ✓ {emp_id} ({item.get('Name', '')}): {tool_name} 권한 추가 완료")

        except Exception as e:
            print(f"  ❌ {emp_id}: 권한 추가 실패 - {e}")


def main():
    print("=" * 60)
    print("새로운 MCP Tool 추가")
    print("=" * 60)

    # 배포 정보 로드
    info = load_deployment_info()
    if not info:
        return

    region = info['region']
    deployment_id = info['deployment_id']
    gateway_id = info['gateway_id']
    perm_table_name = info['employee_permissions_table_name']
    tool_role_name = info['tool_role_name']

    print(f"\n배포 정보:")
    print(f"  Region: {region}")
    print(f"  Deployment ID: {deployment_id}")
    print(f"  Gateway ID: {gateway_id}")
    print(f"\n새 도구: {NEW_TOOL_NAME}")
    print(f"  설명: {NEW_TOOL_DESCRIPTION}")

    # Step 1: Lambda 코드 생성
    tool_file = step1_create_lambda_code(NEW_TOOL_NAME, NEW_TOOL_DESCRIPTION)

    # Step 2: Lambda 배포
    lambda_arn, function_name = step2_deploy_lambda(
        NEW_TOOL_NAME, tool_file, deployment_id, region, tool_role_name
    )

    # Step 3: Gateway Target 등록
    target_id = step3_register_target(
        gateway_id, NEW_TOOL_NAME, lambda_arn, NEW_TOOL_DEFINITION, region
    )

    # Step 4: 직원 권한 추가
    step4_grant_permissions(perm_table_name, region, NEW_TOOL_NAME, GRANT_TO_EMPLOYEES)

    # 결과 요약
    print(f"\n{'=' * 60}")
    print(f"✓ 완료! {NEW_TOOL_NAME} 도구가 추가되었습니다.")
    print(f"  Lambda: {function_name}")
    print(f"  Target ID: {target_id}")
    print(f"  권한 부여: {GRANT_TO_EMPLOYEES}")
    print(f"\n  웹 데모의 agent_service.py는 MCPClient를 통해 Gateway에서")
    print(f"  도구를 자동 발견하므로, 별도 코드 수정 없이 AI Chat에서 바로 사용 가능합니다.")
    print(f"\n다른 직원에게도 권한을 부여하려면 GRANT_TO_EMPLOYEES 리스트를 수정하세요.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
