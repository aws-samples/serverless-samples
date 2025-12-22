# API Inspector - Event-Driven Architecture

This project implements an automated API inspection system using Amazon Bedrock AgentCore and AWS Lambda in an event-driven architecture. The system automatically analyzes Amazon API Gateway deployments and provides improvement recommendations.

## Architecture Overview

![EDA architecture](../assets/eda_diagram.png)

The solution consists of:

1. **Event-Driven Lambda Function**: Triggered by EventBridge when API Gateway deployments or stage updates occur
2. **AgentCore Runtime Integration**: Analyzes API configurations and provides recommendations
3. **Serverless Architecture**: Deployed using AWS SAM (Serverless Application Model)

## How It Works

1. When an API Gateway deployment or stage update occurs, EventBridge captures the event
2. The Lambda function extracts the API ID from the event
3. The function invokes an AgentCore agent with the API ID
4. The AgentCore agent analyzes the API configuration and returns improvement recommendations
5. Results are sent to the owner of the API using Amazon SES

## Prerequisites

- AWS CLI installed and configured
- AWS SAM CLI installed
- Python 3.13
- An existing AgentCore agent deployment with the API Inspector agent
- Amazon SES with verified address or domain

## Setup Instructions

### 1. Deploy the AgentCore Agent

Before deploying this component, ensure you have deployed the API Inspector Agent to AgentCore runtime. Note the Agent ID as it will be needed for this deployment.

### 2. Build and Deploy

```bash
# Build the application
sam build

# Deploy the application with interactive parameter configuration
sam deploy --guided
```

During the guided deployment, you'll be prompted to provide the following parameters:

- `AgentCoreAgentId`: The AgentCore Agent ID for the API Inspector agent
- `AgentCoreRegion`: AWS region where the AgentCore agent is deployed (default: us-east-1)
- `SesEmailForNotifications`: Email "From" address to be used in SES for sending recommendations to the owner

Follow the prompts to complete the deployment process.


