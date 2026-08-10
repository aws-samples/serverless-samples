# API Expert Agent

A serverless AI agent built with the Strands framework that provides expert guidance on Amazon API Gateway development, best practices, and troubleshooting by leveraging a comprehensive knowledge base.

## Deployment

### 1. Deploy Knowledge Base (if not already deployed)

Ensure you have deployed the knowledge base stack first. The agent depends on it for retrieving API Gateway expertise.

### 2. Build

```bash
sam build
```

### 3. Deploy

```bash
sam deploy --guided --capabilities CAPABILITY_IAM
```

Configuration parameters:
- **Stack Name**: Your preferred stack name
- **AWS Region**: Target deployment region
- **KnowledgeBaseStackName**: Name of existing knowledge base stack (default: `api-expert-kb`)
- **BedrockModel**: Bedrock model ID (default: `amazon.nova-pro-v1:0`)

### 4. Subsequent deployments

```bash
sam build && sam deploy
```

## Usage

The agent provides expert guidance on API Gateway topics by searching the knowledge base and generating intelligent responses.

### Direct Lambda Invocation

```bash
aws lambda invoke \
  --function-name <function-name> \
  --payload '{"request": "How do I implement rate limiting in API Gateway?"}' \
  response.json
```

### Example Queries

1. **Configuration Questions**:
   ```json
   {
     "request": "What are the best practices for API Gateway caching?"
   }
   ```

2. **Security Guidance**:
   ```json
   {
     "request": "How do I secure my API Gateway endpoints with Lambda authorizers?"
   }
   ```

3. **Performance Optimization**:
   ```json
   {
     "request": "What are the throttling limits for API Gateway and how can I optimize performance?"
   }
   ```

4. **Troubleshooting**:
   ```json
   {
     "request": "My API Gateway is returning 502 errors. What could be the cause?"
   }
   ```

## Configuration

### Environment Variables

- `BEDROCK_MODEL`: Bedrock model ID for AI-powered responses
- `KNOWLEDGE_BASE_ID`: Knowledge base ID (imported from knowledge base stack)
- `MIN_SCORE`: Minimum confidence score for knowledge base retrieval (default: 0.4)

## Cleanup

```bash
sam delete
```

