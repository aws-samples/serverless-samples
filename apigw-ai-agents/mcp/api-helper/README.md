# API Helper

API Helper is an Amazon Q extension that provides expert guidance and tools for API development, operations, management, and governance on AWS. It leverages Amazon Bedrock agents to deliver specialized assistance for API-related tasks.

## Features

- **API Expert Consultation**: Get answers to questions about API development, best practices, security, and AWS services like API Gateway and AppSync
- **OpenAPI Specification Builder**: Generate OpenAPI/Swagger specifications based on your requirements
- **API Builder**: Create complete API implementations with Infrastructure as Code templates and business logic examples

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
   pip install -e .
   ```

### Environment Variables

The following environment variables must be configured for MCP server to function:

- `AWS_REGION`: AWS region where Bedrock agents are deployed
- `EXPERT_AGENT_ID`: ID of the API Expert Bedrock agent
- `EXPERT_AGENT_ALIAS`: Alias of the API Expert Bedrock agent
- `OAC_BUILDER_AGENT_ID`: ID of the OpenAPI Builder Bedrock agent
- `OAC_BUILDER_AGENT_ALIAS`: Alias of the OpenAPI Builder Bedrock agent
- `API_BUILDER_AGENT_ID`: ID of the API Builder Bedrock agent
- `API_BUILDER_AGENT_ALIAS`: Alias of the API Builder Bedrock agent


## MCP Client Configuration

This directory contains a configuration file [example](../config/mcp.json) and [prompt/rules](../config/q-cli-rules.md) for encouraging and guiding proper usage for the MCP client.

If you are using Amazon Q Developer CLI:
1. Update configuration file with the agent ID and alias ID using output values from the stacks you've deployed using Infrastructure as Code deployment [instructions](../../iac/README.md)
2. Copy configuration file to `~/.aws/amazonq`
3. Copy rules file to `~/.amazonq/rules` (you may need to create this directory first)

**Note that rules guide MCP client to use API Expert for all API related questions and tasks. You may need to adjust them to keep balance between API Expert, other tools, and your development environment built-in capabilities.**

## Tools and integrations

API Helper integrates with MCP client and provides three main tools based on Amazon Bedrock:

### 1. API Expert

Ask questions about API development, management, security, and AWS services:

```
What are the best practices for securing REST APIs on AWS?
```

### 2. OpenAPI Specification Builder

Generate OpenAPI specifications based on your requirements:

```
Build an OpenAPI specification for a pet store API with CRUD operations
```

### 3. API Builder

Create complete API implementations with Infrastructure as Code templates:

```
Build an API for a serverless e-commerce application with Lambda integrations
```

## Development

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



