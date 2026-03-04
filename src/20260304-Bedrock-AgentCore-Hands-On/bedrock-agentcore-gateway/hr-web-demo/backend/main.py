"""
FastAPI backend for HR Employee Management Gateway Web Demo
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import logging
import json
import base64
from decimal import Decimal
from typing import Dict, Any, Optional


class DecimalEncoder(json.JSONEncoder):
    """Handle DynamoDB Decimal types in JSON serialization."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj == int(obj) else float(obj)
        return super().default(obj)

from models import (
    LoginRequest, LoginResponse, ToolListResponse, EmployeeSearchRequest,
    LeaveRequest, PersonalLeaveRequest, ToolCallRequest, ToolCallResponse,
    UserRole, ChatRequest
)
from services import hr_service, USERS_DB
from agent_service import run_agent_chat

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simple session storage (in production, use Redis or database)
user_sessions = {}

def get_current_user(
    authorization: Optional[str] = Header(None),
    x_user_name: Optional[str] = Header(None, alias="X-User-Name")
) -> Optional[str]:
    """Extract username from session token or X-User-Name header fallback"""
    if authorization and authorization.startswith('Bearer '):
        token = authorization[7:]
        for username, session_data in user_sessions.items():
            if session_data.get('token') == token:
                logger.info(f"Found username {username} for token")
                return username
        logger.warning(f"No username found for token: {token[:20]}...")
    
    # Fallback: use X-User-Name header (frontend sends this on every request)
    if x_user_name and x_user_name in USERS_DB:
        logger.info(f"Using X-User-Name header: {x_user_name}")
        return x_user_name
    
    return None

# Create FastAPI app
app = FastAPI(
    title="HR Employee Management Gateway - Web Demo",
    description="Web interface for testing PII masking and fine-grained access control",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"https://.*\.notebook\.*\.sagemaker\.aws",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "HR Employee Management Gateway Web Demo API"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Try to load deployment info to verify gateway is available
        deployment_info = hr_service.deployment_info
        return {
            "status": "healthy",
            "gateway_url": deployment_info.gateway_url,
            "deployment_id": deployment_info.deployment_id,
            "available_roles": list(deployment_info.clients.keys())
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")


@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate user with username/password"""
    try:
        logger.info(f"Login request for username: {request.username}")
        auth_data = hr_service.authenticate_user(request.username, request.password)
        
        # Store user session
        user_sessions[request.username] = {
            'token': auth_data['access_token'],
            'role': auth_data['role'],
            'user_info': auth_data['user_info']
        }
        
        return LoginResponse(
            access_token=auth_data['access_token'],
            role=UserRole(auth_data['role']),
            client_id=auth_data['client_id'],
            description=auth_data['description'],
            user_info=auth_data['user_info']
        )
    except Exception as e:
        logger.error(f"Login failed for username {request.username}: {e}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


@app.get("/tools/{role}")
async def get_tools(role: UserRole, current_user: Optional[str] = Depends(get_current_user)):
    """Get available tools for a role"""
    try:
        logger.info(f"Getting tools for role: {role}, user: {current_user}")
        tools_data = hr_service.get_available_tools(role, username=current_user)
        
        return ToolListResponse(tools=tools_data.get('tools', []))
    except Exception as e:
        logger.error(f"Failed to get tools for role {role}: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to get tools: {str(e)}")


@app.post("/employees/search/{role}")
async def search_employees(role: UserRole, request: EmployeeSearchRequest, 
                          current_user: Optional[str] = Depends(get_current_user)):
    """Search for employees"""
    try:
        logger.info(f"Employee search for role {role}: {request}, user: {current_user}")
        result = hr_service.search_employees(
            role=role,
            employee_id=request.employee_id,
            search_name=request.search_name,
            username=current_user
        )
        
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Employee search failed for role {role}: {e}")
        raise HTTPException(status_code=400, detail=f"Search failed: {str(e)}")


@app.post("/leave/management/{role}")
async def get_leave_management(role: UserRole, request: LeaveRequest,
                              current_user: Optional[str] = Depends(get_current_user)):
    """Get leave management data (HR only)"""
    try:
        if role not in [UserRole.HR_MANAGER]:
            raise HTTPException(status_code=403, detail="Access denied: HR role required")
        
        logger.info(f"Leave management request for role {role}: {request}, user: {current_user}")
        result = hr_service.get_leave_data(
            role=role,
            action=request.action,
            employee_id=request.employee_id,
            username=current_user
        )
        
        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Leave management failed for role {role}: {e}")
        raise HTTPException(status_code=400, detail=f"Leave management failed: {str(e)}")


@app.post("/leave/personal/{role}")
async def get_personal_leave(role: UserRole, request: PersonalLeaveRequest,
                            current_user: Optional[str] = Depends(get_current_user)):
    """Get personal leave data"""
    try:
        logger.info(f"Personal leave request for role {role}: {request}, user: {current_user}")
        
        # For employees, only allow their own leave data
        employee_id = request.employee_id
        if role == UserRole.EMPLOYEE:
            # Get the logged-in user's employee ID from the user database
            if current_user and current_user in USERS_DB:
                user_employee_id = USERS_DB[current_user]['employee_id']
                logger.info(f"Employee {current_user} requesting leave data for: {employee_id}, their ID: {user_employee_id}")
        
        result = hr_service.get_personal_leave(
            role=role,
            employee_id=employee_id,
            username=current_user
        )
        
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Personal leave failed for role {role}: {e}")
        raise HTTPException(status_code=400, detail=f"Personal leave failed: {str(e)}")


@app.post("/tools/call/{role}")
async def call_tool(role: UserRole, request: ToolCallRequest):
    """Generic tool call endpoint"""
    try:
        logger.info(f"Tool call for role {role}: {request.tool_name}")
        result = hr_service.call_tool(
            role=role,
            tool_name=request.tool_name,
            arguments=request.arguments
        )
        
        return ToolCallResponse(success=True, data=result)
    except Exception as e:
        logger.error(f"Tool call failed for role {role}: {e}")
        return ToolCallResponse(success=False, data={}, error=str(e))


@app.post("/employees/all/{role}")
async def get_all_employees(role: UserRole, request: Dict[str, Any],
                           current_user: Optional[str] = Depends(get_current_user)):
    """Get all employees - HR roles only"""
    try:
        if role not in [UserRole.HR_MANAGER]:
            raise HTTPException(status_code=403, detail="Access denied: HR role required")
        
        logger.info(f"Get all employees request for role {role}, user: {current_user}")
        result = hr_service.call_tool(
            role=role,
            tool_name="all_employees_tool",
            arguments={},
            username=current_user
        )
        
        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get all employees failed for role {role}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get all employees: {str(e)}")


@app.get("/deployment/info")
async def get_deployment_info():
    """Get deployment information"""
    try:
        deployment_info = hr_service.deployment_info
        return {
            "deployment_id": deployment_info.deployment_id,
            "region": deployment_info.region,
            "gateway_url": deployment_info.gateway_url,
            "available_roles": list(deployment_info.clients.keys()),
            "client_descriptions": {
                role: info['description'] 
                for role, info in deployment_info.clients.items()
            }
        }
    except Exception as e:
        logger.error(f"Failed to get deployment info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get deployment info: {str(e)}")


@app.get("/employees/list")
async def list_employees_for_tags():
    """Get employee list for quick-tag buttons (reads from DynamoDB Employees table)"""
    try:
        import boto3
        region = hr_service.deployment_info.region
        dynamodb = boto3.resource('dynamodb', region_name=region)
        table = dynamodb.Table('Employees')
        response = table.scan(ProjectionExpression='employee_id, #n, department',
                              ExpressionAttributeNames={'#n': 'name'})
        employees = sorted(response.get('Items', []), key=lambda x: x.get('employee_id', ''))
        return [{"id": e["employee_id"], "name": e.get("name", ""), "dept": e.get("department", "")}
                for e in employees]
    except Exception as e:
        logger.error(f"Failed to list employees: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/chat")
async def chat_with_agent(request: ChatRequest,
                         current_user: Optional[str] = Depends(get_current_user)):
    """Chat with the HR Agent via Server-Sent Events"""
    try:
        role = UserRole(request.role)
        username = request.username or current_user

        if not username:
            raise HTTPException(status_code=401, detail="Username required")

        logger.info(f"Chat request from {username} (role: {role}): {request.message}")

        def event_stream():
            for event in run_agent_chat(role=role, username=username, message=request.message, use_semantic_search=True):
                data = json.dumps(event, cls=DecimalEncoder, ensure_ascii=False)
                yield f"data: {data}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.post("/chat/sync")
async def chat_sync(request: ChatRequest,
                   current_user: Optional[str] = Depends(get_current_user)):
    """Non-streaming chat endpoint (fallback)"""
    try:
        role = UserRole(request.role)
        username = request.username or current_user

        if not username:
            raise HTTPException(status_code=401, detail="Username required")

        logger.info(f"Sync chat from {username} (role: {role}): {request.message}")

        events = []
        for event in run_agent_chat(role=role, username=username, message=request.message, use_semantic_search=True):
            events.append(event)

        return {"success": True, "events": events}
    except Exception as e:
        logger.error(f"Sync chat failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)