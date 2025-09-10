# API Builder Agent

A comprehensive serverless AI agent built with the Strands framework that generates complete API projects including OpenAPI specifications, AWS SAM Infrastructure as Code templates, and Lambda function code placeholders based on natural language requirements.

## Features

- **Complete Project Generation**: Creates OpenAPI specs, SAM templates, and code placeholders in one go
- **AI-Powered Architecture**: Uses Amazon Bedrock (Claude 3.7 Sonnet) for intelligent project generation
- **AWS SAM Integration**: Generates production-ready SAM templates with best practices
- **Multi-Language Support**: Creates Lambda function placeholders in user's preferred programming language
- **Security & Compliance**: Includes proper IAM roles, logging, and security configurations
- **Best Practices Built-in**: Automatically includes request validation, CORS, monitoring, and error handling
- **Comprehensive Documentation**: Generates project documentation and next steps guidance

## Architecture

The agent consists of:
- **AWS Lambda**: Serverless function (Python 3.13) for project generation
- **Strands Framework**: Agent orchestration and prompt management
- **Amazon Bedrock**: AI model for intelligent code and template generation (Claude 3.7 Sonnet)

## Prerequisites

- AWS CLI configured with appropriate permissions
- SAM CLI installed
- Python 3.13 or later
- Access to Amazon Bedrock (Claude 3.7 Sonnet model)

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

This starts an interactive session for testing the agent locally.

## Generated Components

### 1. OpenAPI 3.0 Specification
- Complete API definition with paths, methods, and schemas
- AWS API Gateway extensions and integrations
- Request validators and CORS configuration
- Authentication and authorization schemes
- Comprehensive documentation and examples

### 2. AWS SAM Template
- **API Gateway**: REST API with proper configuration
- **Lambda Functions**: Serverless functions for business logic
- **IAM Roles**: Least-privilege permissions for all resources
- **CloudWatch**: Logging, metrics, and monitoring setup
- **VPC Configuration**: Private API support with VPC endpoints
- **Usage Plans**: Rate limiting and throttling configuration

### 3. Lambda Function Code
- **Multi-language Support**: Python, Node.js, Java, etc.
- **Code Placeholders**: Structured function templates
- **Documentation**: Inline comments and function descriptions
- **Business Logic**: Basic implementation when requested

### 4. Project Documentation
- **Next Steps Guide**: Implementation roadmap
- **Monitoring Setup**: CloudWatch metrics and X-Ray tracing
- **Testing Strategy**: Unit testing and API validation
- **CI/CD Pipeline**: Deployment automation guidance

## Advanced Features

### Security & Compliance
- **Lambda Authorizers**: Custom authentication logic
- **Amazon Cognito**: User pool integration
- **IAM Policies**: Fine-grained access control
- **VPC Integration**: Private API configurations
- **Request Validation**: Input sanitization and validation

### Monitoring & Observability
- **CloudWatch Logs**: Execution and access logging
- **CloudWatch Metrics**: API performance monitoring
- **X-Ray Tracing**: Request flow visualization
- **Error Handling**: Comprehensive error responses

### Infrastructure Best Practices
- **Resource Naming**: Consistent naming conventions
- **Parameter Management**: Configurable deployments
- **Output Exports**: Cross-stack resource sharing
- **Cleanup Procedures**: Resource lifecycle management

## Configuration

### Environment Variables

- `BEDROCK_MODEL`: Bedrock model ID for project generation

### Dependencies

- `strands-agents`: Core agent framework

### IAM Permissions

The Lambda function requires:
- **Bedrock**: Model invocation permissions
- **CloudWatch**: Log creation and writing

## Response Format

The agent returns a structured response containing:

```xml
<response>
  <!-- OpenAPI 3.0 Specification -->
  <!-- AWS SAM Template -->
  <!-- Lambda Function Code -->
  <!-- Project Documentation -->
  <!-- Security Warnings -->
  <!-- Next Steps Guide -->
</response>
```

## Security Considerations

The agent includes this important warning in all responses:
> "This response might contain information related to security, a nuanced topic. You should verify the response using informed human judgement."

Always review generated security configurations and adapt them to your specific requirements.

## Monitoring

- **CloudWatch Logs**: Detailed execution logs with request/response tracking
- **CloudWatch Metrics**: Standard Lambda metrics
- **Error Handling**: Comprehensive error logging and reporting

## Cleanup

```bash
sam delete
```
