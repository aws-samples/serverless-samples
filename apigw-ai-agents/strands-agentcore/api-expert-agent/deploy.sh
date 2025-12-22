# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

#!/bin/bash

# Strands AgentCore Deployment Script
# Deploys agent using Amazon Bedrock AgentCore Runtime with direct code deployment

set -e

# Configuration
AGENT_NAME="${AGENT_NAME:-api-expert-agent}"
ENTRYPOINT="${ENTRYPOINT:-src/main.py}"
PYTHON_RUNTIME="${PYTHON_RUNTIME:-PYTHON_3_12}"
REQUIREMENTS_FILE="${REQUIREMENTS_FILE:-src/requirements.txt}"
AWS_REGION="${AWS_REGION:-us-west-2}"
BEDROCK_MODEL="${BEDROCK_MODEL:-amazon.nova-pro-v1:0}"
KB_ID="${KB_ID:-}"  # Optional Knowledge Base ID

echo "=========================================="
echo "  Strands AgentCore Deployment"
echo "=========================================="
echo ""
echo "Agent: $AGENT_NAME"
echo "Region: $AWS_REGION"
if [ -n "$KB_ID" ]; then
    echo "Knowledge Base: $KB_ID"
fi
echo ""

# Check if agentcore CLI is installed
if ! command -v agentcore &> /dev/null; then
    echo "Error: AgentCore CLI not found"
    echo "Install with: pip install bedrock-agentcore-starter-toolkit"
    exit 1
fi

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
POLICY_NAME="${AGENT_NAME}-execution-policy"

# Step 1: Create IAM policy for agent permissions
echo "Step 1: Creating IAM execution policy..."

# Build policy document
POLICY_DOC=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockModelAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "arn:aws:bedrock:${AWS_REGION}::foundation-model/*"
    },
    {
      "Sid": "APIGatewayReadAccess",
      "Effect": "Allow",
      "Action": [
        "apigateway:GET"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ServiceQuotasReadAccess",
      "Effect": "Allow",
      "Action": [
        "servicequotas:ListServiceQuotas"
      ],
      "Resource": "*"
    },
    {
      "Sid": "WAFReadAccess",
      "Effect": "Allow",
      "Action": [
        "wafv2:GetWebACLForResource"
      ],
      "Resource": "*"
    }
EOF
)

# Add Knowledge Base permissions if KB_ID is set
if [ -n "$KB_ID" ]; then
    POLICY_DOC="${POLICY_DOC},
    {
      \"Sid\": \"KnowledgeBaseAccess\",
      \"Effect\": \"Allow\",
      \"Action\": [
        \"bedrock:Retrieve\",
        \"bedrock:RetrieveAndGenerate\"
      ],
      \"Resource\": \"arn:aws:bedrock:${AWS_REGION}:${ACCOUNT_ID}:knowledge-base/${KB_ID}\"
    }"
fi

POLICY_DOC="${POLICY_DOC}
  ]
}"

# Create or update the policy
POLICY_ARN="arn:aws:iam::${ACCOUNT_ID}:policy/${POLICY_NAME}"

if aws iam get-policy --policy-arn "$POLICY_ARN" &> /dev/null; then
    echo "Policy exists, creating new version..."
    # Delete old versions if at limit (max 5 versions)
    VERSIONS=$(aws iam list-policy-versions --policy-arn "$POLICY_ARN" --query 'Versions[?IsDefaultVersion==`false`].VersionId' --output text)
    for VERSION in $VERSIONS; do
        aws iam delete-policy-version --policy-arn "$POLICY_ARN" --version-id "$VERSION" 2>/dev/null || true
    done
    aws iam create-policy-version --policy-arn "$POLICY_ARN" --policy-document "$POLICY_DOC" --set-as-default > /dev/null
else
    echo "Creating new policy..."
    aws iam create-policy --policy-name "$POLICY_NAME" --policy-document "$POLICY_DOC" > /dev/null
fi

echo "✓ IAM policy created: $POLICY_ARN"
echo ""

# Step 2: Configure agent
echo "Step 2: Configuring agent..."
agentcore configure \
  --entrypoint "$ENTRYPOINT" \
  --name "$AGENT_NAME" \
  --runtime "$PYTHON_RUNTIME" \
  --requirements-file "$REQUIREMENTS_FILE" \
  --deployment-type direct_code_deploy \
  --region "$AWS_REGION" \
  --non-interactive

echo ""
echo "✓ Configuration saved to .bedrock_agentcore.yaml"
echo ""

# Step 3: Deploy to AWS
echo "Step 3: Deploying to AWS..."

# Build deploy command with environment variables
DEPLOY_CMD="agentcore deploy --agent $AGENT_NAME --auto-update-on-conflict"
DEPLOY_CMD="$DEPLOY_CMD --env BEDROCK_MODEL=$BEDROCK_MODEL"
DEPLOY_CMD="$DEPLOY_CMD --env AWS_REGION=$AWS_REGION"

echo "Setting AWS_REGION=$AWS_REGION"

if [ -n "$KB_ID" ]; then
    DEPLOY_CMD="$DEPLOY_CMD --env KNOWLEDGE_BASE_ID=$KB_ID"
    echo "Setting KNOWLEDGE_BASE_ID=$KB_ID"
fi

eval "$DEPLOY_CMD"

echo ""
echo "✓ Agent deployed successfully"
echo ""

# Step 4: Attach policy to agent execution role
echo "Step 4: Attaching execution policy to agent role..."

# Wait a moment for the config file to be written
sleep 2

# Get the agent's execution role from the config (filter out null values)
EXECUTION_ROLE=$(grep "execution_role:" .bedrock_agentcore.yaml | grep -v "null" | head -1 | awk '{print $2}' | tr -d '"')

if [ -n "$EXECUTION_ROLE" ] && [ "$EXECUTION_ROLE" != "null" ]; then
    # Extract role name from ARN (format: arn:aws:iam::account:role/RoleName)
    ROLE_NAME=$(echo "$EXECUTION_ROLE" | sed 's/.*role\///')
    echo "Attaching policy to role: $ROLE_NAME"
    
    # Check if policy is already attached
    if aws iam list-attached-role-policies --role-name "$ROLE_NAME" --query "AttachedPolicies[?PolicyArn=='$POLICY_ARN'].PolicyArn" --output text 2>/dev/null | grep -q "$POLICY_ARN"; then
        echo "✓ Policy already attached to role"
    else
        aws iam attach-role-policy --role-name "$ROLE_NAME" --policy-arn "$POLICY_ARN"
        echo "✓ Policy attached to execution role"
    fi
else
    echo "⚠ Could not find execution role in config. You may need to attach the policy manually."
fi
echo ""

# Step 5: Check status
echo "Step 5: Checking status..."
agentcore status --agent "$AGENT_NAME"

echo ""
echo "=========================================="
echo "  Deployment Complete!"
echo "=========================================="
echo ""
echo "IAM Policy: $POLICY_ARN"
echo ""
echo "Test your agent:"
echo "  agentcore invoke '{\"prompt\": \"What are the best practices for API Gateway?\"}' --agent $AGENT_NAME"
echo ""
echo "Check status:"
echo "  agentcore status --agent $AGENT_NAME"
echo ""
echo "Destroy agent:"
echo "  agentcore destroy --agent $AGENT_NAME"
echo ""
