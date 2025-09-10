# OpenAPI Generator Agent

A serverless AI agent built with the Strands framework that generates comprehensive OpenAPI 3.0 specifications for Amazon API Gateway REST APIs based on natural language requirements.

## Features

- **AI-Powered Generation**: Uses Amazon Bedrock (Claude 3.5 Sonnet) to create OpenAPI specifications from natural language descriptions
- **API Gateway Optimized**: Includes AWS-specific extensions and configurations for seamless API Gateway deployment
- **Best Practices Built-in**: Automatically includes request validation, CORS, authentication, and proper error handling
- **Complete Specifications**: Generates schemas, operation IDs, tags, descriptions, and examples
- **Standards Compliant**: Produces valid OpenAPI 3.0 specifications with proper structure and documentation

## Architecture

The agent consists of:
- **AWS Lambda**: Serverless function (Python 3.13) for specification generation
- **Strands Framework**: Agent orchestration and prompt management
- **Amazon Bedrock**: AI model for intelligent OpenAPI generation (Claude 3.5 Sonnet)

## Prerequisites

- AWS CLI configured with appropriate permissions
- SAM CLI installed
- Python 3.13 or later
- Access to Amazon Bedrock (Claude 3.5 Sonnet model)

## Deployment

### 1. Build the application

```bash
sam build
```

### 2. Deploy the application

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

This starts an interactive session for testing the agent locally.

## Generated Features

The agent automatically includes:

### API Gateway Extensions
- Request validators for query parameters and headers
- CORS configuration when needed
- Lambda authorizers for JWT/OIDC authentication
- Proper integration configurations
- VPC endpoint configurations for private APIs

### OpenAPI Best Practices
- Comprehensive operation tags and descriptions
- Unique operation IDs for each endpoint
- Request/response schemas in components section
- Proper error response definitions
- Server and contact information
- Pagination patterns for list operations

### Validation & Quality
- Built-in OpenAPI specification validation
- AWS extension compliance
- Proper ARN formatting and CloudFormation functions

## Configuration

### Environment Variables

- `BEDROCK_MODEL`: Bedrock model ID for specification generation

### Dependencies

- `strands-agents`: Core agent framework
- `strands-agents-tools`: Additional agent tools

### IAM Permissions

The Lambda function requires:
- **Bedrock**: Model invocation permissions
- **CloudWatch**: Log creation and writing

## Output Format

The agent returns a complete OpenAPI 3.0 specification in YAML format, ready for:
- Direct import into API Gateway
- Use with SAM or CloudFormation templates
- Documentation generation
- Client SDK generation

## Monitoring

- **CloudWatch Logs**: Detailed execution logs with request/response tracking
- **CloudWatch Metrics**: Standard Lambda metrics
- **Error Handling**: Comprehensive error logging and reporting

## Cleanup

```bash
sam delete
```

