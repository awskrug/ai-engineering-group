"""
Gateway setup module for AgentCore Gateway with interceptors
"""

import time
from typing import Dict, List
from src.utils.aws_utils import create_agentcore_gateway_role_with_region


def setup_gateway_with_dual_interceptors(gateway_name: str, response_lambda_arn: str, 
                                       request_lambda_arn: str, discovery_url: str, 
                                       allowed_client_ids: List[str], region: str, 
                                       gateway_client,
                                       enable_semantic_search: bool = False) -> Dict:
    """
    Setup AgentCore Gateway with both REQUEST and RESPONSE interceptors.
    
    Args:
        gateway_name: Name for the Gateway
        response_lambda_arn: ARN of the Response Interceptor Lambda
        request_lambda_arn: ARN of the Request Interceptor Lambda
        discovery_url: Cognito discovery URL
        allowed_client_ids: List of allowed Cognito client IDs
        region: AWS region
        gateway_client: Boto3 Gateway client
        enable_semantic_search: Enable semantic search (x_amz_bedrock_agentcore_search tool).
                                NOTE: Can only be set at gateway creation time, not after.
        
    Returns:
        Dict containing gateway information
    """
    print("\n" + "="*40)
    print("Setting up Gateway with Dual Interceptors")
    print("="*40)
    
    # Create Gateway IAM role
    gateway_iam_role = create_agentcore_gateway_role_with_region(gateway_name, region)
    gateway_role_arn = gateway_iam_role['Role']['Arn']
    
    print(f"✓ Gateway role created: {gateway_role_arn}")
    
    # Wait for role propagation
    time.sleep(10)
    
    # Build protocol configuration
    protocol_config = {
        "mcp": {
            "supportedVersions": ["2025-06-18", "2025-03-26"]
        }
    }
    if enable_semantic_search:
        protocol_config["mcp"]["searchType"] = "SEMANTIC"
        print(f"  ✓ Semantic search enabled (x_amz_bedrock_agentcore_search tool will be available)")

    # Create Gateway with both REQUEST and RESPONSE interceptors
    print(f"Creating Gateway with REQUEST and RESPONSE interceptors...")
    
    try:
        gateway_response = gateway_client.create_gateway(
            name=gateway_name,
            protocolType="MCP",
            protocolConfiguration=protocol_config,
            interceptorConfigurations=[
                {
                    "interceptor": {
                        "lambda": {
                            "arn": request_lambda_arn
                        }
                    },
                    "interceptionPoints": ["REQUEST"],
                    "inputConfiguration": {
                        "passRequestHeaders": True  
                    }
                },
                {
                    "interceptor": {
                        "lambda": {
                            "arn": response_lambda_arn
                        }
                    },
                    "interceptionPoints": ["RESPONSE"],
                    "inputConfiguration": {
                        "passRequestHeaders": True  
                    }
                }
            ],
            authorizerType="CUSTOM_JWT",
            authorizerConfiguration={
                "customJWTAuthorizer": {
                    "discoveryUrl": discovery_url,
                    "allowedClients": allowed_client_ids
                }
            },
            roleArn=gateway_role_arn
        )
        
        gateway_id = gateway_response.get('gatewayId')
        print(f"✓ Gateway created with dual interceptors: {gateway_id}")
        
    except Exception as e:
        print(f"✗ Failed to create Gateway: {e}")
        raise
    
    # Wait for Gateway to be ready
    print("Waiting for Gateway to be ready...")
    
    max_attempts = 30
    gateway_url = None
    
    for attempt in range(max_attempts):
        try:
            response = gateway_client.get_gateway(gatewayIdentifier=gateway_id)
            status = response.get('status', 'UNKNOWN')
            
            print(f"  [{attempt + 1}/{max_attempts}] Status: {status}")
            
            if status == 'READY':
                gateway_url = response.get('gatewayUrl')
                print(f"\n✓ Gateway is ready!")
                print(f"  URL: {gateway_url}")
                break
            elif status == 'FAILED':
                print(f"\n✗ Gateway creation failed")
                raise Exception("Gateway failed")
        except Exception as e:
            print(f"  [{attempt + 1}/{max_attempts}] Error: {e}")
        
        time.sleep(10)
    else:
        print(f"\n⚠ Timeout waiting for Gateway")
        raise Exception("Gateway timeout")
    
    return {
        'gateway_id': gateway_id,
        'gateway_url': gateway_url,
        'gateway_role_arn': gateway_role_arn
    }


def setup_gateway_with_interceptor(gateway_name: str, lambda_arn: str, 
                                 discovery_url: str, allowed_client_ids: List[str],
                                 region: str, gateway_client) -> Dict:
    """
    Setup AgentCore Gateway with Lambda interceptor.
    
    Returns:
        Dict containing gateway information
    """
    print("\n" + "="*40)
    print("Setting up Gateway with Interceptor")
    print("="*40)
    
    # Create Gateway IAM role
    gateway_iam_role = create_agentcore_gateway_role_with_region(gateway_name, region)
    gateway_role_arn = gateway_iam_role['Role']['Arn']
    
    print(f"✓ Gateway role created: {gateway_role_arn}")
    
    # Wait for role propagation
    time.sleep(10)
    
    # Create Gateway with Lambda interceptor
    print(f"Creating Gateway with RESPONSE interceptor...")
    
    try:
        gateway_response = gateway_client.create_gateway(
            name=gateway_name,
            protocolType="MCP",
            protocolConfiguration={
                "mcp": {
                    "supportedVersions": ["2025-06-18", "2025-03-26"]
                }
            },
            interceptorConfigurations=[{
                "interceptor": {
                    "lambda": {
                        "arn": lambda_arn
                    }
                },
                "interceptionPoints": ["RESPONSE"],
                "inputConfiguration": {
                    "passRequestHeaders": True  
                }
            }],
            authorizerType="CUSTOM_JWT",
            authorizerConfiguration={
                "customJWTAuthorizer": {
                    "discoveryUrl": discovery_url,
                    "allowedClients": allowed_client_ids
                }
            },
            roleArn=gateway_role_arn
        )
        
        gateway_id = gateway_response.get('gatewayId')
        print(f"✓ Gateway created: {gateway_id}")
        
    except Exception as e:
        print(f"✗ Failed to create Gateway: {e}")
        raise
    
    # Wait for Gateway to be ready
    print("Waiting for Gateway to be ready...")
    
    max_attempts = 30
    gateway_url = None
    
    for attempt in range(max_attempts):
        try:
            response = gateway_client.get_gateway(gatewayIdentifier=gateway_id)
            status = response.get('status', 'UNKNOWN')
            
            print(f"  [{attempt + 1}/{max_attempts}] Status: {status}")
            
            if status == 'READY':
                gateway_url = response.get('gatewayUrl')
                print(f"\n✓ Gateway is ready!")
                print(f"  URL: {gateway_url}")
                break
            elif status == 'FAILED':
                print(f"\n✗ Gateway creation failed")
                raise Exception("Gateway failed")
        except Exception as e:
            print(f"  [{attempt + 1}/{max_attempts}] Error: {e}")
        
        time.sleep(10)
    else:
        print(f"\n⚠ Timeout waiting for Gateway")
        raise Exception("Gateway timeout")
    
    return {
        'gateway_id': gateway_id,
        'gateway_url': gateway_url,
        'gateway_role_arn': gateway_role_arn
    }


def register_tools_as_targets(gateway_client, gateway_id: str, 
                            deployed_tools: List[Dict]) -> List[str]:
    """
    Register tool Lambda functions as Gateway targets.
    
    Returns:
        List of created target IDs
    """
    print("\n" + "="*40)
    print("Registering Tools as Gateway Targets")
    print("="*40)
    
    created_targets = []
    
    for tool in deployed_tools:
        print(f"  Registering {tool['tool_name']}...")
        
        try:
            response = gateway_client.create_gateway_target(
                gatewayIdentifier=gateway_id,
                name=f"{tool['tool_name'].replace('_', '-')}-target",
                targetConfiguration={
                    "mcp": {
                        "lambda": {
                            "lambdaArn": tool["lambda_arn"],
                            "toolSchema": {"inlinePayload": [tool["tool_definition"]]}
                        }
                    }
                },
                credentialProviderConfigurations=[{
                    "credentialProviderType": "GATEWAY_IAM_ROLE"
                }]
            )
            
            target_id = response['targetId']
            print(f"    ✓ Target created: {target_id}")
            
            # Wait for target to be READY
            for attempt in range(18):
                status_response = gateway_client.get_gateway_target(
                    gatewayIdentifier=gateway_id,
                    targetId=target_id
                )
                status = status_response.get('status')
                
                if status == 'READY':
                    print(f"    ✓ Target is READY")
                    created_targets.append(target_id)
                    break
                elif status == 'FAILED':
                    print(f"    ✗ Target FAILED")
                    break
                
                time.sleep(10)
                
        except Exception as e:
            print(f"    ✗ Failed to create target: {e}")
    
    print(f"✓ Registered {len(created_targets)}/{len(deployed_tools)} targets")
    return created_targets