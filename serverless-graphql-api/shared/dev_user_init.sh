# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Creates regular and administrative user accounts in Cognito, confirms and authenticates new accounts.
# pass development Cognito shared stack name as a command line parameter

#!/bin/bash
# Development environment initialization.

# Getting output values from CloudFormation stacks ...
# Getting Cognito configuration ...
cognitoStackOutputs=$(aws cloudformation describe-stacks --stack-name $1 | jq -r '.Stacks[0].Outputs')
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
echo Regular user name: $regularUserName
echo Regular user password: $regularUserPassword
echo Regular user ID: $regularUserSub
echo Regular user ID token: 
echo $regularUserIdToken
echo Regular user access token: 
echo $regularUserAccessToken
echo Regular user refresh token:
echo $regularUserRefreshToken
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
echo Admin user name: $adminUserName
echo Admin user password: $adminUserPassword
echo Admin user ID: $adminUserSub
echo Admin user ID token: 
echo $adminUserIdToken
echo Admin user access token: 
echo $adminUserAccessToken
echo Admin user refresh token:
echo $adminUserRefreshToken
# Administrative user account for testing created.

# Testing environment initialization completed.
