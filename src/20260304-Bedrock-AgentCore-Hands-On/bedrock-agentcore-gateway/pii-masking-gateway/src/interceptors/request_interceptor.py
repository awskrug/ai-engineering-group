"""
Request Interceptor for AgentCore Gateway
Pre-validates tool access permissions before execution using EmployeePermissions table.
All permission checks are based on EmployeeID from _user_context.
"""

import json
import os
import boto3
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError
from datetime import datetime


def lambda_handler(event, context) -> Dict[str, Any]:
    """
    Request Interceptor Lambda Handler
    
    Validates tool access permissions before allowing execution.
    Uses EmployeePermissions DynamoDB table for per-employee access control.
    """
    request_id = context.aws_request_id if context else "local-test"
    start_time = datetime.utcnow()
    
    print(f"[REQUEST-{request_id}] ===== REQUEST INTERCEPTOR START =====")
    print(f"[REQUEST-{request_id}] Timestamp: {start_time.isoformat()}Z")
    print(f"[REQUEST-{request_id}] Event: {json.dumps(event, default=str)}")
    
    try:
        # Extract request information from Gateway format
        mcp_data = event.get('mcp', {})
        gateway_request = mcp_data.get('gatewayRequest', {})
        
        # Fallback to direct format for testing
        if not gateway_request:
            gateway_request = event
        
        headers = gateway_request.get('headers', {})
        request_body = gateway_request.get('body', {})
        jsonrpc_id = request_body.get('id', 1) if isinstance(request_body, dict) else 1
        
        print(f"[REQUEST-{request_id}] Headers: {json.dumps(headers, default=str)}")
        print(f"[REQUEST-{request_id}] Request Body: {json.dumps(request_body, default=str)}")
        
        # Extract JWT token from Authorization header
        auth_header = headers.get('authorization', '') or headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            print(f"[REQUEST-{request_id}] ERROR: Missing or invalid authorization header")
            return create_deny_response("Missing or invalid authorization header", request_id, jsonrpc_id)
        
        jwt_token = auth_header.replace('Bearer ', '')
        jwt_claims = parse_jwt_token(jwt_token, request_id)
        if not jwt_claims:
            print(f"[REQUEST-{request_id}] ERROR: Invalid JWT token")
            return create_deny_response("Invalid JWT token", request_id, jsonrpc_id)
        
        client_id = jwt_claims.get('client_id')
        print(f"[REQUEST-{request_id}] Client ID: {client_id}")
        
        # Extract method
        method = request_body.get('method')
        print(f"[REQUEST-{request_id}] Request Method: {method}")
        
        # tools/list: allow through (request interceptor doesn't filter, response interceptor handles it)
        if method == 'tools/list':
            print(f"[REQUEST-{request_id}] tools/list request - allowing through")
            return create_allow_response("Tools list access granted", request_id, request_body)
        
        # tools/call: check employee permissions
        if method != 'tools/call':
            print(f"[REQUEST-{request_id}] Non-tool method, allowing through")
            return create_allow_response("Non-tool request allowed", request_id, request_body)
        
        params = request_body.get('params', {})
        tool_name = params.get('name')
        arguments = params.get('arguments', {}) if isinstance(params, dict) else {}
        
        print(f"[REQUEST-{request_id}] Tool Call: {tool_name}")
        print(f"[REQUEST-{request_id}] Arguments: {json.dumps(arguments, default=str)}")
        
        if not tool_name:
            return create_deny_response("Tool name not found in request", request_id, jsonrpc_id)
        
        # Extract _user_context from arguments
        user_context = arguments.get('_user_context', {}) if isinstance(arguments, dict) else {}
        employee_id = user_context.get('employee_id') if user_context else None
        
        # Fallback: MCPClient doesn't send _user_context, use X-User-Employee-Id header
        if not employee_id:
            employee_id = headers.get('X-User-Employee-Id')
            if employee_id:
                print(f"[REQUEST-{request_id}] Got employee_id from header: {employee_id}")
        
        if not employee_id:
            print(f"[REQUEST-{request_id}] ERROR: No employee_id in _user_context or headers")
            return create_deny_response("Employee identification required (_user_context.employee_id or X-User-Employee-Id header)", request_id, jsonrpc_id)
        
        print(f"[REQUEST-{request_id}] Employee ID: {employee_id}")
        
        # Check employee tool permission
        has_permission, permission_details = check_employee_tool_permission(employee_id, tool_name, request_id)
        
        if not has_permission:
            print(f"[REQUEST-{request_id}] PERMISSION DENIED: {employee_id} -> {tool_name}")
            return create_deny_response(f"Access denied to tool: {tool_name}", request_id, jsonrpc_id)
        
        print(f"[REQUEST-{request_id}] PERMISSION GRANTED: {employee_id} -> {tool_name}")
        
        # Additional context-based validation
        user_role = permission_details.get('role', 'unknown')
        validation_result = validate_request_context(
            employee_id=employee_id,
            user_role=user_role,
            tool_name=tool_name,
            request_params=params,
            request_id=request_id
        )
        
        if not validation_result['allowed']:
            print(f"[REQUEST-{request_id}] CONTEXT VALIDATION FAILED: {validation_result['reason']}")
            return create_deny_response(validation_result['reason'], request_id, jsonrpc_id)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds() * 1000
        
        print(f"[REQUEST-{request_id}] ===== REQUEST VALIDATION SUCCESSFUL =====")
        print(f"[REQUEST-{request_id}] Employee: {employee_id}, Role: {user_role}, Tool: {tool_name}")
        print(f"[REQUEST-{request_id}] Duration: {duration:.2f}ms")
        
        return create_allow_response(f"Access granted to tool: {tool_name}", request_id, request_body)
        
    except Exception as e:
        print(f"[REQUEST-{request_id}] CRITICAL ERROR: {e}")
        import traceback
        print(f"[REQUEST-{request_id}] Stack trace: {traceback.format_exc()}")
        return create_deny_response(f"Request validation failed: {str(e)}", request_id, jsonrpc_id)


def parse_jwt_token(token: str, request_id: str) -> Optional[Dict[str, Any]]:
    """Parse JWT token to extract claims (without verification - Gateway handles that)."""
    try:
        import base64
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        payload = parts[1]
        # Add padding
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding
        
        decoded = base64.b64decode(payload)
        claims = json.loads(decoded)
        print(f"[REQUEST-{request_id}] JWT claims decoded successfully")
        return claims
    except Exception as e:
        print(f"[REQUEST-{request_id}] ERROR: JWT decode failed: {e}")
        return None


def check_employee_tool_permission(employee_id: str, tool_name: str, request_id: str) -> tuple:
    """
    Check if employee has permission to access the requested tool using EmployeePermissions table.
    Returns (has_permission, details)
    """
    try:
        employee_permissions_table_name = os.environ.get('EMPLOYEE_PERMISSIONS_TABLE_NAME')
        if not employee_permissions_table_name:
            print(f"[REQUEST-{request_id}] ERROR: EMPLOYEE_PERMISSIONS_TABLE_NAME not set")
            return False, {"error": "Employee permissions table not configured"}

        # Extract actual tool name from Gateway format (prefix___tool_name)
        actual_tool_name = tool_name
        if '___' in tool_name:
            actual_tool_name = tool_name.split('___')[-1]
            print(f"[REQUEST-{request_id}] Extracted actual tool name: {actual_tool_name}")

        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(employee_permissions_table_name)

        response = table.get_item(Key={'EmployeeID': employee_id})
        item = response.get('Item')
        
        if not item:
            print(f"[REQUEST-{request_id}] No permissions found for employee: {employee_id}")
            return False, {"error": f"No permissions configured for employee: {employee_id}"}

        allowed_tools = item.get('AllowedTools', [])
        role = item.get('Role', 'unknown')
        print(f"[REQUEST-{request_id}] Employee {employee_id}: Role={role}, AllowedTools={allowed_tools}")

        if actual_tool_name in allowed_tools:
            print(f"[REQUEST-{request_id}] Permission GRANTED: {employee_id} -> {actual_tool_name}")
            return True, {
                "granted": True,
                "role": role,
                "allowed_tools": allowed_tools,
                "matched_tool": actual_tool_name,
                "source": "EmployeePermissions"
            }

        print(f"[REQUEST-{request_id}] Permission DENIED: {actual_tool_name} not in {allowed_tools}")
        return False, {
            "granted": False,
            "role": role,
            "allowed_tools": allowed_tools,
            "actual_tool_name": actual_tool_name,
            "reason": f"Tool '{actual_tool_name}' not in employee's allowed tools"
        }

    except Exception as e:
        print(f"[REQUEST-{request_id}] ERROR: Permission check error: {e}")
        return False, {"error": f"Permission check failed: {str(e)}"}


def validate_request_context(employee_id: str, user_role: str, tool_name: str,
                           request_params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
    """Perform additional context-based validation."""
    try:
        print(f"[REQUEST-{request_id}] Context validation: employee={employee_id}, role={user_role}, tool={tool_name}")
        
        # Default: allow if basic permission check passed
        return {
            'allowed': True,
            'reason': 'Permission validation passed',
            'context': {'user_role': user_role, 'employee_id': employee_id}
        }
        
    except Exception as e:
        print(f"[REQUEST-{request_id}] ERROR: Context validation error: {e}")
        return {'allowed': False, 'reason': f'Context validation failed: {str(e)}'}


def create_allow_response(message: str, request_id: str, request_body: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create an ALLOW response for the Gateway.

    Per AWS docs, request interceptor output should contain:
    - transformedGatewayRequest: pass through the original request body
    No 'interceptorAction' field - Gateway determines allow/deny by presence of transformedGatewayResponse.
    """
    print(f"[REQUEST-{request_id}] ALLOW: {message}")

    response = {
        "interceptorOutputVersion": "1.0",
        "mcp": {
            "transformedGatewayRequest": {
                "body": request_body if request_body else {}
            }
        }
    }

    return response


def create_deny_response(reason: str, request_id: str, jsonrpc_id=None) -> Dict[str, Any]:
    """Create a DENY response for the Gateway.

    Per AWS docs, to deny a request, return a transformedGatewayResponse
    which causes the Gateway to respond immediately with that content.
    """
    print(f"[REQUEST-{request_id}] DENY: {reason}")

    return {
        "interceptorOutputVersion": "1.0",
        "mcp": {
            "transformedGatewayResponse": {
                "statusCode": 200,
                "body": {
                    "jsonrpc": "2.0",
                    "id": jsonrpc_id if jsonrpc_id is not None else 1,
                    "result": {
                        "isError": True,
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps({"access_denied": True, "message": reason})
                            }
                        ]
                    }
                }
            }
        }
    }
