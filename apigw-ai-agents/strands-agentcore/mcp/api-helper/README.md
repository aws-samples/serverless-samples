# API Helper

API Helper is a Kiro extension that provides expert guidance and tools for API development, operations, management, and governance on AWS. It leverages AI agent running on Amazon Bedrock AgentCore to deliver specialized assistance for API-related tasks.

## Features

- **API Expert Consultation**: Get answers to questions about API development, best practices, security, and AWS services like API Gateway and AppSync
- **API Specification Builder**: Generate OpenAPI/Swagger specifications based on your requirements
- **API Builder**: Create complete API implementations with Infrastructure as Code templates and business logic examples
- **API Inspector**: Inspect configuration of an API gateway endpoint and get improvement recommendations based on general and your organization specific best practices

## Installation

### Prerequisites

- Python 3.13 or higher
- [uv](https://docs.astral.sh/uv/) - Fast Python package manager
- AWS CLI configured with appropriate permissions
- Amazon Bedrock agents configured and accessible

### Setup with uv

1. Clone the repository

2. Install uv (if not already installed):
   ```bash
   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Or with Homebrew
   brew install uv
   ```

3. Sync dependencies:
   ```bash
   cd strands-agentcore/mcp/api-helper
   uv sync
   ```

4. Run the MCP server:
   ```bash
   uv run api_helper.py
   ```

### Environment Variables

The following environment variables must be configured for MCP server to function:

- `AWS_REGION`: AWS region where Bedrock agents are deployed
- `AGENTCORE_AGENT_ARN`: ARN of the API Expert Bedrock AgentCore Runtime agent

## MCP Client Configuration

This directory contains a configuration file [example](../config/mcp.json) for the MCP client.

Example configuration using uv:
```json
{
  "mcpServers": {
    "api-helper": {
      "command": "uv",
      "args": ["--directory", "/path/to/strands-agentcore/mcp/api-helper", "run", "api_helper.py"],
      "env": {
        "AWS_REGION": "us-east-1",
        "AGENTCORE_AGENT_ARN": "arn:aws:bedrock:us-east-1:123456789012:agent-runtime/your-agent-id"
      }
    }
  }
}
```

## Implementation

API Helper is built as a FastMCP server that integrates with Amazon Q. It provides tools that invoke Amazon Bedrock agents:

1. **ask_api_expert**: Connects to an API Expert Bedrock agent to answer questions and provide guidance
2. **inspect_API**: Retrieves and analyzes API Gateway configurations against best practices

Each tool follows a similar pattern:
- Accept a request string from Amazon Q
- Invoke the appropriate Bedrock agent
- Return the agent's response to Amazon Q

### Project Structure

- `api_helper.py`: Main module containing the FastMCP server and tool implementations
- `pyproject.toml`: Project metadata and dependencies (uv/pip compatible)
- `.python-version`: Python version specification for uv

### Adding New Features

To add new API-related tools:

1. Create a new function in `api_helper.py` decorated with `@mcp.tool()`
2. Implement the logic to invoke the appropriate Bedrock agent
3. Update documentation


