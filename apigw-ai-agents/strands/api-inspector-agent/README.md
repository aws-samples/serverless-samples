# API Inspector Agent

A serverless AI agent built with the Strands framework that analyzes Amazon API Gateway configurations and provides intelligent recommendations based on AWS best practices, security guidelines, and organizational policies.

## Features

- **AI-Powered Analysis**: Uses Amazon Bedrock (Claude 3.7 Sonnet) for intelligent configuration review
- **API Configuration Inspection**: Comprehensive analysis of existing API Gateway REST APIs
- **Account-Level Assessment**: Reviews account quotas, limits, and configurations
- **Knowledge Base Integration**: Leverages organizational best practices from a centralized knowledge base
- **Security & Compliance**: Identifies security vulnerabilities and compliance issues
- **Well-Architected Alignment**: Ensures configurations follow AWS Well-Architected principles
- **OpenAPI Specification Review**: Analyzes API definitions for best practices

## Architecture

The agent is built using:
- **AWS Lambda**: Serverless function (Python 3.13) for agent execution
- **Strands Framework**: Agent orchestration and tool integration
- **Amazon Bedrock**: AI model for intelligent analysis (Claude 3.7 Sonnet)
- **Amazon Bedrock Knowledge Base**: Organizational best practices and guidelines
- **Custom Tools**: API configuration and account information retrievers

## Prerequisites

- AWS CLI configured with appropriate permissions
- SAM CLI installed
- Python 3.13 or later
- Access to Amazon Bedrock (Claude 3.7 Sonnet model)
- Existing Knowledge Base stack (default: `api-inspector-kb`)

## Deployment

### 1. Deploy Knowledge Base (if not exists)

Ensure you have deployed the knowledge base stack first. The agent depends on it for organizational best practices.

### 2. Build the application

```bash
sam build
```

### 3. Deploy the application

```bash
sam deploy --guided
```

Configuration parameters:
- **Stack name**: `strands-api-inspector-agent` (default)
- **AWS Region**: Target deployment region
- **KnowledgeBaseStackName**: Name of existing knowledge base stack (default: `api-inspector-kb`)
- **BedrockModel**: Bedrock model ID (default: `us.anthropic.claude-3-7-sonnet-20250219-v1:0`)

### 4. Verify deployment

```bash
aws cloudformation describe-stacks --stack-name strands-api-inspector-agent --query 'Stacks[0].Outputs'
```

## Usage

The agent is designed to be invoked directly as a Lambda function, not through API Gateway. It accepts three types of analysis requests:

### 1. API Configuration Analysis

Analyze a specific API Gateway REST API:

```python
event = {
    "request": "your-api-gateway-id"
}
```

### 2. OpenAPI Specification Review

Analyze an OpenAPI specification:

```python
event = {
    "request": "Please analyze this OpenAPI spec: [paste your OpenAPI specification here]"
}
```

### 3. Account Configuration Assessment

Review account-level API Gateway settings:

```python
event = {
    "request": "Please analyze my API Gateway account configuration"
}
```

### Response Format

The agent returns structured analysis in text format with three sections:

```
<assessment>
[Detailed analysis of identified issues and configurations]
</assessment>

<recommendations>
[Specific actionable recommendations with documentation links]
</recommendations>

<organizational_best_practices>
[Organization-specific recommendations from knowledge base]
</organizational_best_practices>
```

## Local Development

### Interactive Testing

```bash
python src/main.py
```

This starts an interactive session where you can input API IDs for analysis.

### SAM Local Testing

```bash
sam local invoke ApiInspectorAgentFunction --event events/test-event.json
```

## Configuration

### Environment Variables

- `BEDROCK_MODEL`: Bedrock model ID for AI analysis
- `KNOWLEDGE_BASE_ID`: Knowledge base ID (imported from knowledge base stack)
- `MIN_SCORE`: Minimum relevance score for knowledge base retrieval (default: 0.4)

### Dependencies

The agent uses these key dependencies:
- `strands-agents>=1.0.0`: Core agent framework
- `strands-agents-tools>=0.2.0`: Pre-built tools including knowledge base retrieval
- `boto3>=1.34.0`: AWS SDK for API Gateway and Bedrock operations

### IAM Permissions

The Lambda function requires:
- **Bedrock**: Model invocation and knowledge base retrieval
- **API Gateway**: Read access to REST APIs, stages, resources, and account settings
- **CloudWatch**: Log creation and writing

## Analysis Capabilities

### API Configuration Review
- Resource and stage limits (300 resources, 10 stages)
- Authentication and authorization settings
- Caching and throttling configurations
- Request/response validation
- WAF integration status
- Observability settings (logging, tracing, metrics)
- Security vulnerabilities (API keys, resource policies)

### Account Assessment
- VPC links status and limits (20 default)
- Custom domain limits (120 public, 50 private)
- API keys and usage plans quotas
- Client certificates count (60 default)
- CloudWatch role configuration

### OpenAPI Specification Analysis
- Security schemes and error responses
- Operation documentation and examples
- Pagination implementation
- API Gateway extensions
- Response models and validation

## Cleanup

```bash
sam delete --stack-name strands-api-inspector-agent
```

## Troubleshooting

### Common Issues

1. **Knowledge Base Not Found**: Ensure the knowledge base stack exists and is properly named
2. **Bedrock Access Denied**: Verify Bedrock model access in your AWS account and region
3. **API Gateway Permissions**: Check that the Lambda execution role has sufficient API Gateway read permissions

### Debugging

Enable detailed logging by checking CloudWatch Logs for the Lambda function. All API calls and errors are logged with appropriate context.
