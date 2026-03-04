"""
Combined Interceptor for Gateway MCP RESPONSES with PII Masking and Fine-Grained Access Control

This Lambda function intercepts Gateway MCP responses and provides:
1. PII Masking using Amazon Bedrock Guardrails for tools/call responses
2. Fine-Grained Access Control using EmployeePermissions DynamoDB for tools/list responses

All permission checks are based on EmployeeID from _user_context embedded in request arguments.
"""

import json
import os
import boto3
import base64
from typing import Any, Dict, List

# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime')
dynamodb = boto3.resource('dynamodb')

# Get configuration from environment variables
GUARDRAIL_ID = os.environ.get('GUARDRAIL_ID')
GUARDRAIL_VERSION = os.environ.get('GUARDRAIL_VERSION', 'DRAFT')
EMPLOYEE_PERMISSIONS_TABLE_NAME = os.environ.get('EMPLOYEE_PERMISSIONS_TABLE_NAME')

# Initialize DynamoDB table
employee_permissions_table = None
if EMPLOYEE_PERMISSIONS_TABLE_NAME:
    employee_permissions_table = dynamodb.Table(EMPLOYEE_PERMISSIONS_TABLE_NAME)


def extract_client_id_from_jwt(headers: Dict[str, str]) -> str:
    """Extract client_id from JWT token in Authorization header."""
    try:
        auth_header = headers.get('authorization', '') or headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None
        token = auth_header.replace('Bearer ', '')
        parts = token.split('.')
        if len(parts) != 3:
            return None
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding
        decoded = base64.b64decode(payload)
        claims = json.loads(decoded)
        return claims.get('client_id')
    except Exception as e:
        print(f"[DEBUG] Error extracting client_id from JWT: {e}")
        return None


def get_employee_permissions(employee_id: str) -> Dict:
    """
    Get employee permissions from EmployeePermissions DynamoDB table.
    Returns dict with Role, AllowedTools, Name, Department, Username or empty dict.
    """
    print(f"[DEBUG] get_employee_permissions - employee_id: {employee_id}")

    if not employee_permissions_table or not employee_id:
        print("[DEBUG] No employee permissions table or employee_id, returning empty dict")
        return {}

    try:
        response = employee_permissions_table.get_item(Key={'EmployeeID': employee_id})
        if 'Item' in response:
            item = response['Item']
            print(f"[DEBUG] Found employee permissions for {employee_id}: Role={item.get('Role')}, Tools={item.get('AllowedTools')}")
            return item
        else:
            print(f"[DEBUG] No employee permissions found for: {employee_id}")
            return {}
    except Exception as e:
        print(f"[DEBUG] Error querying employee permissions: {e}")
        return {}


def filter_tools_by_permissions(tools: List[Dict], allowed_tools: List[str]) -> List[Dict]:
    """Filter tools list based on allowed tools from EmployeePermissions."""
    if not allowed_tools:
        print("[DEBUG] No allowed tools specified, returning all tools")
        return tools

    filtered = []
    for tool in tools:
        tool_name = tool.get('name', '')
        actual_name = tool_name.split('___')[-1] if '___' in tool_name else tool_name
        if actual_name in allowed_tools:
            filtered.append(tool)
            print(f"[DEBUG] Tool ALLOWED: {tool_name}")
        else:
            print(f"[DEBUG] Tool FILTERED: {tool_name}")

    return filtered


# Fields that Guardrail cannot detect as PII (plain numbers, etc.)
SENSITIVE_FIELDS_TO_STRIP = {'salary'}


def strip_sensitive_fields(data: Any) -> Any:
    """Remove sensitive fields that Bedrock Guardrail cannot detect (e.g. salary as plain number)."""
    if isinstance(data, dict):
        if 'employees' in data and isinstance(data['employees'], list):
            data['employees'] = [
                {k: v for k, v in emp.items() if k not in SENSITIVE_FIELDS_TO_STRIP}
                for emp in data['employees']
            ]
        elif 'employee_id' in data or 'name' in data:
            data = {k: v for k, v in data.items() if k not in SENSITIVE_FIELDS_TO_STRIP}
    return data


def mask_pii_with_guardrails(text: str) -> str:
    """Apply Bedrock Guardrails to mask PII in text."""
    if not GUARDRAIL_ID:
        print("[DEBUG] No GUARDRAIL_ID configured, skipping PII masking")
        return text

    if not text or not text.strip():
        return text

    try:
        response = bedrock_runtime.apply_guardrail(
            guardrailIdentifier=GUARDRAIL_ID,
            guardrailVersion=GUARDRAIL_VERSION,
            source='OUTPUT',
            content=[{'text': {'text': text}}]
        )

        action = response.get('action', 'NONE')
        print(f"[DEBUG] Guardrail action: {action}")

        if action == 'GUARDRAIL_INTERVENED':
            outputs = response.get('outputs', [])
            if outputs:
                masked_text = outputs[0].get('text', text)
                print(f"[DEBUG] PII masking applied successfully")
                return masked_text

        return text

    except Exception as e:
        print(f"[DEBUG] Error applying Bedrock Guardrails: {e}")
        return text


def filter_employee_data_for_non_hr(data: Any, is_self_access: bool = False) -> Any:
    """Filter sensitive fields from employee data for non-HR users."""
    if is_self_access:
        return data

    sensitive_fields = {'salary', 'address', 'phone', 'email',
                       'annual_leave_entitlement', 'sick_leave_entitlement', 'personal_leave_entitlement'}

    if isinstance(data, dict):
        if 'employees' in data:
            data['employees'] = [
                {k: v for k, v in emp.items() if k not in sensitive_fields}
                for emp in data['employees']
            ]
        elif 'employee_id' in data or 'name' in data:
            data = {k: v for k, v in data.items() if k not in sensitive_fields}
    return data


def apply_selective_masking(data: Any) -> Any:
    """Apply selective field masking for employee clients viewing other employees' data."""
    print(f"[DEBUG] apply_selective_masking - input type: {type(data)}")

    if isinstance(data, dict):
        if 'employees' in data and isinstance(data['employees'], list):
            masked_employees = []
            for emp in data['employees']:
                masked_emp = {}
                for key, value in emp.items():
                    if key in ('salary', 'address'):
                        masked_emp[key] = '***MASKED***'
                    elif key in ('phone',):
                        masked_emp[key] = '***-***-****'
                    elif key in ('email',):
                        masked_emp[key] = '***@***.***'
                    else:
                        masked_emp[key] = value
                masked_employees.append(masked_emp)
            data['employees'] = masked_employees
        elif 'name' in data or 'employee_id' in data:
            for key in list(data.keys()):
                if key in ('salary', 'address'):
                    data[key] = '***MASKED***'
                elif key in ('phone',):
                    data[key] = '***-***-****'
                elif key in ('email',):
                    data[key] = '***@***.***'

    return data


def mask_tool_response(response_body: Dict[str, Any], request_body: Dict[str, Any] = None,
                      request_headers: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Mask PII in tool response based on employee permissions from _user_context.
    
    Args:
        response_body: MCP JSON-RPC response body
        request_body: Original request body (contains _user_context in params.arguments)
        request_headers: Request headers
    
    Returns:
        Response body with masked PII (if applicable)
    """
    print(f"[DEBUG] mask_tool_response - processing response")
    
    # --- Determine role from _user_context + EmployeePermissions ---
    client_role = None
    user_employee_id = None
    
    if request_body:
        params = request_body.get('params', {})
        arguments = params.get('arguments', {}) if isinstance(params, dict) else {}
        user_context = arguments.get('_user_context', {}) if isinstance(arguments, dict) else {}
        if user_context:
            user_employee_id = user_context.get('employee_id')
            ctx_role = user_context.get('role', '')
            print(f"[DEBUG] _user_context: employee_id={user_employee_id}, role={ctx_role}")
            
            if user_employee_id:
                emp_perms = get_employee_permissions(user_employee_id)
                if emp_perms:
                    client_role = emp_perms.get('Role', ctx_role)
                    print(f"[DEBUG] Role from EmployeePermissions: {client_role}")
                else:
                    client_role = ctx_role
                    print(f"[DEBUG] Role from _user_context fallback: {client_role}")
    
    if not client_role:
        # Fallback: MCPClient doesn't send _user_context, use X-User-Employee-Id header
        if request_headers:
            header_employee_id = request_headers.get('X-User-Employee-Id')
            if header_employee_id:
                user_employee_id = header_employee_id
                emp_perms = get_employee_permissions(header_employee_id)
                if emp_perms:
                    client_role = emp_perms.get('Role', 'employee')
                    print(f"[DEBUG] Role from header fallback: {client_role} (employee_id={header_employee_id})")
        
    if not client_role:
        print(f"[DEBUG] No role determined - defaulting to employee (mask everything)")
        client_role = 'employee'
    
    # HR managers see unmasked data
    if client_role == 'hr-manager':
        print(f"[DEBUG] HR role - returning unmasked data")
        return response_body
    
    # For employee clients, check self-access
    is_self_access = False
    
    if client_role == 'employee' and request_body and user_employee_id:
        params = request_body.get('params', {})
        arguments = params.get('arguments', {}) if isinstance(params, dict) else {}
        requested_employee_id = arguments.get('employee_id')
        requested_name = arguments.get('search_name')
        
        print(f"[DEBUG] Self-access check: user={user_employee_id}, requested_id={requested_employee_id}, name={requested_name}")
        
        # Direct ID match
        if requested_employee_id and requested_employee_id.upper() == user_employee_id.upper():
            print(f"[DEBUG] Self-access by employee_id match")
            is_self_access = True
        
        # Response-based check for name searches (single result matching user's ID)
        if not is_self_access:
            try:
                result_content = response_body.get('result', {}).get('content', [])
                if result_content and len(result_content) > 0:
                    content_text = result_content[0].get('text', '')
                    parsed = json.loads(content_text) if isinstance(content_text, str) else content_text
                    if isinstance(parsed, dict):
                        employees = parsed.get('body', {}).get('result', {}).get('employees', [])
                        if len(employees) == 1 and employees[0].get('employee_id', '').upper() == user_employee_id.upper():
                            print(f"[DEBUG] Self-access by single-result response match")
                            is_self_access = True
            except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
                print(f"[DEBUG] Could not parse response for self-access check: {e}")
    
    if is_self_access:
        print(f"[DEBUG] Self-access - returning unmasked data")
        return response_body
    
    print(f"[DEBUG] Applying PII masking for employee client")
    
    # Deep copy
    masked_response = json.loads(json.dumps(response_body))
    
    if 'result' not in masked_response or 'content' not in masked_response.get('result', {}):
        return masked_response

    content_list = masked_response['result']['content']
    if not isinstance(content_list, list) or len(content_list) == 0:
        return masked_response

    for i, content_item in enumerate(content_list):
        if content_item.get('type') != 'text':
            continue
        
        text_value = content_item.get('text', '')
        if not text_value:
            continue
        
        try:
            parsed_data = None
            original_structure = None
            
            if isinstance(text_value, dict):
                parsed_data = text_value
                if 'body' in text_value and 'result' in text_value['body']:
                    original_structure = text_value
                    data_to_process = text_value['body']['result']
                else:
                    data_to_process = text_value
            elif isinstance(text_value, str):
                parsed_data = json.loads(text_value)
                if 'body' in parsed_data and 'result' in parsed_data['body']:
                    original_structure = parsed_data
                    data_to_process = parsed_data['body']['result']
                else:
                    data_to_process = parsed_data
            else:
                data_to_process = text_value
            
            # Strip salary field before Guardrail (Guardrail can't detect plain numbers as PII)
            data_to_process = strip_sensitive_fields(data_to_process)
            
            # Apply Bedrock Guardrails PII masking for all data (employee and non-employee)
            print(f"[DEBUG] Applying Bedrock Guardrails PII masking")
            json_string = json.dumps(data_to_process, indent=2, default=str)
            anonymized_json_string = mask_pii_with_guardrails(json_string)
            
            try:
                anonymized_json = json.loads(anonymized_json_string)
                if original_structure:
                    if 'body' in original_structure and 'result' in original_structure['body']:
                        original_structure['body']['result'] = anonymized_json
                    else:
                        original_structure = anonymized_json
                    masked_response['result']['content'][i]['text'] = json.dumps(original_structure, default=str)
                else:
                    masked_response['result']['content'][i]['text'] = json.dumps(anonymized_json, default=str)
            except json.JSONDecodeError:
                masked_response['result']['content'][i]['text'] = anonymized_json_string
                
        except json.JSONDecodeError:
            anonymized_text = mask_pii_with_guardrails(str(text_value))
            masked_response['result']['content'][i]['text'] = anonymized_text
    
    print(f"[DEBUG] mask_tool_response - completed")
    return masked_response


def lambda_handler(event, context):
    """
    Main Lambda handler for Gateway RESPONSE interceptor.
    
    Provides:
    1. Fine-Grained Access Control for tools/list responses (via EmployeePermissions)
    2. PII Masking for tools/call responses
    """
    print(f"[DEBUG] ========== COMBINED INTERCEPTOR START ==========")
    print(f"[DEBUG] Event: {json.dumps(event, default=str)}")
    
    try:
        mcp_data = event.get('mcp', {})
        gateway_response = mcp_data.get('gatewayResponse', {})
        gateway_request = mcp_data.get('gatewayRequest', {})
        
        response_headers = gateway_response.get('headers', {})
        response_body = gateway_response.get('body', {})
        status_code = gateway_response.get('statusCode', 200)
        
        request_headers = gateway_request.get('headers', {})
        request_body = gateway_request.get('body', {})
        
        method = request_body.get('method', '')
        print(f"[DEBUG] Method: {method}")
        
        # Notifications (e.g. notifications/initialized) have null response body.
        # Response interceptor must always return transformedGatewayResponse.
        if response_body is None:
            print(f"[DEBUG] Method '{method}' - null response body (notification), passing through with empty body")
            return {
                "interceptorOutputVersion": "1.0",
                "mcp": {
                    "transformedGatewayResponse": {
                        "body": {},
                        "statusCode": status_code
                    }
                }
            }
        
        # Error responses (e.g. Request Interceptor DENY) — pass through unchanged
        if isinstance(response_body, dict):
            if 'error' in response_body:
                print(f"[DEBUG] JSON-RPC error response, passing through")
                return {
                    "interceptorOutputVersion": "1.0",
                    "mcp": {
                        "transformedGatewayResponse": {
                            "headers": response_headers,
                            "body": response_body,
                            "statusCode": status_code
                        }
                    }
                }
            result = response_body.get('result', {})
            if isinstance(result, dict) and result.get('isError'):
                print(f"[DEBUG] Tool error response (isError=true), passing through")
                return {
                    "interceptorOutputVersion": "1.0",
                    "mcp": {
                        "transformedGatewayResponse": {
                            "headers": response_headers,
                            "body": response_body,
                            "statusCode": status_code
                        }
                    }
                }
        
        if method == 'tools/list':
            print(f"[DEBUG] Processing tools/list - filtering by employee permissions")
            
            # Extract employee_id: first try _user_context in params, then fall back to request headers
            request_params = request_body.get('params', {})
            user_context = request_params.get('_user_context', {}) if isinstance(request_params, dict) else {}
            employee_id = user_context.get('employee_id') if user_context else None
            
            # Fallback: MCPClient doesn't send _user_context, use X-User-Employee-Id header
            if not employee_id and request_headers:
                employee_id = request_headers.get('X-User-Employee-Id')
                if employee_id:
                    print(f"[DEBUG] Got employee_id from header: {employee_id}")
            
            if employee_id and 'result' in response_body and 'tools' in response_body['result']:
                original_tools = response_body['result']['tools']
                print(f"[DEBUG] Total tools: {len(original_tools)}, filtering for employee: {employee_id}")
                
                emp_perms = get_employee_permissions(employee_id)
                allowed_tools = emp_perms.get('AllowedTools', []) if emp_perms else []
                
                if allowed_tools:
                    filtered_tools = filter_tools_by_permissions(original_tools, allowed_tools)
                    response_body['result']['tools'] = filtered_tools
                    print(f"[DEBUG] Filtered to {len(filtered_tools)} tools for {employee_id}")
                else:
                    print(f"[DEBUG] No permissions found for {employee_id}, returning empty tools list")
                    response_body['result']['tools'] = []
            else:
                print(f"[DEBUG] No _user_context in tools/list request, returning all tools")
            
        elif method == 'tools/call':
            print(f"[DEBUG] Processing tools/call with PII masking")
            response_body = mask_tool_response(response_body, request_body, request_headers)
            
        else:
            print(f"[DEBUG] Method '{method}' - passing through unchanged")
        
        return_obj = {
            "interceptorOutputVersion": "1.0",
            "mcp": {
                "transformedGatewayResponse": {
                    "headers": response_headers,
                    "body": response_body,
                    "statusCode": status_code
                }
            }
        }
        
        print(f"[DEBUG] ========== COMBINED INTERCEPTOR END ==========")
        return return_obj
    
    except Exception as e:
        print(f"[DEBUG] ERROR in lambda_handler: {e}")
        import traceback
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        
        return {
            "interceptorOutputVersion": "1.0",
            "mcp": {
                "transformedGatewayResponse": {
                    "headers": gateway_response.get('headers', {}),
                    "body": gateway_response.get('body', {}),
                    "statusCode": gateway_response.get('statusCode', 500)
                }
            }
        }
