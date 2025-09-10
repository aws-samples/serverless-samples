# API Requirements Gatherer Agent

An interactive AI agent built with the Strands framework that systematically gathers comprehensive requirements for Amazon API Gateway projects through intelligent questioning and conversation flow.

## Features

- **Interactive Requirements Gathering**: Conducts structured conversations to collect all necessary API project details
- **Comprehensive Questionnaire**: Covers authentication, integration targets, security, networking, and deployment requirements
- **AI-Powered Conversation**: Uses Amazon Bedrock (Nova Pro) for intelligent follow-up questions and clarifications
- **Structured Output**: Produces well-formatted requirements documents ready for development teams
- **User-Friendly Interface**: Provides clear, conversational interactions with minimal technical jargon
- **Complete Coverage**: Ensures no critical requirements are missed through systematic questioning

## Architecture

The agent consists of:
- **Python Application**: Interactive console application for local use
- **Strands Framework**: Agent orchestration with user interaction tools
- **Amazon Bedrock**: AI model for intelligent conversation management (Nova Pro)
- **Handoff Tool**: Enables interactive user communication and question flow

## Prerequisites

- Python 3.13 or later
- AWS CLI configured with appropriate permissions
- Access to Amazon Bedrock (Nova Pro model)

## Installation

### 1. Install dependencies

```bash
cd src/
pip install -r requirements.txt
```

### 2. Configure AWS credentials

Ensure your AWS credentials are configured for Bedrock access:

```bash
aws configure
```

## Usage

### Interactive Mode

Run the agent locally for interactive requirements gathering:

```bash
python src/main.py
```

The agent will:
1. Ask for your initial API description
2. Conduct a structured interview to gather detailed requirements
3. Ask follow-up questions based on your responses
4. Generate a comprehensive requirements document

### Example Session

```
Starting local invocation of API Requirements Gatherer Agent...
Please provide your API request as input:
Enter your API requirements: I need an e-commerce API for my online store

Thinking...

I'll help you gather the detailed requirements for your e-commerce API. Let me ask you some questions to understand your needs better.

Could you describe your e-commerce use case in more detail? For example:
- What types of products will you be selling?
- What are the main features you need (product catalog, shopping cart, order management, etc.)?
- Who will be using this API (web applications, mobile apps, third-party integrations)?
```

## Requirements Categories

The agent systematically gathers information about:

### Core API Details
- **Use Case Description**: Detailed business requirements and functionality
- **Programming Language**: Preferred language for Lambda functions or code examples
- **API Endpoint Type**: Public or private API configuration

### Integration & Architecture
- **Integration Targets**:
  - Existing public HTTP resources
  - Lambda functions (new or existing)
  - Other AWS services
  - Private VPC resources
- **VPC Configuration**: VPC IDs, subnet IDs for private APIs
- **Load Balancer Details**: ARNs and DNS names for VPC Link configuration

### Security & Authentication
- **Identity Providers**:
  - None (public API)
  - AWS IAM
  - Amazon Cognito (new or existing user pools)
  - Third-party OIDC/OAuth providers
  - Custom authentication
- **Rate Limiting**: Usage quotas and throttling requirements
- **CORS Configuration**: Cross-origin resource sharing settings

### Development & Deployment
- **CI/CD Tools**: Preferred deployment and automation tools
- **Business Logic**: Whether to include sample business logic in generated code
- **Function ARNs**: Existing Lambda function details if applicable

## Output Format

The agent produces structured requirements in this format:

```xml
<request>Original user request</request>
<requirements>
- Detailed requirement 1
- Detailed requirement 2
- Integration specifications
- Security configurations
- Deployment preferences
</requirements>
```

## Configuration

### Environment Variables

- `BEDROCK_MODEL`: Bedrock model ID (default: `amazon.nova-pro-v1:0`)
- `STRANDS_TOOL_CONSOLE_MODE`: Set to `enabled` for interactive console mode

### Dependencies

- `strands-agents`: Core agent framework
- `strands-agents-tools`: User interaction tools including handoff functionality

## Advanced Features

### Intelligent Follow-up Questions
The agent asks contextual follow-up questions based on previous answers:
- Private API → VPC and subnet configuration
- Cognito authentication → User pool preferences
- VPC integration → Load balancer details
- Lambda functions → New vs existing function preferences

### Conversation Flow Management
The agent uses a sophisticated callback handler to:
- Filter out internal "thinking" processes
- Provide clean, user-friendly output
- Maintain conversation context and flow
- Handle interruptions gracefully

### Comprehensive Coverage
Ensures all critical aspects are covered:
- Security considerations (explicitly avoids API keys for auth)
- Network architecture (public vs private)
- Integration patterns (HTTP, Lambda, AWS services)
- Development workflow (CI/CD, testing)

## Local Development

The agent is designed primarily for local interactive use:

```bash
python src/main.py
```

Features:
- **Interactive Console**: Real-time conversation with the AI agent
- **Graceful Interruption**: Handle Ctrl+C cleanly
- **Verbose Logging**: Detailed execution information for debugging
- **Error Handling**: Comprehensive error reporting and recovery

