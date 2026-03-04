"""
AWS utility functions for PII Masking Gateway deployment
"""

import boto3
import json
import time
from boto3.session import Session
import botocore
from botocore.exceptions import ClientError
import requests
import zipfile
import io
from pathlib import Path
from typing import Dict, List, Optional, Any


def get_or_create_user_pool(cognito, user_pool_name: str) -> str:
    """Get existing user pool or create a new one."""
    response = cognito.list_user_pools(MaxResults=60)
    for pool in response["UserPools"]:
        if pool["Name"] == user_pool_name:
            user_pool_id = pool["Id"]
            response = cognito.describe_user_pool(UserPoolId=user_pool_id)
            
            # Get the domain from user pool description
            user_pool = response.get('UserPool', {})
            domain = user_pool.get('Domain')
            
            if domain:
                region = user_pool_id.split('_')[0] if '_' in user_pool_id else 'us-east-1'
                domain_url = f"https://{domain}.auth.{region}.amazoncognito.com"
                print(f"Found domain for user pool {user_pool_id}: {domain} ({domain_url})")
            else:
                print(f"No domains found for user pool {user_pool_id}")
            return pool["Id"]
    
    print('Creating new user pool')
    created = cognito.create_user_pool(PoolName=user_pool_name)
    user_pool_id = created["UserPool"]["Id"]
    user_pool_id_without_underscore_lc = user_pool_id.replace("_", "").lower()
    cognito.create_user_pool_domain(
        Domain=user_pool_id_without_underscore_lc,
        UserPoolId=user_pool_id
    )
    print("Domain created as well")
    return created["UserPool"]["Id"]


def get_or_create_resource_server(cognito, user_pool_id: str, resource_server_id: str, 
                                 resource_server_name: str, scopes: List[Dict]) -> str:
    """Get existing resource server or create a new one."""
    try:
        existing = cognito.describe_resource_server(
            UserPoolId=user_pool_id,
            Identifier=resource_server_id
        )
        return resource_server_id
    except cognito.exceptions.ResourceNotFoundException:
        print('Creating new resource server')
        cognito.create_resource_server(
            UserPoolId=user_pool_id,
            Identifier=resource_server_id,
            Name=resource_server_name,
            Scopes=scopes
        )
        return resource_server_id


def get_or_create_m2m_client(cognito, user_pool_id: str, client_name: str, 
                           resource_server_id: str, scopes: Optional[List[str]] = None) -> tuple:
    """Get existing M2M client or create a new one."""
    response = cognito.list_user_pool_clients(UserPoolId=user_pool_id, MaxResults=60)
    for client in response["UserPoolClients"]:
        if client["ClientName"] == client_name:
            describe = cognito.describe_user_pool_client(UserPoolId=user_pool_id, ClientId=client["ClientId"])
            return client["ClientId"], describe["UserPoolClient"]["ClientSecret"]
    
    print('Creating new M2M client')

    # Default scopes if not provided
    if scopes is None:
        scopes = [f"{resource_server_id}/gateway:read", f"{resource_server_id}/gateway:write"]

    created = cognito.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=client_name,
        GenerateSecret=True,
        AllowedOAuthFlows=["client_credentials"],
        AllowedOAuthScopes=scopes,
        AllowedOAuthFlowsUserPoolClient=True,
        SupportedIdentityProviders=["COGNITO"],
        ExplicitAuthFlows=["ALLOW_REFRESH_TOKEN_AUTH"]
    )
    return created["UserPoolClient"]["ClientId"], created["UserPoolClient"]["ClientSecret"]


def get_token(user_pool_id: str, client_id: str, client_secret: str, 
              scope_string: str, region: str) -> Dict:
    """Get OAuth token using client credentials flow."""
    try:
        user_pool_id_without_underscore = user_pool_id.replace("_", "")
        url = f"https://{user_pool_id_without_underscore}.auth.{region}.amazoncognito.com/oauth2/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": scope_string,
        }
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as err:
        return {"error": str(err)}


def create_agentcore_gateway_role_with_region(gateway_name: str, region: str) -> Dict:
    """Create an IAM role for AgentCore Gateway with explicit region specification."""
    iam_client = boto3.client('iam')
    agentcore_gateway_role_name = f'agentcore-{gateway_name}-role'
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    
    role_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "AmazonBedrockAgentCoreGatewayLambda",
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction"
            ],
            "Resource": f"arn:aws:lambda:{region}:{account_id}:function:*"
        }]
    }

    assume_role_policy_document = {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "AssumeRolePolicy",
            "Effect": "Allow",
            "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {"aws:SourceAccount": f"{account_id}"},
                "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock-agentcore:{region}:{account_id}:*"}
            }
        }]
    }

    assume_role_policy_document_json = json.dumps(assume_role_policy_document)
    role_policy_document = json.dumps(role_policy)
    
    try:
        agentcore_iam_role = iam_client.create_role(
            RoleName=agentcore_gateway_role_name,
            AssumeRolePolicyDocument=assume_role_policy_document_json
        )
        time.sleep(10)
    except iam_client.exceptions.EntityAlreadyExistsException:
        print("Role already exists -- deleting and creating it again")
        policies = iam_client.list_role_policies(
            RoleName=agentcore_gateway_role_name,
            MaxItems=100
        )
        print("policies:", policies)
        for policy_name in policies['PolicyNames']:
            iam_client.delete_role_policy(
                RoleName=agentcore_gateway_role_name,
                PolicyName=policy_name
            )
        print(f"deleting {agentcore_gateway_role_name}")
        iam_client.delete_role(RoleName=agentcore_gateway_role_name)
        print(f"recreating {agentcore_gateway_role_name}")
        agentcore_iam_role = iam_client.create_role(
            RoleName=agentcore_gateway_role_name,
            AssumeRolePolicyDocument=assume_role_policy_document_json
        )

    print(f"attaching role policy {agentcore_gateway_role_name}")
    try:
        iam_client.put_role_policy(
            PolicyDocument=role_policy_document,
            PolicyName="AgentCorePolicy",
            RoleName=agentcore_gateway_role_name
        )
    except Exception as e:
        print(e)

    return agentcore_iam_role


def create_lambda_role(role_name: str, description: str = 'Lambda execution role') -> str:
    """Create basic IAM role for Lambda with execution permissions."""
    iam_client = boto3.client('iam')
    
    # Trust policy for Lambda
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }
    
    try:
        role_response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=description
        )
        role_arn = role_response['Role']['Arn']
        print(f"✓ IAM role created: {role_name}")
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            print(f"⚠ Role already exists: {role_name}")
            role_response = iam_client.get_role(RoleName=role_name)
            role_arn = role_response['Role']['Arn']
        else:
            raise
    
    # Attach basic Lambda execution policy
    iam_client.attach_role_policy(
        RoleName=role_name,
        PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
    )
    
    # Wait for role to propagate
    time.sleep(10)
    
    return role_arn


def deploy_lambda_function(function_name: str, role_arn: str, lambda_code_path: str, 
                         environment_vars: Optional[Dict] = None, description: str = 'Lambda function',
                         timeout: int = 30, memory_size: int = 256, region: str = 'us-east-1') -> str:
    """Deploy Lambda function from Python code file."""
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Read Lambda code
    lambda_code_path = Path(lambda_code_path)
    if not lambda_code_path.exists():
        raise FileNotFoundError(f"Lambda code not found: {lambda_code_path}")
    
    with open(lambda_code_path, 'r') as f:
        lambda_code = f.read()
    
    # Create deployment package
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr('lambda_function.py', lambda_code)
    
    zip_buffer.seek(0)
    deployment_package = zip_buffer.read()
    
    # Build function config
    function_config = {
        'FunctionName': function_name,
        'Runtime': 'python3.14',
        'Role': role_arn,
        'Handler': 'lambda_function.lambda_handler',
        'Code': {'ZipFile': deployment_package},
        'Description': description,
        'Timeout': timeout,
        'MemorySize': memory_size
    }
    
    # Add environment variables if provided
    if environment_vars:
        function_config['Environment'] = {'Variables': environment_vars}
    
    try:
        response = lambda_client.create_function(**function_config)
        lambda_arn = response['FunctionArn']
        print(f"✓ Lambda created: {function_name}")
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceConflictException':
            print(f"⚠ Lambda already exists: {function_name}")
            response = lambda_client.get_function(FunctionName=function_name)
            lambda_arn = response['Configuration']['FunctionArn']
        else:
            raise
    
    return lambda_arn


def grant_gateway_invoke_permission(function_name: str, region: str = 'us-east-1'):
    """Grant Gateway permission to invoke the Lambda interceptor."""
    lambda_client = boto3.client('lambda', region_name=region)
    sts_client = boto3.client('sts')
    account_id = sts_client.get_caller_identity()['Account']
    
    try:
        lambda_client.add_permission(
            FunctionName=function_name,
            StatementId='AllowGatewayInvoke',
            Action='lambda:InvokeFunction',
            Principal='bedrock-agentcore.amazonaws.com',
            SourceArn=f'arn:aws:bedrock-agentcore:{region}:{account_id}:gateway/*'
        )
        print(f"✓ Gateway invoke permission added to Lambda")
        print(f"  Principal: bedrock-agentcore.amazonaws.com")
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceConflictException':
            print(f"⚠ Permission already exists (this is fine)")
        else:
            print(f"⚠ Error adding permission: {e}")
            raise


def delete_gateway(gateway_client, gateway_id: str):
    """Delete gateway and all its targets."""
    print("Deleting all targets for gateway", gateway_id)
    list_response = gateway_client.list_gateway_targets(
        gatewayIdentifier=gateway_id,
        maxResults=100
    )
    for item in list_response['items']:
        target_id = item["targetId"]
        print("Deleting target ", target_id)
        gateway_client.delete_gateway_target(
            gatewayIdentifier=gateway_id,
            targetId=target_id
        )
        time.sleep(5)
    print("Deleting gateway ", gateway_id)
    gateway_client.delete_gateway(gatewayIdentifier=gateway_id)


def delete_gateway_targets(gateway_client, gateway_id: str, target_ids: List[str]):
    """Delete multiple gateway targets."""
    print(f"Deleting {len(target_ids)} gateway targets...")
    for target_id in target_ids:
        try:
            gateway_client.delete_gateway_target(
                gatewayIdentifier=gateway_id,
                targetId=target_id
            )
            print(f"  ✓ Deleted target: {target_id}")
        except Exception as e:
            print(f"  ✗ Failed to delete target {target_id}: {e}")
        time.sleep(2)


def delete_lambda_functions(function_names: List[str], region: str = 'us-east-1'):
    """Delete multiple Lambda functions."""
    lambda_client = boto3.client('lambda', region_name=region)
    print(f"Deleting {len(function_names)} Lambda functions...")
    
    for function_name in function_names:
        try:
            lambda_client.delete_function(FunctionName=function_name)
            print(f"  ✓ Deleted Lambda: {function_name}")
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                print(f"  ✗ Failed to delete {function_name}: {e}")
        time.sleep(1)


def delete_iam_role(role_name: str):
    """Delete IAM role and its attached policies."""
    iam_client = boto3.client('iam')
    
    try:
        # Detach managed policies
        attached_policies = iam_client.list_attached_role_policies(RoleName=role_name)
        for policy in attached_policies['AttachedPolicies']:
            iam_client.detach_role_policy(
                RoleName=role_name,
                PolicyArn=policy['PolicyArn']
            )
        
        # Delete inline policies
        inline_policies = iam_client.list_role_policies(RoleName=role_name)
        for policy_name in inline_policies['PolicyNames']:
            iam_client.delete_role_policy(
                RoleName=role_name,
                PolicyName=policy_name
            )
        
        # Delete role
        iam_client.delete_role(RoleName=role_name)
        print(f"✓ Deleted IAM role: {role_name}")
        
    except ClientError as e:
        if e.response['Error']['Code'] != 'NoSuchEntity':
            print(f"✗ Failed to delete role {role_name}: {e}")


def delete_cognito_user_pool(user_pool_id: str, region: str = 'us-east-1'):
    """Delete Cognito user pool (domain must be deleted first)."""
    import time
    cognito_client = boto3.client('cognito-idp', region_name=region)

    try:
        # Domain을 먼저 삭제해야 User Pool 삭제 가능
        pool_info = cognito_client.describe_user_pool(UserPoolId=user_pool_id)
        domain = pool_info.get('UserPool', {}).get('Domain')
        if domain:
            cognito_client.delete_user_pool_domain(
                Domain=domain, UserPoolId=user_pool_id
            )
            print(f"  ✓ Deleted Cognito domain: {domain}")
            # 도메인 삭제 완료 대기
            for _ in range(30):
                try:
                    resp = cognito_client.describe_user_pool_domain(Domain=domain)
                    status = resp.get('DomainDescription', {}).get('Status')
                    if not status or status == 'DELETED':
                        break
                except ClientError:
                    break
                time.sleep(2)

        cognito_client.delete_user_pool(UserPoolId=user_pool_id)
        print(f"✓ Deleted Cognito user pool: {user_pool_id}")
    except ClientError as e:
        if e.response['Error']['Code'] != 'ResourceNotFoundException':
            print(f"✗ Failed to delete user pool: {e}")


def create_bedrock_guardrail(guardrail_name: str, pii_entity_config: Dict, region: str = 'us-east-1') -> tuple:
    """Create Bedrock Guardrail with PII detection configuration."""
    bedrock_client = boto3.client('bedrock', region_name=region)
    
    try:
        # Create the guardrail
        guardrail_response = bedrock_client.create_guardrail(
            name=guardrail_name,
            description='Guardrail for anonymizing sensitive PII data in tool responses',
            sensitiveInformationPolicyConfig=pii_entity_config,
            blockedInputMessaging='Input contains sensitive information that has been anonymized.',
            blockedOutputsMessaging='Output contains sensitive information that has been anonymized.'
        )
        
        guardrail_id = guardrail_response['guardrailId']
        guardrail_arn = guardrail_response['guardrailArn']
        
        print(f"✓ Guardrail created: {guardrail_id}")
        print(f"  ARN: {guardrail_arn}")
        
        # Create a version of the guardrail
        print("\nCreating guardrail version...")
        version_response = bedrock_client.create_guardrail_version(
            guardrailIdentifier=guardrail_id,
            description='Initial version with PII anonymization'
        )
        
        guardrail_version = version_response['version']
        print(f"✓ Guardrail version created: {guardrail_version}")
        
        return guardrail_id, guardrail_version, guardrail_arn
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ConflictException':
            print(f"⚠ Guardrail with name '{guardrail_name}' already exists")
            # List existing guardrails to get the ID
            list_response = bedrock_client.list_guardrails()
            for guardrail in list_response.get('guardrails', []):
                if guardrail['name'] == guardrail_name:
                    guardrail_id = guardrail['id']
                    guardrail_arn = guardrail['arn']
                    print(f"  Using existing guardrail: {guardrail_id}")
                    
                    # Get the latest version of the existing guardrail
                    try:
                        get_response = bedrock_client.get_guardrail(
                            guardrailIdentifier=guardrail_id
                        )
                        guardrail_version = get_response.get('version', 'DRAFT')
                        print(f"  Guardrail version: {guardrail_version}")
                        return guardrail_id, guardrail_version, guardrail_arn
                    except Exception as get_error:
                        print(f"  ⚠ Could not get guardrail version: {get_error}")
                        return guardrail_id, 'DRAFT', guardrail_arn
        else:
            print(f"✗ Failed to create guardrail: {e}")
            raise


def delete_bedrock_guardrail(guardrail_id: str, region: str = 'us-east-1'):
    """Delete Bedrock Guardrail."""
    bedrock_client = boto3.client('bedrock', region_name=region)
    
    try:
        bedrock_client.delete_guardrail(guardrailIdentifier=guardrail_id)
        print(f"✓ Deleted guardrail: {guardrail_id}")
    except Exception as e:
        print(f"⚠ Failed to delete guardrail: {e}")


def delete_dynamodb_table(table_name: str, region: str = 'us-east-1'):
    """Delete DynamoDB table."""
    dynamodb_client = boto3.client('dynamodb', region_name=region)
    
    try:
        dynamodb_client.delete_table(TableName=table_name)
        print(f"✓ Deleted DynamoDB table: {table_name}")
    except ClientError as e:
        if e.response['Error']['Code'] != 'ResourceNotFoundException':
            print(f"✗ Failed to delete table: {e}")


def create_dynamodb_table(table_name: str, key_schema: List, attribute_definitions: List, region: str = 'us-east-1') -> str:
    """Create DynamoDB table with specified schema."""
    dynamodb_client = boto3.client('dynamodb', region_name=region)
    
    try:
        response = dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            BillingMode='PAY_PER_REQUEST'
        )
        
        print(f"✓ Table created: {table_name}")
        
        # Wait for table to be active
        waiter = dynamodb_client.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        print(f"  Table is active")
        
        return table_name
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"⚠ Table already exists: {table_name}")
            return table_name
        else:
            raise


def batch_write_dynamodb(table_name: str, items: List, region: str = 'us-east-1') -> int:
    """Batch write items to DynamoDB table."""
    from datetime import datetime
    
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)
    
    # Batch write
    with table.batch_writer() as batch:
        for item in items:
            # Add timestamps if not present
            if 'CreatedAt' not in item:
                item['CreatedAt'] = datetime.utcnow().isoformat()
            if 'UpdatedAt' not in item:
                item['UpdatedAt'] = datetime.utcnow().isoformat()
            batch.put_item(Item=item)
    
    print(f"✓ Wrote {len(items)} items to {table_name}")
    return len(items)