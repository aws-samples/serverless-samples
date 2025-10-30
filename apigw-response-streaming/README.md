# apigw-response-streaming

This repository contains example implementations of Amazon API Gateway response streaming using different architectures and technologies.

See Amazon API Gateway feature launch blog post.

## Overview

This repository demonstrates three different approaches to implementing streaming responses with API Gateway:

### 1. Node.js Lambda with Bedrock (`node-bedrock-lambda/`)

A serverless implementation using AWS Lambda and Amazon Bedrock that streams AI model responses in real-time.

**Architecture:**
- API Gateway → Lambda Function → Amazon Bedrock Nova Lite Model
- Streaming responses from Bedrock model through Lambda to client
- Serverless, pay-per-request pricing model

[View Node.js Lambda Implementation →](./node-bedrock-lambda/)

### 2. Python FastAPI on ECS (`python-strands-ecs/`)

A containerized implementation using FastAPI on Amazon ECS Fargate with Strands agents for AI responses.

**Architecture:**
- API Gateway → VPC Link → Network Load Balancer → ECS Fargate → FastAPI + Strands
- Secure private subnet deployment with public API access
- Container-based with auto-scaling capabilities

[View Python ECS Implementation →](./python-strands-ecs/)

### 3. Python FastAPI on Lambda (`python-strands-lambda/`)

A serverless implementation using AWS Lambda with FastAPI and Strands agents for AI responses. Lambda uses [AWS Lambda Web Adapter](https://github.com/awslabs/aws-lambda-web-adapter) for Python response streaming.

**Architecture:**
- API Gateway → Lambda Function → FastAPI + Strands
- Streaming responses from Bedrock model through Lambda and Strands agents to client
- Serverless, pay-per-request pricing model

[View Python Lambda Implementation →](./python-strands-lambda/)


## Prerequisites

Both implementations require:
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html) installed and configured
- [AWS SAM CLI](https://aws.amazon.com/serverless/sam/) for deployment
- Access to Amazon Bedrock models in your AWS account

## Deployment & Testing

For detailed deployment and testing instructions, please refer to the individual project directories:

- **Node.js Lambda**: See [`node-bedrock-lambda/README.md`](./node-bedrock-lambda/README.md)
- **Python ECS**: See [`python-strands-ecs/README.md`](./python-strands-ecs/README.md)
- **Python Lambda**: See [`python-strands-lambda/README.md`](./python-strands-lambda/README.md)