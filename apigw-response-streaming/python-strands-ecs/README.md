# FastAPI Response Streaming on ECS

This example shows how to run a FastAPI application with response streaming on Amazon ECS using Fargate.

## Architecture

- **ECS Fargate**: Serverless container platform running in private subnets
- **Network Load Balancer (Private)**: Routes traffic to ECS tasks within the VPC
- **API Gateway**: HTTP API with OpenAPI specification for public access
- **VPC Link**: Connects API Gateway to the private Network Load Balancer
- **VPC**: Custom VPC with public and private subnets across 2 AZs
- **NAT Gateways**: Provide outbound internet access for ECS tasks
- **ECR**: Container registry for Docker images
- **CloudWatch**: Logging and monitoring

## Features

- **Streaming AI Responses**: Real-time responses from AWS Bedrock Nova Lite model using Strands agents
- **Secure Architecture**: ECS service runs in private subnets, accessible only via API Gateway
- **Production Ready**: Includes health checks, CloudWatch logging, and proper IAM roles
- **Scalable**: ECS Fargate with auto-scaling capabilities
- **Public API**: REST API Gateway with OpenAPI specification for easy integration

## Setup

### 1. Create ECR Repository (One-time Setup)

Before deploying, you need to create an ECR repository to store your Docker images:

```bash
# Create ECR repository
aws ecr create-repository \
  --repository-name fastapi-streaming-python-ecs \
  --image-scanning-configuration scanOnPush=true \
  --region us-west-1

# Set lifecycle policy to keep only 10 recent images (optional but recommended)
aws ecr put-lifecycle-policy \
  --repository-name fastapi-streaming-python-ecs \
  --lifecycle-policy-text '{
    "rules": [
      {
        "rulePriority": 1,
        "description": "Keep last 10 images",
        "selection": {
          "tagStatus": "any",
          "countType": "imageCountMoreThan",
          "countNumber": 10
        },
        "action": {
          "type": "expire"
        }
      }
    ]
  }' \
  --region us-west-1
```

**Note**: Replace `us-west-1` with your preferred AWS region if different.

## Build and Deploy

### Prerequisites for Deployment

- AWS CLI configured with appropriate permissions
- Docker installed and running
- SAM CLI installed ([Installation Guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html))
- ECR repository created (see setup instructions below)

### Deployment Steps

#### 1. Build and Push Docker Image

```bash
# Run the build script to push image to ECR
./build.sh
```

The script will:
1. Verify ECR repository exists
2. Build Docker image for x86_64 architecture
3. Push the image to ECR

#### 2. Get AWS Account ID

```bash
# Get your AWS account ID for the next step
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
```

#### 3. Deploy with SAM

```bash
# Deploy the stack using SAM
sam deploy --template-file template.yaml \
  --stack-name fastapi-streaming-ecs \
  --parameter-overrides ContainerImage=${ACCOUNT_ID}.dkr.ecr.us-west-1.amazonaws.com/fastapi-streaming-python-ecs:latest \
  --capabilities CAPABILITY_IAM \
  --region us-west-1 \
  --resolve-s3 \
  --no-confirm-changeset
```

#### 4. Test the API

After deployment completes, you can test the streaming API:

```bash
# Get the API Gateway URL from CloudFormation outputs
API_URL=$(aws cloudformation describe-stacks \
  --stack-name fastapi-streaming-ecs \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
  --output text \
  --region us-west-1)

# Test the streaming endpoint
curl -X POST "${API_URL}/ask" \
  -H "Content-Type: application/json" \
  -d '{"request": "Tell me a short story about a robot"}' \
  --no-buffer

# Test with a simple question
curl -X POST "${API_URL}/ask" \
  -H "Content-Type: application/json" \
  -d '{"request": "What is 2+2?"}' \
  --no-buffer
```

**Example API URL**: `https://d1q5a7nic4.execute-api.us-west-1.amazonaws.com/prod/ask`

## Cleanup

To avoid ongoing AWS charges, clean up the resources when you're done:

### 1. Delete CloudFormation Stack

```bash
# Delete the main stack (this will remove ECS, VPC, and all associated resources)
aws cloudformation delete-stack \
  --stack-name fastapi-streaming-ecs \
  --region us-west-1

# Wait for stack deletion to complete (optional)
aws cloudformation wait stack-delete-complete \
  --stack-name fastapi-streaming-ecs \
  --region us-west-1
```

### 2. Delete ECR Repository and Images

```bash
# Delete all images in the repository
aws ecr batch-delete-image \
  --repository-name fastapi-streaming-python-ecs \
  --image-ids imageTag=latest \
  --region us-west-1

# Delete the ECR repository
aws ecr delete-repository \
  --repository-name fastapi-streaming-python-ecs \
  --force \
  --region us-west-1
```

### 3. Verify Cleanup

```bash
# Check that the stack is deleted
aws cloudformation describe-stacks \
  --stack-name fastapi-streaming-ecs \
  --region us-west-1
# Should return: "Stack with id fastapi-streaming-ecs does not exist"

# Check that ECR repository is deleted
aws ecr describe-repositories \
  --repository-names fastapi-streaming-python-ecs \
  --region us-west-1
# Should return: "RepositoryNotFoundException"
```

**Note**: Replace `us-west-1` with your AWS region if different. The CloudFormation stack deletion will automatically remove the VPC, subnets, NAT gateways, load balancer, ECS cluster, and all other resources created by the template.