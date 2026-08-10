# API Gateway Expert Agent - Strands + AgentCore

## Overview

This agent provides comprehensive API Gateway expertise with the following capabilities:

* **API Management & Governance** - Best practices and recommendations
* **Configuration Inspection** - Analyze and validate API Gateway configurations
* **Requirements Gathering** - Systematic collection of API requirements
* **Service Information** - Retrieve capabilities, quotas, and account settings
* **Knowledge Base Integration** - Access internal standards and AWS documentation

## Architecture

- **Framework**: Strands Agents SDK
- **Runtime**: Amazon Bedrock AgentCore
- **Knowledge Base**: Amazon Bedrock Knowledge Base with S3 Vectors
- **Model**: Amazon Nova Pro (configurable)

## Prerequisites

1. **Install AgentCore CLI**
   ```bash
   pip install bedrock-agentcore-starter-toolkit
   ```

2. **Configure AWS Credentials**
   ```bash
   aws configure
   ```

## Quick Start

### Deploy the Agent

1. **Clone and navigate to directory**
   ```bash
   cd strands-agentcore
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings (especially KB_ID for Knowledge Base)
   source .env
   ```

3. **Run deployment script**
   ```bash
   ./deploy.sh
   ```

The script will:
- Create IAM policy with required permissions (including Knowledge Base access if KB_ID is set)
- Configure agent with AgentCore CLI
- Deploy to AWS using direct code deployment
- Set KNOWLEDGE_BASE_ID environment variable for the agent
- Attach execution policy to agent role
- Display deployment status

### Test the Agent

```bash
agentcore invoke '{"prompt": "What are the best practices for API Gateway?"}' --agent api-expert-agent
```

### Check Status

```bash
agentcore status --agent api-expert-agent
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_NAME` | `api_expert_agent` | Name of the agent |
| `ENTRYPOINT` | `src/main.py` | Python file containing agent code |
| `PYTHON_RUNTIME` | `PYTHON_3_13` | Python runtime version |
| `AWS_REGION` | `us-east-1` | AWS region for deployment |
| `BEDROCK_MODEL` | `us.anthropic.claude-sonnet-4-20250514-v1:0` | Bedrock model to use |
| `KB_ID` | _(empty)_ | Knowledge Base ID (optional) |

### IAM Permissions

The deployment script creates an IAM policy with the following permissions:

- **Bedrock Model Access** - Invoke foundation models
- **API Gateway Read** - Retrieve API configurations and account settings
- **Service Quotas Read** - Get API Gateway quotas
- **WAF Read** - Check WAF configurations
- **Knowledge Base Access** - Retrieve from Bedrock Knowledge Base (if configured)

## Agent Tools

### 1. Knowledge Base Retrieval (`retrieve`)
Query internal standards, style guides, and AWS best practices from the Knowledge Base.

### 2. API Account Info Retriever (`api_account_info_retriever`)
Retrieve account-level API Gateway information:
- VPC links status and limits
- Custom domain limits
- API keys and usage plans
- Client certificates
- CloudWatch role configuration

### 3. API Configuration Retriever (`api_configuration_retriever`)
Examine detailed configurations for specific APIs:
- API details and settings
- Resources and methods
- Stages and deployments
- Authorizers
- WAF integration
- Models and validators
- Documentation

## Usage Examples

### Requirements Gathering
```bash
agentcore invoke '{"prompt": "I need to build a new REST API for user management"}' --agent api-expert-agent
```

### Configuration Inspection
```bash
agentcore invoke '{"prompt": "Inspect API Gateway with ID abc123xyz"}' --agent api-expert-agent
```

### Expert Consulting
```bash
agentcore invoke '{"prompt": "What are the security best practices for API Gateway?"}' --agent api-expert-agent
```

### With Session Context
```bash
# First message
agentcore invoke '{"prompt": "Tell me about API Gateway throttling"}' \
  --agent api-expert-agent \
  --session-id my-session-123

# Follow-up in same session
agentcore invoke '{"prompt": "How do I configure it?"}' \
  --agent api-expert-agent \
  --session-id my-session-123
```

## Local Development

### Start Local Agent
```bash
# Export environment variables first (required for local mode)
export KNOWLEDGE_BASE_ID=<you knowledge base ID>
export BEDROCK_MODEL=us.anthropic.claude-sonnet-4-20250514-v1:0

# Start local agent
agentcore deploy --local
```

### Test Locally
```bash
agentcore invoke '{"prompt": "What are the best practices for API Gateway?"}' --local
```

**Note**: For local deployment, environment variables must be exported in your shell before running `agentcore deploy --local`. The `--env` flag only applies to AWS deployments.

## Management Commands

### Update Agent
```bash
# Modify code, then redeploy
agentcore deploy --agent api-expert-agent --auto-update-on-conflict
```

### View Logs
```bash
# CloudWatch logs
aws logs tail /aws/lambda/agentcore-api-expert-agent --follow

# Or use status command
agentcore status --agent api-expert-agent --verbose
```

### Stop Session
```bash
agentcore stop-session --agent api-expert-agent --session-id SESSION_ID
```

### Destroy Agent
```bash
agentcore destroy --agent api-expert-agent
```

## Project Structure

```
strands-agentcore/
├── src/
│   ├── main.py                          # Agent entrypoint with BedrockAgentCoreApp
│   ├── requirements.txt                 # Python dependencies
│   ├── __init__.py
│   └── tools/
│       ├── __init__.py
│       ├── api_account_info_retriever.py    # Account-level API info tool
│       └── api_configuration_retriever.py   # API configuration tool
├── deploy.sh                            # Deployment script
├── .env.example                         # Environment configuration template
└── README.md                            # This file
```

## Troubleshooting

### AgentCore CLI Not Found
```bash
pip install bedrock-agentcore-starter-toolkit
```

### AWS Authentication Failed
```bash
aws configure
# Or set AWS_PROFILE environment variable
```

### Model Access Denied
- Request model access in AWS Bedrock console
- Verify IAM permissions for Bedrock

### Deployment Failed
- Check CloudWatch logs for detailed errors
- Verify all dependencies are in requirements.txt
- Ensure Python runtime version matches your code

### Policy Attachment Failed
The script automatically attaches the IAM policy to the agent's execution role. If this fails:
```bash
# Get the role name from .bedrock_agentcore.yaml
ROLE_NAME=$(grep "execution_role:" .bedrock_agentcore.yaml | awk '{print $2}' | tr -d '"' | awk -F'/' '{print $NF}')

# Attach policy manually
aws iam attach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn "arn:aws:iam::ACCOUNT_ID:policy/api-expert-agent-execution-policy"
```

## Additional Resources

- [Strands Framework Documentation](https://github.com/strands-agents)
- [Amazon Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html)
- [AgentCore CLI Reference](https://pypi.org/project/bedrock-agentcore-starter-toolkit/)


