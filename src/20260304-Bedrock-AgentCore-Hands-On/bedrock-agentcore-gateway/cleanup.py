#!/usr/bin/env python3
"""
01-pii-gateway-setup.ipynb + 03-migrate-to-policy-engine.ipynb 리소스 전체 삭제

사용법:
  python3 cleanup.py          # 확인 후 삭제
  python3 cleanup.py --force   # 확인 없이 즉시 삭제
"""

import sys
import json
import time
from pathlib import Path

project_root = Path(__file__).parent / 'pii-masking-gateway'
sys.path.insert(0, str(project_root))

import boto3
from botocore.exceptions import ClientError
from src.utils.aws_utils import (
    delete_gateway, delete_gateway_targets,
    delete_lambda_functions, delete_iam_role,
    delete_cognito_user_pool, delete_bedrock_guardrail,
    delete_dynamodb_table
)


def load_deployment_info():
    deployment_file = project_root / 'deployment_info.json'
    if not deployment_file.exists():
        print("✗ deployment_info.json이 없습니다.")
        sys.exit(1)
    with open(deployment_file, 'r') as f:
        return json.load(f), deployment_file


def safe(fn, label):
    try:
        fn()
    except Exception as e:
        print(f"  ⚠ {label}: {e}")


def cleanup():
    info, deployment_file = load_deployment_info()
    region = info.get('region', 'us-east-1')
    gateway_id = info.get('gateway_id', '')

    gateway_client = boto3.client('bedrock-agentcore-control', region_name=region)
    logs_client = boto3.client('logs', region_name=region)

    print("=" * 60)
    print(f"Deployment ID: {info['deployment_id']}")
    print(f"Gateway ID:    {gateway_id}")
    print(f"Region:        {region}")
    print(f"Migration:     {info.get('migration_completed', False)}")
    print("=" * 60)

    # 1. Gateway Targets
    print("\n[1/9] Gateway Targets 삭제")
    target_ids = info.get('target_ids', [])
    if gateway_id and target_ids:
        safe(lambda: delete_gateway_targets(gateway_client, gateway_id, target_ids),
             "Target 삭제")
        print(f"  ✓ {len(target_ids)}개 target 삭제")
        time.sleep(5)
    else:
        print("  - 없음")

    # 2. Gateway
    print("\n[2/9] Gateway 삭제")
    if gateway_id:
        safe(lambda: delete_gateway(gateway_client, gateway_id), "Gateway 삭제")
        print(f"  ✓ {gateway_id}")
    else:
        print("  - 없음")

    # 3. Policy Engine + Cedar 정책 (03 노트북)
    print("\n[3/9] Policy Engine + Cedar 정책 삭제")
    pe_id = info.get('policy_engine_id')
    if pe_id:
        # 정책 먼저 삭제
        try:
            policies = gateway_client.list_policies(
                policyEngineId=pe_id, maxResults=100
            ).get('policies', [])
            for p in policies:
                safe(lambda pid=p['policyId']: gateway_client.delete_policy(
                    policyEngineId=pe_id, policyId=pid
                ), f"Policy {p.get('name', p['policyId'])}")
                print(f"  ✓ Policy: {p.get('name', p['policyId'])}")
            # 모든 정책 삭제 완료 대기
            if policies:
                print("  ⏳ 정책 삭제 완료 대기 중...")
                for _ in range(30):
                    remaining = gateway_client.list_policies(
                        policyEngineId=pe_id, maxResults=100
                    ).get('policies', [])
                    if not remaining:
                        break
                    time.sleep(2)
        except Exception as e:
            print(f"  ⚠ Policy 목록 조회: {e}")

        safe(lambda: gateway_client.delete_policy_engine(policyEngineId=pe_id),
             "Policy Engine 삭제")
        print(f"  ✓ Policy Engine: {pe_id}")
    else:
        print("  - 없음 (03 노트북 미실행)")

    # 4. Observability (Logs/Traces) (03 노트북)
    print("\n[4/9] Observability 리소스 삭제")
    if gateway_id:
        # Delivery 연결 삭제
        try:
            deliveries = logs_client.describe_deliveries(limit=50).get('deliveries', [])
            for d in deliveries:
                if gateway_id in d.get('deliverySourceName', ''):
                    safe(lambda did=d['id']: logs_client.delete_delivery(id=did),
                         f"Delivery {d['id']}")
                    print(f"  ✓ Delivery: {d['id']}")
        except Exception:
            pass

        # Sources
        for suffix in ['logs-source', 'traces-source']:
            name = f"{gateway_id}-{suffix}"
            safe(lambda n=name: logs_client.delete_delivery_source(name=n), f"Source {suffix}")

        # Destinations
        for suffix in ['logs-destination', 'traces-destination']:
            name = f"{gateway_id}-{suffix}"
            safe(lambda n=name: logs_client.delete_delivery_destination(name=n), f"Dest {suffix}")

        # Log Group
        log_group = f'/aws/vendedlogs/bedrock-agentcore/{gateway_id}'
        safe(lambda: logs_client.delete_log_group(logGroupName=log_group), "Log Group")
        print("  ✓ 완료")
    else:
        print("  - 없음")

    # 5. Lambda 함수
    print("\n[5/9] Lambda 함수 삭제")
    lambdas = []
    if info.get('lambda_function_name'):
        lambdas.append(info['lambda_function_name'])
    for key in ['request_interceptor_name', 'old_request_interceptor_name']:
        if info.get(key):
            lambdas.append(info[key])
    lambdas.extend(info.get('deployed_tools', []))

    if lambdas:
        safe(lambda: delete_lambda_functions(lambdas, region), "Lambda 삭제")
        print(f"  ✓ {len(lambdas)}개 함수 삭제")
    else:
        print("  - 없음")

    # 6. IAM Roles
    print("\n[6/9] IAM Roles 삭제")
    roles = []
    if info.get('lambda_role_name'):
        roles.append(info['lambda_role_name'])
    if info.get('tool_role_name'):
        roles.append(info['tool_role_name'])
    if info.get('gateway_name'):
        roles.append(f"agentcore-{info['gateway_name']}-role")

    for role in roles:
        safe(lambda r=role: delete_iam_role(r), f"Role {role}")
        print(f"  ✓ {role}")
    if not roles:
        print("  - 없음")

    # 7. DynamoDB 테이블
    print("\n[7/9] DynamoDB 테이블 삭제")
    tables = [
        info.get('employee_permissions_table_name'),
        info.get('employees_table_name'),
        info.get('leave_records_table_name'),
    ]
    tables = [t for t in tables if t]

    for table in tables:
        safe(lambda t=table: delete_dynamodb_table(t, region), f"Table {table}")
        print(f"  ✓ {table}")
    if not tables:
        print("  - 없음")

    # 8. Cognito User Pool
    print("\n[8/9] Cognito User Pool 삭제")
    pool_id = info.get('user_pool_id')
    if pool_id:
        safe(lambda: delete_cognito_user_pool(pool_id, region), "Cognito 삭제")
        print(f"  ✓ {pool_id}")
    else:
        print("  - 없음")

    # 9. Bedrock Guardrails
    print("\n[9/9] Bedrock Guardrails 삭제")
    guardrail_id = info.get('guardrail_id')
    if guardrail_id:
        safe(lambda: delete_bedrock_guardrail(guardrail_id, region), "Guardrail 삭제")
        print(f"  ✓ {guardrail_id}")
    else:
        print("  - 없음")

    # deployment_info.json 삭제
    print()
    if deployment_file.exists():
        deployment_file.unlink()
        print(f"✓ {deployment_file} 삭제")

    print("\n" + "=" * 60)
    print("🧹 모든 리소스 삭제 완료!")
    print("=" * 60)


if __name__ == "__main__":
    if '--force' not in sys.argv:
        resp = input("\n⚠️  모든 AWS 리소스를 삭제합니다. 계속하시겠습니까? (yes/no): ")
        if resp.lower() not in ('yes', 'y'):
            print("취소됨.")
            sys.exit(0)

    cleanup()
