# OpenAPI Generator Agent

A serverless AI agent built with the Strands framework that generates comprehensive OpenAPI 3.0 specifications for Amazon API Gateway REST APIs based on natural language requirements.


## Deployment

### 1. Build 

```bash
sam build
```

### 2. Deploy 

```bash
sam deploy --guided --capabilities CAPABILITY_IAM
```

Configuration parameters:
- **Stack name**: Your preferred stack name
- **AWS Region**: Target deployment region
- **BedrockModel**: Bedrock model ID (default: `us.anthropic.claude-3-5-sonnet-20240620-v1:0`)

### 3. Subsequent deployments

```bash
sam build && sam deploy
```

## Usage

The agent accepts natural language descriptions of API requirements and generates complete OpenAPI 3.0 specifications.

### Direct Lambda Invocation

```bash
aws lambda invoke \
  --function-name <function-name> \
  --payload '{"request": "Create an OpenAPI specification for a pet store API with endpoints to create, read, update, and delete pets. Include authentication using API keys."}' \
  response.json
```

### Example Requests

1. **Basic CRUD API**:
   ```json
   {
     "request": "Generate OpenAPI spec for a user management API with CRUD operations, JWT authentication, and proper error handling"
   }
   ```

2. **E-commerce API**:
   ```json
   {
     "request": "Create OpenAPI specification for an e-commerce API with product catalog, shopping cart, and order management endpoints"
   }
   ```

3. **Private API**:
   ```json
   {
     "request": "Build a private API specification for internal microservices with Lambda integrations and VPC endpoints"
   }
   ```

### Local Development

```bash
python src/main.py
```

## Configuration

### Environment Variables

- `BEDROCK_MODEL`: Bedrock model ID for specification generation


## Cleanup

```bash
sam delete
```

