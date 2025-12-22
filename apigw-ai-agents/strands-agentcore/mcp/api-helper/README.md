# API Helper

API Helper is an Amazon Q and Kiro extension that provides expert guidance and tools for API development, operations, management, and governance on AWS. It leverages AI agent running on Amazon Bedrock AgentCore to deliver specialized assistance for API-related tasks.

## Features

- **API Expert Consultation**: Get answers to questions about API development, best practices, security, and AWS services like API Gateway and AppSync
- **API Specification Builder**: Generate OpenAPI/Swagger specifications based on your requirements
- **API Builder**: Create complete API implementations with Infrastructure as Code templates and business logic examples
- **API Inspector**: Inspect configuration of an API gateway endpoint and get improvement recommendations based on general and your organization specific best practices

## Installation

### Prerequisites

- Python 3.13 or higher
- AWS CLI configured with appropriate permissions
- Amazon Bedrock agents configured and accessible

### Setup

1. Clone the repository
2. Set up a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install the package:
   ```bash
   pip install -r requirements.txt
   ```

### Environment Variables

The following environment variables must be configured for MCP server to function:

- `AWS_REGION`: AWS region where Bedrock agents are deployed
- `EXPERT_AGENT_ARN`: ID of the API Expert Bedrock AgentCore Runtime agent

## MCP Client Configuration

This directory contains a configuration file [example](../config/mcp.json) for the MCP client.


## Implementation

API Helper is built as a FastMCP server that integrates with Amazon Q. It provides three main tools that invoke Amazon Bedrock agents:

1. **ask_api_expert**: Connects to an API Expert Bedrock agent to answer questions and provide guidance
2. **build_openapi_specification**: Invokes a specialized Bedrock agent to generate OpenAPI specifications
3. **build_API**: Leverages a Bedrock agent to create complete API implementations with IaC templates

Each tool follows a similar pattern:
- Accept a request string from Amazon Q
- Invoke the appropriate Bedrock agent
- Return the agent's response to Amazon Q

### Project Structure

- `api_helper.py`: Main module containing the FastMCP server and tool implementations.
- `pyproject.toml`: Project metadata and dependencies

### Adding New Features

To add new API-related tools:

1. Create a new function in `api_helper.py` decorated with `@mcp.tool()`
2. Implement the logic to invoke the appropriate Bedrock agent
3. Update documentation



