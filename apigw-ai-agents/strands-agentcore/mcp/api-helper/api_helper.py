# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. 
# SPDX-License-Identifier: MIT-0

from typing import Any
import boto3
import botocore
import os
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.logging import get_logger
import uuid
import json

logger = get_logger(__name__)

config = botocore.config.Config(
    read_timeout=600,
    connect_timeout=600,
    retries={"max_attempts": 0}
)

# Initialize FastMCP server
mcp = FastMCP("api-helper")

@mcp.tool()
async def ask_api_expert(request: str) -> str:
    """ 
    An extensive API expert tool for asking questions and getting guidance related to the APIs and Amazon API Gateway service, API management and governance.
    This tool analyzes request, uses wide knowledge base with latest documentation of the services, best practices and implementation guidance, 
    blog posts, community content, technical support answers.
    
    Use this tool when you received a question, request, task, inquiry related to:
    - API development
    - API management
    - API lifecycle
    - API planning, development, testing
    - Security of the APIs and how to secure APIs
    - Deployment, publishing of the APIs, CI/CD pipelines for APIs
    - Scaling and operating APIs on AWS
    - Monitoring and observability of the APIs, including logging, metrics, tracing
    - API usage analytics, operational and business insights, monetization of the APIs
    - API discoverability, developer portals
    - API first design
    - API best practices
    - API governance, security controls, governance tools, preventative/proactive/detective/responsive controls for APIs
    - Amazon API Gateway service
    - REST implementation
    - Build API for a use case
    - Build a microservice
    - Build web application backend
    - Build mobile application backend
    - Build Infrastructure as Code template for an API

    Args:
        request: 
            question for the API Expert 
    """
    
    # Initialize the Bedrock Agent Runtime client
    agentcore_runtime = boto3.client(
        'bedrock-agentcore',
        region_name=os.getenv("AWS_REGION"),
        config=config
    )
    try:
        logger.debug(f"API Expert tool request: {request}")
        session_id= "api_expert_session_"+str(uuid.uuid4())
        payload = json.dumps({"request": request}).encode()
        # Invoke bedrock API Expert agent and get response
        response = agentcore_runtime.invoke_agent_runtime(
            agentRuntimeArn=os.getenv("AGENTCORE_AGENT_ARN"),
            runtimeSessionId=session_id,
            payload=payload
        )
        result=response["response"].read().decode('utf-8')

        logger.debug(f"API Expert agent response: {result}")
        return result
    except Exception as e:
        logger.error(f"Error invoking API Expert agent: {e}")
        return "Error: Could not complete requested action."



@mcp.tool()
async def inspect_API(request: str) -> str:
    """ 
    An API inspector tool retrieves and inspects API definition and configuration.
    This tool is designed to analyze and identify potential issues in API Gateway configurations and OpenAPI specifications. 

    Use this tool to inspect and evaluate API endpoints against AWS best practices, security standards, and Well-Architected principles. 
    
    The tool retrieves API configuration data directly from AWS accounts when provided with an API ID. 
    It examines critical aspects including:
     - security configurations, 
     - throttling settings,
     - resource limits, 
     - request validation,
     - WAF integration, 
     - observability setups, 
     - documentation completeness. 
     
     After analysis, tool delivers a structured assessment of identified issues alongside actionable recommendations for improvement.
    
    Args:
        request: 
            ID of an API to be inspected 
    """
    
    # Initialize the Bedrock Agent Runtime client
    agentcore_runtime = boto3.client(
        'bedrock-agentcore',
        region_name=os.getenv("AWS_REGION"),
        config=config
    )
    try:
        logger.debug(f"API Inspector tool request: {request}")
        session_id= "api_inspector_session_"+api_id+str(uuid.uuid4())
        payload = json.dumps({"request": f"Inspect API with ID {request} and provide improvement recommendations"}).encode()

        # Invoke bedrock API Expert agent and get response
        response = agentcore_runtime.invoke_agent_runtime(
            agentRuntimeArn=os.getenv("AGENTCORE_AGENT_ARN"),
            runtimeSessionId=session_id,
            payload=payload
        )
        result=result = response["response"].read().decode('utf-8')

        logger.debug(f"API Inspector agent response: {result}")
        return result
    except Exception as e:
        logger.error(f"Error invoking API Inspector agent: {e}")
        return "Error: Could not complete requested action."


if __name__ == "__main__":
    # Initialize and run the server
    logger.info("Starting API Helper MCP server")
    mcp.run(transport='stdio')
