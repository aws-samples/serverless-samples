# API Builder Agent

A comprehensive serverless AI agent built with the Strands framework that generates complete API projects including OpenAPI specifications, AWS SAM Infrastructure as Code templates, and Lambda function code placeholders based on natural language requirements.

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
- **BedrockModel**: Bedrock model ID (default: `us.anthropic.claude-3-7-sonnet-20250219-v1:0`)

### 3. Subsequent deployments

```bash
sam build && sam deploy
```

## Usage

The agent accepts comprehensive API requirements and generates a complete project structure including OpenAPI specifications, SAM templates, and Lambda function code.

### Direct Lambda Invocation

```bash
aws lambda invoke \
  --function-name <function-name> \
  --payload '{"request": "Create a complete REST API for a task management system with user authentication, CRUD operations for tasks, and proper error handling. Use Python for Lambda functions."}' \
  response.json
```

### Example Requests

1. **E-commerce API**:
   ```json
   {
     "request": "Build a complete e-commerce API with product catalog, shopping cart, order management, and payment processing. Include JWT authentication and rate limiting. Use Node.js for Lambda functions."
   }
   ```

2. **User Management System**:
   ```json
   {
     "request": "Create a user management API with registration, login, profile management, and admin functions. Use Amazon Cognito for authentication and Python for backend functions."
   }
   ```

3. **Private Microservice**:
   ```json
   {
     "request": "Generate a private API for internal microservices communication with VPC endpoints, Lambda integrations, and comprehensive logging. Use Java for Lambda functions."
   }
   ```

### Local Development

```bash
python src/main.py
```

## Configuration

### Environment Variables

- `BEDROCK_MODEL`: Bedrock model ID for project generation

## Cleanup

```bash
sam delete
```
