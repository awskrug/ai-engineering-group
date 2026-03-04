"""
Data models for HR Web Demo
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum


class UserRole(str, Enum):
    HR_MANAGER = "hr-manager"
    EMPLOYEE = "employee"


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    role: UserRole
    client_id: str
    description: str
    user_info: Dict[str, str]


class ToolListResponse(BaseModel):
    tools: List[Dict[str, Any]]


class EmployeeSearchRequest(BaseModel):
    employee_id: Optional[str] = None
    search_name: Optional[str] = None


class LeaveRequest(BaseModel):
    action: str = "view"
    employee_id: Optional[str] = None


class PersonalLeaveRequest(BaseModel):
    employee_id: str


class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]


class ToolCallResponse(BaseModel):
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None


class Employee(BaseModel):
    employee_id: str
    name: str
    department: str
    position: str
    email: str
    phone: str
    address: str
    salary: Optional[float] = None
    hire_date: str
    status: str


class LeaveData(BaseModel):
    employee_id: str
    employee_name: str
    total_leave_days: int
    used_leave_days: int
    remaining_leave_days: int
    leave_history: List[Dict[str, Any]]
    pending_requests: List[Dict[str, Any]]


class DeploymentInfo(BaseModel):
    deployment_id: str
    region: str
    gateway_url: str
    user_pool_id: str
    token_url: str
    clients: Dict[str, Dict[str, str]]



class ChatRequest(BaseModel):
    message: str
    role: str
    username: str


class ChatEvent(BaseModel):
    type: str  # 'text', 'tool_call', 'tool_result', 'status', 'error', 'done'
    content: Any

