"""
Business logic services for HR Web Demo
"""

import json
import requests
from pathlib import Path
from typing import Dict, Any, Optional
import sys
import os
import hashlib

# Add the parent directory to the path to import from pii-masking-gateway
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir / "pii-masking-gateway"))

from src.utils.aws_utils import get_token
from models import DeploymentInfo, UserRole


# Sample user database with ID/Password
USERS_DB = {
    "hr-manager": {
        "password": "hr123!",  # In production, this would be hashed
        "role": "hr-manager",
        "name": "HR Manager",
        "employee_id": "EMP-001",
        "department": "Human Resources",
        "position": "HR Manager"
    },
    "employee2": {
        "password": "emp789!",
        "role": "employee",
        "name": "Employee 2",
        "employee_id": "EMP-002",
        "department": "Engineering",
        "position": "Senior Developer"
    },
    "employee3": {
        "password": "marketing2024!",
        "role": "employee",
        "name": "Employee 3",
        "employee_id": "EMP-003",
        "department": "Marketing",
        "position": "Marketing Specialist"
    },
}


class HRGatewayService:
    """Service to interact with the HR Employee Management Gateway"""
    
    def __init__(self):
        self.deployment_info = self._load_deployment_info()
        self._tokens_cache = {}  # Cache tokens by role
    
    def _load_deployment_info(self) -> DeploymentInfo:
        """Load deployment information from the gateway deployment"""
        deployment_file = parent_dir / "pii-masking-gateway" / "deployment_info.json"
        
        if not deployment_file.exists():
            raise FileNotFoundError(
                "Deployment info not found. Please run the gateway setup first: "
                "python3 pii-masking-gateway/scripts/setup.py"
            )
        
        with open(deployment_file, 'r') as f:
            data = json.load(f)
        
        return DeploymentInfo(**data)
    
    def get_client_info(self, role: UserRole) -> Dict[str, str]:
        """Get client information for a specific role"""
        role_key = role.value
        if role_key not in self.deployment_info.clients:
            raise ValueError(f"Role {role} not found in deployment")
        
        return self.deployment_info.clients[role_key]
    
    def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate user with username/password and return role and user info"""
        if username not in USERS_DB:
            raise ValueError("Invalid username or password")
        
        user_data = USERS_DB[username]
        if user_data["password"] != password:
            raise ValueError("Invalid username or password")
        
        role = UserRole(user_data["role"])
        
        # Get AWS Cognito token for the role
        client_info = self.get_client_info(role)
        
        try:
            token_response = get_token(
                user_pool_id=self.deployment_info.user_pool_id,
                client_id=client_info['client_id'],
                client_secret=client_info['client_secret'],
                scope_string="hr-gateway/tools",
                region=self.deployment_info.region
            )
            
            # Check if token response contains error
            if 'error' in token_response:
                raise ValueError(f"Token request failed: {token_response['error']}")
            
            # Extract access token from response
            access_token = token_response.get('access_token')
            if not access_token:
                raise ValueError(f"No access token in response: {token_response}")
            
            return {
                'access_token': access_token,
                'role': role.value,
                'client_id': client_info['client_id'],
                'description': client_info['description'],
                'user_info': {
                    'username': username,
                    'name': user_data['name'],
                    'employee_id': user_data['employee_id'],
                    'department': user_data['department'],
                    'position': user_data['position']
                }
            }
        except Exception as e:
            raise ValueError(f"Authentication failed: {str(e)}")

    def authenticate(self, role: UserRole) -> Dict[str, Any]:
        """Authenticate and get access token for a role"""
        client_info = self.get_client_info(role)
        
        # Get token from AWS Cognito
        token_data = get_token(
            user_pool_id=self.deployment_info.user_pool_id,
            client_id=client_info['client_id'],
            client_secret=client_info['client_secret'],
            scope_string="hr-gateway/tools",
            region=self.deployment_info.region
        )
        
        if 'error' in token_data:
            raise Exception(f"Authentication failed: {token_data['error']}")
        
        # Extract access token from response
        access_token = token_data.get('access_token')
        if not access_token:
            raise Exception(f"No access token in response: {token_data}")
        
        # Cache the token
        self._tokens_cache[role] = access_token
        
        return {
            'access_token': access_token,
            'role': role,
            'client_id': client_info['client_id'],
            'description': client_info['description']
        }
    
    def get_available_tools(self, role: UserRole, username: str = None) -> Dict[str, Any]:
        """Get list of available tools for a role"""
        if role not in self._tokens_cache:
            self.authenticate(role)
        
        token = self._tokens_cache[role]
        
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1,
            "params": {}
        }
        
        # Embed _user_context so response interceptor can filter tools per employee
        if username and username in USERS_DB:
            user_data = USERS_DB[username]
            request_data["params"]["_user_context"] = {
                "employee_id": user_data.get("employee_id", ""),
                "role": user_data.get("role", ""),
                "username": username
            }
        
        response = requests.post(
            self.deployment_info.gateway_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "MCP-Protocol-Version": "2025-06-18"
            },
            json=request_data
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to get tools: {response.status_code}")
        
        result = response.json()
        return result.get('result', {})
    
    def call_tool(self, role: UserRole, tool_name: str, arguments: Dict[str, Any], username: str = None) -> Dict[str, Any]:
        """Call a specific tool with arguments.

        Access control is delegated to the Gateway's request interceptor.
        We use HR_MANAGER token to get the full tool list for name resolution,
        but the actual call uses the role's own token so the request interceptor
        can enforce permissions based on _user_context.
        """
        if role not in self._tokens_cache:
            self.authenticate(role)

        token = self._tokens_cache[role]

        # Get full tool list (unfiltered) for name resolution only.
        # Use HR_MANAGER to ensure we see all tools regardless of response interceptor filtering.
        if UserRole.HR_MANAGER not in self._tokens_cache:
            self.authenticate(UserRole.HR_MANAGER)

        manager_token = self._tokens_cache[UserRole.HR_MANAGER]

        list_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1,
            "params": {}
        }
        list_response = requests.post(
            self.deployment_info.gateway_url,
            headers={
                "Authorization": f"Bearer {manager_token}",
                "Content-Type": "application/json",
                "MCP-Protocol-Version": "2025-06-18"
            },
            json=list_request
        )

        full_tool_name = None
        if list_response.status_code == 200:
            all_tools = list_response.json().get('result', {}).get('tools', [])
            for tool in all_tools:
                if tool_name in tool['name']:
                    full_tool_name = tool['name']
                    break

        if not full_tool_name:
            raise Exception(f"Tool {tool_name} not found in gateway")

        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 2,
            "params": {
                "name": full_tool_name,
                "arguments": arguments
            }
        }

        # Embed user context in arguments (Gateway strips non-standard params fields)
        if username and username in USERS_DB:
            user_data = USERS_DB[username]
            request_data["params"]["arguments"]["_user_context"] = {
                "employee_id": user_data.get("employee_id", ""),
                "role": user_data.get("role", ""),
                "username": username
            }
            print(f"[DEBUG] Embedded _user_context in arguments: {request_data['params']['arguments']['_user_context']}")

        # Add custom headers for user identification
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "MCP-Protocol-Version": "2025-06-18"
        }

        print(f"[DEBUG] Making request to gateway with headers: {headers}")
        print(f"[DEBUG] Request data: {request_data}")

        response = requests.post(
            self.deployment_info.gateway_url,
            headers=headers,
            json=request_data
        )

        # Parse response body even for non-200 status codes (e.g. 403 from request interceptor deny).
        # This lets the agent see the deny reason instead of a generic error.
        try:
            result = response.json()
        except Exception:
            if response.status_code != 200:
                raise Exception(f"Failed to call tool: {response.status_code}")
            raise

        print(f"[DEBUG] Gateway response (status={response.status_code}): {result}")
        return result
    
    def search_employees(self, role: UserRole, employee_id: Optional[str] = None, 
                        search_name: Optional[str] = None, username: str = None) -> Dict[str, Any]:
        """Search for employees using the employee search tool"""
        arguments = {}
        if employee_id:
            arguments['employee_id'] = employee_id
        if search_name:
            arguments['search_name'] = search_name
        
        return self.call_tool(role, 'employee_search_tool', arguments, username)
    
    def get_leave_data(self, role: UserRole, action: str = "view", 
                      employee_id: Optional[str] = None, username: str = None) -> Dict[str, Any]:
        """Get all leave records data (HR only)"""
        arguments = {'action': action}
        if employee_id:
            arguments['employee_id'] = employee_id
        
        return self.call_tool(role, 'all_leave_records_tool', arguments, username)
    
    def get_personal_leave(self, role: UserRole, employee_id: str, username: str = None) -> Dict[str, Any]:
        """Get employee leave data"""
        arguments = {'employee_id': employee_id}
        return self.call_tool(role, 'employee_leave_tool', arguments, username)


# Global service instance
hr_service = HRGatewayService()