# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. 
# SPDX-License-Identifier: MIT-0

from typing import Any
import boto3
import botocore
import os
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.logging import get_logger
import uuid

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
    An extensive API expert tool for asking questions and getting guidance related to the APIs, Amazon API Gateway, and AWS AppSync services.
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
    - AWS AppSync service
    - REST, HTTP, GraphQL implementation

    Args:
        request: 
            question for the API Expert 
    """
    
    # Initialize the Bedrock Agent Runtime client
    bedrock_agent_runtime = boto3.client(
        'bedrock-agent-runtime',
        region_name=os.getenv("AWS_REGION"),
        config=config
    )
    try:
        logger.debug(f"API Expert tool request: {request}")
        # Invoke bedrock API Expert agent and get response
        response = bedrock_agent_runtime.invoke_agent(
            agentId=os.getenv("EXPERT_AGENT_ID"),
            agentAliasId=os.getenv("EXPERT_AGENT_ALIAS"),
            sessionId=str(uuid.uuid4()),
            inputText=request
        )
        result=""
        for event in response.get("completion"):
            result+=event['chunk']['bytes'].decode('utf-8')

        logger.debug(f"API Expert agent response: {result}")
        return result
    except Exception as e:
        logger.error(f"Error invoking API Expert agent: {e}")
        return "Error: Could not complete requested action."


@mcp.tool()
async def build_openapi_specification(request: str) -> str:
    """ 
    An OpenAPI definition/specification builder tool for building OpenAPI specification. It follows use case and requirements provided and builds API specification 
    which allows both humans and computers to discover and understand the capabilities of the service without access to source code, documentation, or through network traffic inspection.
    Specification uses Amazon API Gateway specific extensions that allows it to be used in Infrastructure as Code templates.
    
    Use this tool when you received a request, task, asking to:
    - Build API specification for a use case
    - Build OpenAPI specification for an API
    - Build Swagger specification
    - Create Swagger file

    Collect use case description and requirements FIRST, before using this tool. ASK following questions if needed.
        Ask user to describe use case in more details if it is not in the original request.
        Also ask the user the following questions to identify features required for the project:
        - What is your preferred programming language to be used if code examples need to be generated?
        - Do you need a private or public API endpoint?
        - What is the integration target for the API? Valid options:
            - Existing public resource over HTTP
            - Lambda function
            - Other AWS service
            - Existing resources in a private VPC (e.g., container orchestrator, on-premises applications accessible via DirectConnect)
        - What identity provider will be used to determine authentication and authorization for the API? Valid options:
            - None
            - IAM
            - Amazon Cognito
            - 3rd party OIDC/OAuth compliant identity provider
            - Custom
        (Do not offer to use API keys for authentication/authorization.)
        - Are rate limiting and usage quotas needed?
        - Will you use this API by a web application and need to add CORS configuration to the API? If yes, which domains should be allowed?
        - What CI/CD tools do you use or are familiar with?

        If integration target uses existing public resources over HTTP, ask follow-up question:
        - What is URL of the resource to be used in the integration target definition

        If integration target uses existing resources in a private VPC, ask follow-up questions:
        - What is load balancer ARN to be used in VPC Link configuration
        - What is load balancer DNS name to be used in the integration target definition

        If integration target uses Lambda functions, ask follow-up questions:
        - Are these new or already existing Lambda functions
        - In case of already existing functions - what are ARN of the functions to be used for each resource and method

        If CORS configuration is needed and domain was not provided, ask follow-up question:
        - Which domain should be allowed in the CORS configuration

    Args:
        request: 
            API requirements to be used while building OpenAPI specification 
    """
    
    # Initialize the Bedrock Agent Runtime client
    bedrock_agent_runtime = boto3.client(
        'bedrock-agent-runtime',
        region_name=os.getenv("AWS_REGION"),
        config=config
    )
    try:
        logger.debug(f"OpenAPI Builder tool request: {request}")
        # Invoke bedrock API Expert agent and get response
        response = bedrock_agent_runtime.invoke_agent(
            agentId=os.getenv("OAC_BUILDER_AGENT_ID"),
            agentAliasId=os.getenv("OAC_BUILDER_AGENT_ALIAS"),
            sessionId=str(uuid.uuid4()),
            inputText=request
        )
        result=""
        for event in response.get("completion"):
            result+=event['chunk']['bytes'].decode('utf-8')

        logger.debug(f"OpenAPI Builder agent response: {result}")
        return result
    except Exception as e:
        logger.error(f"Error invoking OpenAPI Builder agent: {e}")
        return "Error: Could not complete requested action."

@mcp.tool()
async def build_API(request: str) -> str:
    """ 
    An API builder tool for building APIs with Infrastructure as Code templates and business logic examples. It follows use case and requirements provided and builds OpenAPI Specification, 
    Infrastructure as Code template, business logic placeholders and samples. 

    Use this tool when you received a request, task, asking to:
    - Build API for a use case
    - Build a microservice
    - Build web application backend
    - Build mobile application backend
    - Build Infrastructure as Code template for an API

    Collect use case description and requirements FIRST, before using this tool. ASK following questions if needed.
        Ask user to describe use case in more details if it is not in the original request.
        Also ask the user the following questions to identify features required for the project:
        - What is your preferred programming language to be used if code examples need to be generated?
        - Do you need a private or public API endpoint?
        - What is the integration target for the API? Valid options:
            - Existing public resource over HTTP
            - Lambda function
            - Other AWS service
            - Existing resources in a private VPC (e.g., container orchestrator, on-premises applications accessible via DirectConnect)
        - What identity provider will be used to determine authentication and authorization for the API? Valid options:
            - None
            - IAM
            - Amazon Cognito
            - 3rd party OIDC/OAuth compliant identity provider
            - Custom
        (Do not offer to use API keys for authentication/authorization.)
        - Are rate limiting and usage quotas needed?
        - Will you use this API by a web application and need to add CORS configuration to the API? If yes, which domains should be allowed?
        - What CI/CD tools do you use or are familiar with?

        If API uses private endpoint, ask follow-up questions:
        - What is VPC ID from where this API should be accessible
        - What are subnet IDs from where this API should be accessible

        If integration target uses existing public resources over HTTP, ask follow-up question:
        - What is URL of the resource to be used in the integration target definition

        If integration target uses existing resources in a private VPC, ask follow-up questions:
        - What is load balancer ARN to be used in VPC Link configuration
        - What is load balancer DNS name to be used in the integration target definition

        If integration target uses Lambda functions, ask follow-up questions:
        - Are these new or already existing Lambda functions
        - In case of already existing functions - what are ARN of the functions to be used for each resource and method
        - if new functions will be used - should functions generated include basics business logics

        If authentication uses Amazon Cognito, ask follow-up question:
        - Do you want to use existing Amazon Cognito user pool, and if so - what is ID of the user pool

        If CORS configuration is needed and domain was not provided, ask follow-up question:
        - Which domain should be allowed in the CORS configuration
    
    Args:
        request: 
            Use case description and requirements to be used while building API 
    """
    
    # Initialize the Bedrock Agent Runtime client
    bedrock_agent_runtime = boto3.client(
        'bedrock-agent-runtime',
        region_name=os.getenv("AWS_REGION"),
        config=config
    )
    try:
        logger.debug(f"API Builder tool request: {request}")
        # Invoke bedrock API Expert agent and get response
        response = bedrock_agent_runtime.invoke_agent(
            agentId=os.getenv("API_BUILDER_AGENT_ID"),
            agentAliasId=os.getenv("API_BUILDER_AGENT_ALIAS"),
            sessionId=str(uuid.uuid4()),
            inputText=request
        )
        result=""
        for event in response.get("completion"):
            result+=event['chunk']['bytes'].decode('utf-8')

        logger.debug(f"API Builder agent response: {result}")
        return result
    except Exception as e:
        logger.error(f"Error invoking API Builder agent: {e}")
        return "Error: Could not complete requested action."


if __name__ == "__main__":
    # Initialize and run the server
    logger.info("Starting API Helper MCP server")
    mcp.run(transport='stdio')
