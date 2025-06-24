# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

#!/bin/bash

# Get application outputs necessary
applicationStackOutputs=$(aws cloudformation describe-stacks --stack-name $TEST_APPLICATION_STACK_NAME | jq -r '.Stacks[0].Outputs')
locationsTable=$(echo "$applicationStackOutputs" | jq -r '.[] | select(.OutputKey == "LocationsTable") | .OutputValue')
resourcesTable=$(echo "$applicationStackOutputs" | jq -r '.[] | select(.OutputKey == "ResourcesTable") | .OutputValue')
bookingsTable=$(echo "$applicationStackOutputs" | jq -r '.[] | select(.OutputKey == "BookingsTable") | .OutputValue')

# Get Cognito outputs necessary
cognitoStackOutputs=$(aws cloudformation describe-stacks --stack-name $TEST_COGNITO_STACK_NAME | jq -r '.Stacks[0].Outputs')
userPool=$(echo "$cognitoStackOutputs" | jq -r '.[] | select(.OutputKey == "UserPool") | .OutputValue')

# Delete regular Cognito user
aws cognito-idp admin-delete-user --user-pool-id $userPool --username $REGULAR_USER_NAME 

# Delete admin user
aws cognito-idp admin-delete-user --user-pool-id $userPool --username $ADMIN_USER_NAME 

# Purge DynamoDB tables
# Based on https://stackoverflow.com/a/51663200
aws dynamodb scan \
  --attributes-to-get "locationid" \
  --table-name $locationsTable --query "Items[*]" \
  | jq --compact-output '.[]' \
  | tr '\n' '\0' \
  | xargs -0 -t -I keyItem \
    aws dynamodb delete-item --table-name $locationsTable --key=keyItem
aws dynamodb scan \
  --attributes-to-get "resourceid" \
  --table-name $resourcesTable --query "Items[*]" \
  | jq --compact-output '.[]' \
  | tr '\n' '\0' \
  | xargs -0 -t -I keyItem \
    aws dynamodb delete-item --table-name $resourcesTable --key=keyItem
aws dynamodb scan \
  --attributes-to-get "bookingid" \
  --table-name $bookingsTable --query "Items[*]" \
  | jq --compact-output '.[]' \
  | tr '\n' '\0' \
  | xargs -0 -t -I keyItem \
    aws dynamodb delete-item --table-name $bookingsTable --key=keyItem
