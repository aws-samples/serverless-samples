# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

#!/bin/bash

set -e

# Configuration
export $(grep -v '^#' .agentcore_identity_user.env | xargs)
export $(grep -v '^#' .env | xargs)

echo "=========================================="
echo "  Strands AgentCore Deployment"
echo "=========================================="
echo ""
echo "Agent: $AGENT_NAME"
echo "Region: $AWS_REGION"
echo ""

# Check if agentcore CLI is installed
if ! command -v agentcore &> /dev/null; then
    echo "Error: AgentCore CLI not found"
    echo "Install with: pip install bedrock-agentcore-starter-toolkit"
    exit 1
fi

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ACCOUNT_ID

# # Save ACCOUNT_ID to .env if not already present
# if ! grep -q "^ACCOUNT_ID=" .env; then
#     echo "ACCOUNT_ID=\"$ACCOUNT_ID\"" >> .env
# else
#     sed -i.bak "s|^export ACCOUNT_ID=.*|export ACCOUNT_ID=\"$ACCOUNT_ID\"|" .env && rm .env.bak
# fi

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
    }
    ]
}
EOF
)

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

echo "IAM policy created: $POLICY_ARN"

# Step 2: Configure agent
echo "Step 2: Configuring agent..."
agentcore configure \
  --entrypoint "$ENTRYPOINT" \
  --name "$AGENT_NAME" \
  --runtime "$PYTHON_RUNTIME" \
  --requirements-file "$REQUIREMENTS_FILE" \
  --deployment-type direct_code_deploy \
  --region "$AWS_REGION" \
  --non-interactive \
    --disable-memory \
  --authorizer-config '{
    "customJWTAuthorizer": {
      "discoveryUrl": "'$RUNTIME_DISCOVERY_URL'",
      "allowedClients": ["'$RUNTIME_CLIENT_ID'"]
    }
  }' 

echo "Configuration saved to .bedrock_agentcore.yaml"

# Step 3: Deploy to AWS
echo "Step 3: Deploying to AWS..."

agentcore deploy --agent $AGENT_NAME --auto-update-on-conflict

echo "Agent deployed successfully"

# Extract Agent ID from config
echo "Extracting Agent ID from configuration..."
AGENT_ID=$(grep "agent_id:" .bedrock_agentcore.yaml | grep -v "null" | head -1 | awk '{print $2}' | tr -d '"')

# if [ -n "$AGENT_ID" ] && [ "$AGENT_ID" != "null" ]; then
#     echo "Agent ID: $AGENT_ID"
#     export AGENT_ID
#     # Append to .env file if not already present
#     if ! grep -q "^export AGENT_ID=" .env; then
#         echo "export AGENT_ID=\"$AGENT_ID\"" >> .env
#         echo "Agent ID added to .env file"
#     else
#         # Update existing entry
#         sed -i.bak "s|^export AGENT_ID=.*|export AGENT_ID=\"$AGENT_ID\"|" .env && rm .env.bak
#         echo "Agent ID updated in .env file"
#     fi
# else
#     echo "Warning: Could not extract Agent ID from .bedrock_agentcore.yaml"
# fi

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
        echo "Policy already attached to role"
    else
        aws iam attach-role-policy --role-name "$ROLE_NAME" --policy-arn "$POLICY_ARN"
        echo "Policy attached to execution role"
    fi
else
    echo "Could not find execution role in config. You may need to attach the policy manually."
fi

# Step 5: Create API Gateway from OpenAPI specification
echo "Step 5: Creating API Gateway endpoint..."

API_NAME="${AGENT_NAME}-api"

# Use envsubst with explicit variable list to avoid replacing $ref
export API_NAME AGENT_ID ACCOUNT_ID AWS_REGION
envsubst '$API_NAME $AGENT_ID $ACCOUNT_ID $AWS_REGION' < api-gateway-config.yaml.example > api-gateway-config.yaml

# Check if API already exists
EXISTING_API_ID=$(aws apigateway get-rest-apis --query "items[?name=='$API_NAME'].id" --output text --region "$AWS_REGION")

if [ -n "$EXISTING_API_ID" ]; then
    echo "API Gateway already exists with ID: $EXISTING_API_ID"
    echo "Updating API with new OpenAPI specification..."
    aws apigateway put-rest-api \
        --rest-api-id "$EXISTING_API_ID" \
        --mode overwrite \
        --body "fileb://api-gateway-config.yaml" \
        --region "$AWS_REGION" > /dev/null
    API_ID="$EXISTING_API_ID"
else
    echo "Creating new API Gateway..."
    API_ID=$(aws apigateway import-rest-api \
        --body "fileb://api-gateway-config.yaml" \
        --parameters endpointConfigurationTypes=REGIONAL \
        --region "$AWS_REGION" \
        --query 'id' \
        --output text)
fi

# Deploy the API to a stage
STAGE_NAME="prod"
echo "Deploying API to stage: $STAGE_NAME"
aws apigateway create-deployment \
    --rest-api-id "$API_ID" \
    --stage-name "$STAGE_NAME" \
    --region "$AWS_REGION" > /dev/null

API_ENDPOINT="https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/${STAGE_NAME}"

# Step 6: Check status
echo "Step 5: Checking status..."
agentcore status --agent "$AGENT_NAME"

echo ""
echo "=========================================="
echo "  Deployment Complete!"
echo "=========================================="
echo ""
echo "API Gateway ID: $API_ID"
echo ""
echo ""
echo "API Gateway Endpoint: $API_ENDPOINT/ask"
echo ""
