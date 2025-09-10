# API Inspector Agent

A serverless AI agent built with the Strands framework that analyzes Amazon API Gateway configurations and provides intelligent recommendations based on AWS best practices, security guidelines, and organizational policies.

## Deployment

### 1. Deploy Knowledge Base (if not exists)

Ensure you have deployed the knowledge base stack first. The agent depends on it for organizational best practices.

### 2. Build 

```bash
sam build
```

### 3. Deploy 

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

The agent is designed to be invoked directly as a Lambda function using request in the event. 

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

## Cleanup

```bash
sam delete --stack-name strands-api-inspector-agent
```

