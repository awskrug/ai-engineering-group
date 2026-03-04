# client.py
import os
import sys
import base64
import hashlib
import hmac
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from typing import TypeVar, Any
import json


async def call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> Any:
    """
    MCP 서버의 도구를 호출하는 함수
    블로그의 callMCPTool에 해당
    """
    region = os.environ['REGION']
    agent_arn = os.environ['AGENT_ARN']
    bearer_token = os.environ['BEARER_TOKEN']

    if not agent_arn or not bearer_token:
        print("Error: AGENT_ARN or BEARER_TOKEN environment variable is not set")
        sys.exit(1)
    if not agent_arn or not bearer_token:
        print("Error: AGENT_ARN or BEARER_TOKEN environment variable is not set")
        sys.exit(1)
    
    encoded_arn = agent_arn.replace(':', '%3A').replace('/', '%2F')
    mcp_url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
    headers = {"authorization": f"Bearer {bearer_token}","Content-Type":"application/json"}
    #print(f"Invoking: {mcp_url}, \nwith headers: {headers}\n")

    async with streamablehttp_client(mcp_url, headers, timeout=120, terminate_on_close=False) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            #print("session intialized")
            tool_result = await session.call_tool(tool_name, arguments)
            #print(tool_result)
            return tool_result


async def list_tools() -> list[dict]:
    """사용 가능한 도구 목록 조회"""
    region = os.environ['REGION']
    agent_arn = os.environ['AGENT_ARN']
    bearer_token = os.environ['BEARER_TOKEN']

    if not agent_arn or not bearer_token:
        print("Error: AGENT_ARN or BEARER_TOKEN environment variable is not set")
        sys.exit(1)
    if not agent_arn or not bearer_token:
        print("Error: AGENT_ARN or BEARER_TOKEN environment variable is not set")
        sys.exit(1)
    
    encoded_arn = agent_arn.replace(':', '%3A').replace('/', '%2F')
    mcp_url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
    headers = {"authorization": f"Bearer {bearer_token}","Content-Type":"application/json"}
    #print(f"Invoking: {mcp_url}, \nwith headers: {headers}\n")

    async with streamablehttp_client(mcp_url, headers, timeout=120, terminate_on_close=False) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            #print("session intialized")
            tool_result = await session.list_tools()
            #print(tool_result)
            return tool_result


async def read_resource(uri: str) -> Any:
    """MCP 리소스 읽기"""
    region = os.environ['REGION']
    agent_arn = os.environ['AGENT_ARN']
    bearer_token = os.environ['BEARER_TOKEN']

    if not agent_arn or not bearer_token:
        print("Error: AGENT_ARN or BEARER_TOKEN environment variable is not set")
        sys.exit(1)
    if not agent_arn or not bearer_token:
        print("Error: AGENT_ARN or BEARER_TOKEN environment variable is not set")
        sys.exit(1)
    
    encoded_arn = agent_arn.replace(':', '%3A').replace('/', '%2F')
    mcp_url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
    headers = {"authorization": f"Bearer {bearer_token}","Content-Type":"application/json"}
    #print(f"Invoking: {mcp_url}, \nwith headers: {headers}\n")

    async with streamablehttp_client(mcp_url, headers, timeout=120, terminate_on_close=False) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            #print("session intialized")
            tool_result = await session.read_resource(uri)
            #print(tool_result)
            return tool_result
