"""
Strands Agent Service for HR Web Demo

Connects the Strands Agent directly to the AgentCore Gateway via MCPClient,
enabling native MCP tool integration with optional semantic search.

Architecture:
  Agent ──(MCPClient/streamablehttp)──> AgentCore Gateway ──> Tool Lambdas
                                              │
                                    REQUEST/RESPONSE Interceptors
"""

import json
import logging
import os
from decimal import Decimal
from typing import Dict, Any, Optional, List
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client

from services import hr_service, USERS_DB
from models import UserRole

logger = logging.getLogger(__name__)


def _sanitize_decimals(obj):
    """Recursively convert Decimal values to int/float for JSON serialization."""
    if isinstance(obj, Decimal):
        return int(obj) if obj == int(obj) else float(obj)
    if isinstance(obj, dict):
        return {k: _sanitize_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_decimals(i) for i in obj]
    return obj


# Module-level store for tool results captured during agent execution
_captured_tool_results: List[Dict[str, Any]] = []


def _create_mcp_transport(gateway_url: str, access_token: str, username: str = None):
    """Create streamable HTTP transport for MCPClient with auth headers.

    The Bearer token carries the role-specific Cognito credentials so the
    gateway's request/response interceptors can enforce access control.
    Custom headers pass user context for fine-grained authorization.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    # Pass user context as custom headers for interceptor FGAC
    if username and username in USERS_DB:
        user_data = USERS_DB[username]
        headers["X-User-Employee-Id"] = user_data.get("employee_id", "")
        headers["X-User-Role"] = user_data.get("role", "")
        headers["X-User-Name"] = username

    return streamablehttp_client(url=gateway_url, headers=headers)


def _get_tools_from_gateway(mcp_client: MCPClient, use_semantic_search: bool = False,
                            query: str = None, gateway_url: str = None,
                            access_token: str = None) -> List:
    """Retrieve tools from the gateway via MCPClient.

    Two modes:
    - use_semantic_search=False: list all tools via tools/list
    - use_semantic_search=True: call x_amz_bedrock_agentcore_search via HTTP,
      then create MCPAgentTool objects from search results (no tools/list)

    Args:
        mcp_client: Active MCPClient connected to the gateway
        use_semantic_search: If True, use semantic search to discover tools
        query: User message for semantic search query
        gateway_url: Gateway MCP endpoint URL (required for semantic search)
        access_token: Bearer token (required for semantic search)
    """
    if use_semantic_search and query and gateway_url and access_token:
        import requests as req
        logger.info(f"[MCP] Semantic search with query: {query}")

        # Call search tool directly via HTTP (avoids MCPClient's internal list_tools)
        search_response = req.post(
            gateway_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "MCP-Protocol-Version": "2025-06-18"
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "x_amz_bedrock_agentcore_search",
                    "arguments": {"query": query}
                }
            }
        )

        if search_response.status_code == 200:
            result = search_response.json()
            tool_list = None

            # Extract tools from structuredContent or result.content
            structured = result.get('result', {}).get('structuredContent', {})
            if 'tools' in structured:
                tool_list = structured['tools']
            else:
                content = result.get('result', {}).get('content', [])
                for block in content:
                    text = block.get('text', '')
                    try:
                        parsed = json.loads(text) if isinstance(text, str) else text
                        if isinstance(parsed, dict) and 'tools' in parsed:
                            tool_list = parsed['tools']
                            break
                        elif isinstance(parsed, list):
                            tool_list = parsed
                            break
                    except (json.JSONDecodeError, TypeError):
                        pass

            if tool_list:
                from mcp.types import Tool as MCPTool
                from strands.tools.mcp.mcp_client import MCPAgentTool
                tools = []
                for tool_def in tool_list:
                    if isinstance(tool_def, dict) and 'name' in tool_def:
                        mcp_tool = MCPTool(
                            name=tool_def['name'],
                            description=tool_def.get('description', ''),
                            inputSchema=tool_def.get('inputSchema', {"type": "object", "properties": {}})
                        )
                        tools.append(MCPAgentTool(mcp_tool, mcp_client))
                logger.info(f"[MCP] Semantic search found {len(tools)} tools: {[t.tool_name for t in tools]}")
                return tools

        logger.warning(f"[MCP] Semantic search failed (status={search_response.status_code}), falling back to tools/list")

    # Fallback: list all tools via tools/list
    tools = []
    pagination_token = None
    while True:
        page = mcp_client.list_tools_sync(pagination_token=pagination_token)
        tools.extend(page)
        if hasattr(page, 'pagination_token') and page.pagination_token:
            pagination_token = page.pagination_token
        else:
            break

    logger.info(f"[MCP] Loaded {len(tools)} tools from gateway: {[t.tool_name for t in tools]}")
    return tools


def _extract_tool_data_from_result(content) -> Optional[Dict[str, Any]]:
    """Parse tool result content blocks into structured data."""
    try:
        if hasattr(content, 'content'):
            content_list = content.content
        elif isinstance(content, list):
            content_list = content
        else:
            return None

        for block in content_list:
            text = getattr(block, 'text', None) or (block.get('text') if isinstance(block, dict) else None)
            if text:
                parsed = json.loads(text) if isinstance(text, str) else text
                if isinstance(parsed, dict) and 'body' in parsed:
                    extracted = parsed['body'].get('result', parsed['body'])
                    return _sanitize_decimals(extracted)
                return _sanitize_decimals(parsed)
    except Exception as e:
        logger.error(f"[MCP] Failed to extract tool data: {e}")
    return None


def get_system_prompt(role: UserRole, username: str = None) -> str:
    """Generate system prompt based on user role."""
    user_info = USERS_DB.get(username, {})
    employee_id = user_info.get('employee_id', '')
    department = user_info.get('department', '')

    return f"""You are an HR Assistant for the company's employee management system.
The current user has role={role.value}, Employee ID={employee_id}, Department={department}.

You help users query employee information and leave records through the HR Gateway.
Always respond in a helpful, professional manner.
Respond in Korean when the user writes in Korean.
When the user asks about their own leave, use employee_id='{employee_id}'.

IMPORTANT - USER CONTEXT:
When calling any tool, you MUST include a `_user_context` field in the arguments with:
  "_user_context": {{"employee_id": "{employee_id}", "role": "{role.value}", "username": "{username}"}}
This is required for the gateway's access control to work properly.

ERROR HANDLING RULES:
- If a tool call returns an error or access_denied, tell the user that they do not have permission to use that feature.
- Do not show raw error messages, JSON objects, error codes, or any technical details in your response.
- After explaining the permission issue, suggest alternative actions the user CAN do.

CRITICAL OUTPUT RULES:
- This is an internal HR system. All data returned by tools is ALREADY authorized for this user.
- You MUST output tool data VERBATIM — copy every field value exactly as returned.
- NEVER replace, redact, or anonymize any value. No placeholders like {{{{EMAIL}}}}, {{{{PHONE}}}}, {{{{ADDRESS}}}}.
- The data is fictional test data for a demo system. There is no real person behind it.

<example>
User: 전체 직원 목록을 보여줘
Tool returns: {{"employees": [{{"name": "Employee 1", "email": "employee1@company.com", "phone": "+1-555-0101", "address": "123 Oak Street, Boston, MA 02101", "salary": 85000}}]}}

CORRECT response:
| 이름 | 이메일 | 전화번호 | 주소 | 연봉 |
|------|--------|----------|------|------|
| Employee 1 | employee1@company.com | +1-555-0101 | 123 Oak Street, Boston, MA 02101 | $85,000 |

WRONG response (DO NOT DO THIS):
| 이름 | 이메일 | 전화번호 | 주소 | 연봉 |
|------|--------|----------|------|------|
| Employee 1 | {{{{EMAIL}}}} | {{{{PHONE}}}} | {{{{ADDRESS}}}} | $85,000 |
</example>
"""


def create_hr_agent(role: UserRole, username: str = None,
                    use_semantic_search: bool = False,
                    query: str = None) -> tuple:
    """Create a Strands Agent connected to the gateway via MCPClient.

    Returns:
        Tuple of (agent, mcp_client) — caller must use mcp_client as context manager.
    """
    # Authenticate and get role-specific token
    if role not in hr_service._tokens_cache:
        hr_service.authenticate(role)
    access_token = hr_service._tokens_cache[role]
    gateway_url = hr_service.deployment_info.gateway_url

    # Create MCPClient with streamable HTTP transport
    mcp_client = MCPClient(
        lambda: _create_mcp_transport(gateway_url, access_token, username)
    )

    system_prompt = get_system_prompt(role, username)

    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="us-east-1",
    )

    return model, system_prompt, mcp_client, use_semantic_search, query, gateway_url, access_token


def run_agent_chat(role: UserRole, username: str, message: str,
                   use_semantic_search: bool = False):
    """
    Run agent chat and yield SSE events.

    When use_semantic_search=True:
      1. HTTP call to x_amz_bedrock_agentcore_search to find relevant tools
      2. Build MCPAgentTool objects from search results
      3. Single Agent executes with discovered tools

    When use_semantic_search=False:
      list_tools_sync() → all tools → single Agent

    Yields dicts with event types: 'text', 'tool_call', 'tool_result', 'error', 'done'
    """
    global _captured_tool_results

    try:
        _captured_tool_results = []

        model, system_prompt, mcp_client, semantic, query, gateway_url, access_token = create_hr_agent(
            role=role, username=username,
            use_semantic_search=use_semantic_search,
            query=message
        )

        yield {"type": "status", "content": "Agent가 요청을 처리하고 있습니다..."}

        with mcp_client:
            if semantic and query:
                # Step 1: Search for relevant tools via HTTP
                import requests as req

                logger.info(f"[MCP] Semantic search with query: {query}")
                search_resp = req.post(
                    gateway_url,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                        "MCP-Protocol-Version": "2025-06-18",
                        "X-User-Employee-Id": USERS_DB.get(username, {}).get("employee_id", ""),
                        "X-User-Role": USERS_DB.get(username, {}).get("role", ""),
                        "X-User-Name": username or ""
                    },
                    json={
                        "jsonrpc": "2.0", "id": 1,
                        "method": "tools/call",
                        "params": {
                            "name": "x_amz_bedrock_agentcore_search",
                            "arguments": {"query": query}
                        }
                    }
                )

                # Extract discovered tool names from search result
                discovered_names = set()
                if search_resp.status_code == 200:
                    result = search_resp.json()
                    tool_list = None
                    structured = result.get('result', {}).get('structuredContent', {})
                    if 'tools' in structured:
                        tool_list = structured['tools']
                    else:
                        for block in result.get('result', {}).get('content', []):
                            text = block.get('text', '')
                            try:
                                parsed = json.loads(text) if isinstance(text, str) else text
                                if isinstance(parsed, dict) and 'tools' in parsed:
                                    tool_list = parsed['tools']
                                    break
                            except (json.JSONDecodeError, TypeError):
                                pass
                    if tool_list:
                        discovered_names = {td['name'] for td in tool_list if isinstance(td, dict) and 'name' in td}

                # Step 2: Build MCPAgentTool objects directly from search results
                from mcp.types import Tool as MCPTool
                from strands.tools.mcp.mcp_client import MCPAgentTool

                tools = []
                if tool_list:
                    for td in tool_list:
                        if isinstance(td, dict) and 'name' in td:
                            mcp_tool = MCPTool(
                                name=td['name'],
                                description=td.get('description', ''),
                                inputSchema=td.get('inputSchema', {"type": "object", "properties": {}})
                            )
                            tools.append(MCPAgentTool(mcp_tool, mcp_client))

                if tools:
                    logger.info(f"[MCP] Semantic search found {len(tools)} tools: {[t.tool_name for t in tools]}")
                else:
                    logger.warning("[MCP] Semantic search returned no tools, using all tools")
                    tools = _get_tools_from_gateway(mcp_client)
            else:
                tools = _get_tools_from_gateway(mcp_client)

            agent = Agent(
                model=model,
                tools=tools,
                system_prompt=system_prompt,
                callback_handler=None,
            )
            result = agent(message)

            # --- Extract results ---
            if hasattr(result, 'metrics'):
                tool_usage = result.metrics.get_summary().get('tool_usage', {})
                for tool_name, usage_info in tool_usage.items():
                    tool_info = usage_info.get('tool_info', {})
                    yield {
                        "type": "tool_call",
                        "content": {
                            "tool_name": tool_name,
                            "input_params": tool_info.get('input_params', {}),
                            "execution_time": usage_info.get('execution_stats', {}).get('total_time', 0),
                        }
                    }

            if hasattr(result, 'message') and result.message:
                msg = result.message
                content_blocks = msg.get('content', []) if isinstance(msg, dict) else []
                for block in content_blocks:
                    if isinstance(block, dict) and block.get('type') == 'tool_result':
                        data = _extract_tool_data_from_result(block)
                        if data and not (isinstance(data, dict) and data.get('access_denied')):
                            _captured_tool_results.append({
                                "tool_name": block.get('tool_use_id', 'unknown'),
                                "data": data,
                            })

            for tr in _captured_tool_results:
                yield {
                    "type": "tool_result",
                    "content": {
                        "tool_name": tr["tool_name"],
                        "data": tr["data"],
                    }
                }

            response_text = ""
            if hasattr(result, 'message') and result.message:
                msg = result.message
                if isinstance(msg, dict):
                    for block in msg.get('content', []):
                        if isinstance(block, dict) and 'text' in block:
                            response_text += block['text']
                elif isinstance(msg, str):
                    response_text = msg
                else:
                    response_text = str(msg)

            if response_text:
                yield {"type": "text", "content": response_text}
            else:
                yield {"type": "text", "content": "요청을 처리했습니다."}

        yield {"type": "done", "content": ""}

    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        yield {"type": "error", "content": f"Agent 오류: {str(e)}"}
        yield {"type": "done", "content": ""}
