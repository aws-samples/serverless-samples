---
name: "centralized-developer-guidance"
displayName: "Centralized Developer Guidance"
description: "Provides organization-wide, centralized developer guidance. API expertise, best practices, and configuration inspection directly in your IDE."
keywords: ["api-gateway", "governance", "best-practices", "api-expert"]
author: "Your Organization"
---

# Centralized Developer Guidance

## Overview

This power provides centralized, AI-powered developer guidance for your organization. It connects to an Amazon Bedrock AgentCore-based agent that has access to your organization's knowledge base containing best practices, governance requirements, and curated documentation.

**This is a sample implementation, not limited to API development.** While this example focuses on API development guidance, the underlying architecture can be tailored for any use case or development area - security practices, infrastructure patterns, data engineering, frontend development, or any domain where your organization wants to provide centralized guidance. The Knowledge Base content, agent prompts, and tools can all be customized to fit your specific needs.

Unlike project-specific steering files, this power enables organization-wide guidance that can be shared across all teams from a central location. Teams can install this power from a shared directory and receive consistent guidance alongside their project-specific steering files.

**Key capabilities (in this API-focused example):**
- **API Expert Consultation** - Get answers about API development, security, AWS services, and your organization's specific standards
- **API Inspector** - Analyze existing API Gateway configurations and receive improvement recommendations based on AWS best practices and your organization's requirements

**Adapt for your use case** by modifying the Knowledge Base content, agent instructions, and MCP tools to cover your organization's specific domain expertise.

## Available Steering Files

This power includes steering files that provide detailed workflow guidance:

- **api-requirements** - Comprehensive guide for gathering API requirements, covering all aspects from endpoints and authentication to performance and security requirements

## When to Use This Power

Use this power when you need:
- Organization-specific development standards and best practices
- Guidance on API development, management, and governance
- Help with Amazon API Gateway configuration
- Inspection of existing API configurations

## Onboarding

### Prerequisites

Before using this power, your organization needs to deploy the backend infrastructure:

1. **Knowledge Base** - See [strands-agentcore/iac](../strands-agentcore/iac/README.md) for deployment instructions:
   - CloudFormation template: [bedrock-kb-s3.yaml](../strands-agentcore/iac/bedrock-kb-s3.yaml)
   - S3 bucket with organization documentation
   - Bedrock Knowledge Base with vector embeddings
   - Data sources for your content and optionally AWS public docs

2. **AgentCore Agent** - See [strands-agentcore/api-expert-agent](../strands-agentcore/api-expert-agent/README.md) for deployment instructions:
   - Strands-based agent with Knowledge Base access
   - Deployed to Amazon Bedrock AgentCore Runtime

3. **MCP Server** - See [strands-agentcore/mcp](../strands-agentcore/mcp/README.md) for setup details:
   - Python-based FastMCP server
   - Requirements: [api-helper/requirements.txt](../strands-agentcore/mcp/api-helper/requirements.txt)

> **Important:** For production environments, organizations should deploy a remote MCP server with appropriate authentication and authorization instead of running locally on each developer's machine.

### Local Setup

1. Ensure AWS CLI is configured with appropriate credentials
2. Install this power from your organization's shared location

## Best Practices

- **Combine with project steering** - Use this power for organization-wide guidance alongside project-specific `.kiro/steering/` files
- **Keep Knowledge Base updated** - Ensure your platform team regularly syncs the Knowledge Base with latest documentation
- **Review recommendations** - AI-generated advice should be reviewed by humans, especially for security-related decisions
- **Add organization content** - Customize the Knowledge Base with your internal standards, patterns, and governance requirements

## Configuration

### Local MCP Server Setup (Development/Testing)

For local development and testing, configure the MCP server to run on your machine:

**Step 1: Update `mcp.json` with the actual path to `api_helper.py`**

```json
{
  "mcpServers": {
    "api-expert-server": {
      "command": "python",
      "args": [
        "/absolute/path/to/strands-agentcore/mcp/api-helper/api_helper.py"
      ],
      "disabled": false,
      "env": {
        "AWS_REGION": "us-east-1",
        "AGENTCORE_AGENT_ARN": "arn:aws:bedrock-agentcore:us-east-1:123456789012:agent-runtime/XXXXXXXXXX"
      }
    }
  }
}
```

**Step 2: Replace placeholders with your actual values**

| Placeholder | Description | How to Get It |
|-------------|-------------|---------------|
| `/absolute/path/to/.../api_helper.py` | Full path to the MCP server script | Run `pwd` in the `strands-agentcore/mcp/api-helper` directory and append `/api_helper.py` |
| `AWS_REGION` | AWS region where your agent is deployed | Check your AgentCore deployment output |
| `AGENTCORE_AGENT_ARN` | ARN of your Bedrock AgentCore Runtime agent | Get from deployment output or AWS Console: Bedrock → AgentCore → Agents |

**Step 3: Configure AWS credentials**

The MCP server uses boto3 which reads credentials from your AWS configuration. Ensure your `~/.aws/config` has valid credentials

**Step 4: Install Python dependencies**

```bash
cd strands-agentcore/mcp/api-helper
pip install -r requirements.txt
```

**Step 5: Reconnect the MCP server**

After updating `mcp.json`, reconnect the MCP server from the Kiro MCP Server panel to apply changes.

### Remote MCP Server Setup (Production)

> **Important:** For production environments, organizations should deploy a remote MCP server with appropriate authentication and authorization instead of running locally on each developer's machine.

**Benefits of remote MCP server:**
- Centralized credential management (no AWS credentials on developer machines)
- Consistent configuration across all developers
- Audit logging and access control
- Easier updates and maintenance

**Remote server configuration in `mcp.json`:**

```json
{
  "mcpServers": {
    "api-expert-server": {
      "url": "https://your-mcp-server.example.com/sse",
      "headers": {
        "Authorization": "Bearer YOUR_AUTH_TOKEN"
      }
    }
  }
}
```

**Recommended production architecture:**
- Deploy the MCP server behind an API Gateway or Application Load Balancer
- Use OAuth 2.0, OIDC, or your organization's SSO for authentication
- Implement IAM roles for the server to access Bedrock AgentCore
- Enable CloudWatch logging for audit and troubleshooting
- Consider using AWS PrivateLink for private connectivity

### Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|----------|
| `AWS_REGION` | AWS region where AgentCore agent is deployed | Yes |
| `AGENTCORE_AGENT_ARN` | ARN of the Bedrock AgentCore Runtime agent | Yes |

## Sharing This Power

To share this power across your organization:

1. **Host on shared storage** - Place the power directory on a network drive or shared location
2. **Teams install locally** - Each developer adds the power via Kiro Powers UI → "Add Custom Power" → "Local Directory"
3. **Keep synchronized** - Update the shared copy when infrastructure changes


