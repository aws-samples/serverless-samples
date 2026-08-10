# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

#!/bin/bash

export $(grep -v '^#' .env | xargs)

# Based on https://aws.github.io/bedrock-agentcore-starter-toolkit/api-reference/cli.html#oauth-identity-setup-workflow

# 1. Create Cognito pools
agentcore identity setup-cognito --region $AWS_REGION

export $(grep -v '^#' .agentcore_identity_user.env | xargs)

# 2. Create credential provider
agentcore identity create-credential-provider \
  --name $AGENT_NAME \
  --type cognito \
  --client-id $IDENTITY_CLIENT_ID \
  --client-secret $IDENTITY_CLIENT_SECRET \
  --discovery-url $IDENTITY_DISCOVERY_URL \
  --cognito-pool-id $IDENTITY_POOL_ID \
  --region $AWS_REGION

# 3. Create workload identity
agentcore identity create-workload-identity \
  --name $AGENT_NAME \
  --region $AWS_REGION


