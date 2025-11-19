# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

#!/bin/bash

# FastAPI Docker Build and Push Script

set -e

# Configuration
REGION="us-west-1"
IMAGE_TAG="latest"
ECR_REPO_NAME="fastapi-streaming-python-ecs"

echo "Starting Docker build and push process..."

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
ECR_REPO_URI="${ECR_URI}/${ECR_REPO_NAME}"

echo "Step 1: Verifying ECR repository exists..."

# Check if ECR repository exists
if ! aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $REGION >/dev/null 2>&1; then
    echo "Error: ECR repository '$ECR_REPO_NAME' does not exist."
    echo "Please create the ECR repository first by following the setup instructions in README.md"
    exit 1
else
    echo "ECR repository $ECR_REPO_NAME found"
fi

echo "Step 2: Building and pushing Docker image..."

# Login to ECR
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI

# Build image for x86_64 architecture (ECS Fargate default)
echo "Building Docker image for x86_64 architecture..."
docker build --platform linux/amd64 -t $ECR_REPO_NAME .

# Tag image
docker tag $ECR_REPO_NAME:latest $ECR_REPO_URI:$IMAGE_TAG

# Push image
echo "Pushing image to ECR..."
docker push $ECR_REPO_URI:$IMAGE_TAG

echo "Build and push completed successfully!"
echo "ECR Repository: $ECR_REPO_URI"