# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

#!/bin/bash
# Starting testing environment initialization.

# Getting output values from CloudFormation stacks ...
applicationStackOutputs=$(aws cloudformation describe-stacks --stack-name $TEST_APPLICATION_STACK_NAME | jq -r '.Stacks[0].Outputs')
apiEndpoint=$(echo "$applicationStackOutputs" | jq -r '.[] | select(.OutputKey == "APIEndpoint") | .OutputValue')
locationsTable=$(echo "$applicationStackOutputs" | jq -r '.[] | select(.OutputKey == "LocationsTable") | .OutputValue')
resourcesTable=$(echo "$applicationStackOutputs" | jq -r '.[] | select(.OutputKey == "ResourcesTable") | .OutputValue')
bookingsTable=$(echo "$applicationStackOutputs" | jq -r '.[] | select(.OutputKey == "BookingsTable") | .OutputValue')
echo export API_ENDPOINT="$apiEndpoint"

# Getting Cognito configuration ...
cognitoStackOutputs=$(aws cloudformation describe-stacks --stack-name $TEST_COGNITO_STACK_NAME | jq -r '.Stacks[0].Outputs')
userPool=$(echo "$cognitoStackOutputs" | jq -r '.[] | select(.OutputKey == "UserPool") | .OutputValue')
applicationClient=$(echo "$cognitoStackOutputs" | jq -r '.[] | select(.OutputKey == "UserPoolClient") | .OutputValue')
adminGroupName=$(echo "$cognitoStackOutputs" | jq -r '.[] | select(.OutputKey == "UserPoolAdminGroupName") | .OutputValue')

# Creating regular user account for testing ...
regularUserName="regularUser@example.com"
# --- Generating random password ...
regularUserPassword=$(aws secretsmanager get-random-password --require-each-included-type --exclude-characters "\"\'\`[]{}():;,$/\\<>|=&" | jq -r '.RandomPassword')
# --- Deleting user if it already exists ...
result=$(aws cognito-idp admin-delete-user --user-pool-id $userPool --username "$regularUserName")
# --- Creating new user ...
regularUserSub=$(aws cognito-idp sign-up --client-id $applicationClient --username "$regularUserName" --password "$regularUserPassword" --user-attributes Name="name",Value="$regularUserName" | jq -r '.UserSub')
# --- Confirming new user ...
result=$(aws cognito-idp admin-confirm-sign-up --user-pool-id $userPool --username "$regularUserName")
# --- Getting new user authentication ...
regularUserAuthOutputs=$(aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH --client-id $applicationClient --auth-parameters USERNAME="$regularUserName",PASSWORD="$regularUserPassword" | jq -r '.AuthenticationResult')
regularUserIdToken=$(echo "$regularUserAuthOutputs" | jq -r '.IdToken')
regularUserAccessToken=$(echo "$regularUserAuthOutputs" | jq -r '.AccessToken')
regularUserRefreshToken=$(echo "$regularUserAuthOutputs" | jq -r '.RefreshToken')
# --- Export to environmental variables for the test scripts to consume
echo export REGULAR_USER_NAME="$regularUserName"
echo export REGULAR_USER_PASSWORD="$regularUserPassword"
echo export REGULAR_USER_SUB="$regularUserSub"
echo export REGULAR_USER_ID_TOKEN="$regularUserIdToken"
echo export REGULAR_USER_ACCESS_TOKEN="$regularUserAccessToken"
echo export REGULAR_USER_REFRESH_TOKEN="$regularUserRefreshToken"
# Regular user account for testing created.

# Create admin user and add to admin group, authenticate and set environment variables for testing
# Creating administrative user account for testing ...
adminUserName="adminUser@example.com"
# --- Generating random password ...
adminUserPassword=$(aws secretsmanager get-random-password --require-each-included-type --exclude-characters "\"\'\`[]{}():;,$/\\<>|=&" | jq -r '.RandomPassword')
# --- Deleting user if it already exists ...
result=$(aws cognito-idp admin-delete-user --user-pool-id $userPool --username "$adminUserName")
# --- Creating new user ...
adminUserSub=$(aws cognito-idp sign-up --client-id $applicationClient --username "$adminUserName" --password "$adminUserPassword" --user-attributes Name="name",Value="$adminUserName" | jq -r '.UserSub')
# --- Confirming new user ...
result=$(aws cognito-idp admin-confirm-sign-up --user-pool-id $userPool --username "$adminUserName")
# --- Adding new user to the administrators group...
result=$(aws cognito-idp admin-add-user-to-group --user-pool-id $userPool --username "$adminUserName" --group-name $adminGroupName)
# --- Getting new user authentication ...
adminUserAuthOutputs=$(aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH --client-id $applicationClient --auth-parameters USERNAME="$adminUserName",PASSWORD="$adminUserPassword" | jq -r '.AuthenticationResult')
adminUserIdToken=$(echo "$adminUserAuthOutputs" | jq -r '.IdToken')
adminUserAccessToken=$(echo "$adminUserAuthOutputs" | jq -r '.AccessToken')
adminUserRefreshToken=$(echo "$adminUserAuthOutputs" | jq -r '.RefreshToken')
# --- Export to environmental variables for the test scripts to consume
echo export ADMIN_USER_NAME="$adminUserName"
echo export ADMIN_USER_PASSWORD="$adminUserPassword"
echo export ADMIN_USER_SUB="$adminUserSub"
echo export ADMIN_USER_ID_TOKEN="$adminUserIdToken"
echo export ADMIN_USER_ACCESS_TOKEN="$adminUserAccessToken"
echo export ADMIN_USER_REFRESH_TOKEN="$adminUserRefreshToken"
# Administrative user account for testing created.

# Based on https://stackoverflow.com/a/51663200
# Purging data from dynamoDB tables used for testing ...
# --- Processing $locationsTable
result=$(aws dynamodb scan \
  --attributes-to-get "locationid" \
  --table-name $locationsTable --query "Items[*]" \
  | jq --compact-output '.[]' \
  | tr '\n' '\0' \
  | xargs -0 -t -I keyItem \
    aws dynamodb delete-item --table-name $locationsTable --key=keyItem)
# --- Processing $resourcesTable
result=$(aws dynamodb scan \
  --attributes-to-get "resourceid" \
  --table-name $resourcesTable --query "Items[*]" \
  | jq --compact-output '.[]' \
  | tr '\n' '\0' \
  | xargs -0 -t -I keyItem \
    aws dynamodb delete-item --table-name $resourcesTable --key=keyItem)
# --- Processing $bookingsTable
result=$(aws dynamodb scan \
  --attributes-to-get "bookingid" \
  --table-name $bookingsTable --query "Items[*]" \
  | jq --compact-output '.[]' \
  | tr '\n' '\0' \
  | xargs -0 -t -I keyItem \
    aws dynamodb delete-item --table-name $bookingsTable --key=keyItem)

# Testing environment initialization completed.
