# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import os
import pytest

APPLICATION_STACK_NAME = os.getenv('TEST_APPLICATION_STACK_NAME', 'cdk-pipeline-int-test-apigw')
globalConfig = {}


def get_stack_outputs(stack_name):
    result = {}
    cf_client = boto3.client('cloudformation')
    cf_response = cf_client.describe_stacks(StackName=stack_name)
    outputs = cf_response["Stacks"][0]["Outputs"]
    for output in outputs:
        result[output["OutputKey"]] = output["OutputValue"]
    return result


def create_cognito_accounts(cognito_stack_name):
    result = {}
    cognito_config_prefix = cognito_stack_name.replace('-', '')
    sm_client = boto3.client('secretsmanager')
    idp_client = boto3.client('cognito-idp')
    # create regular user account
    sm_response = sm_client.get_random_password(ExcludeCharacters='"''`[]{}():;,$/\\<>|=&',
                                                RequireEachIncludedType=True)
    result["regularUserName"] = "regularUser@example.com"
    result["regularUserPassword"] = sm_response["RandomPassword"]
    try:
        idp_client.admin_delete_user(UserPoolId=globalConfig[cognito_config_prefix+"UserPool"],
                                     Username=result["regularUserName"])
    except idp_client.exceptions.UserNotFoundException:
        print('Regular user haven''t been created previously')
    idp_response = idp_client.sign_up(
        ClientId=globalConfig[cognito_config_prefix+"UserPoolClient"],
        Username=result["regularUserName"],
        Password=result["regularUserPassword"],
        UserAttributes=[{"Name": "name", "Value": result["regularUserName"]}]
    )
    result["regularUserSub"] = idp_response["UserSub"]
    idp_client.admin_confirm_sign_up(UserPoolId=globalConfig[cognito_config_prefix+"UserPool"],
                                     Username=result["regularUserName"])
    # get new user authentication info
    idp_response = idp_client.initiate_auth(
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': result["regularUserName"],
            'PASSWORD': result["regularUserPassword"]
        },
        ClientId=globalConfig[cognito_config_prefix+"UserPoolClient"],
    )
    result["regularUserIdToken"] = idp_response["AuthenticationResult"]["IdToken"]
    result["regularUserAccessToken"] = idp_response["AuthenticationResult"]["AccessToken"]
    result["regularUserRefreshToken"] = idp_response["AuthenticationResult"]["RefreshToken"]
    # create administrative user account
    sm_response = sm_client.get_random_password(ExcludeCharacters='"''`[]{}():;,$/\\<>|=&',
                                                RequireEachIncludedType=True)
    result["adminUserName"] = "adminUser@example.com"
    result["adminUserPassword"] = sm_response["RandomPassword"]
    try:
        idp_client.admin_delete_user(UserPoolId=globalConfig[cognito_config_prefix+"UserPool"],
                                     Username=result["adminUserName"])
    except idp_client.exceptions.UserNotFoundException:
        print('Regular user haven''t been created previously')
    idp_response = idp_client.sign_up(
        ClientId=globalConfig[cognito_config_prefix+"UserPoolClient"],
        Username=result["adminUserName"],
        Password=result["adminUserPassword"],
        UserAttributes=[{"Name": "name", "Value": result["adminUserName"]}]
    )
    result["adminUserSub"] = idp_response["UserSub"]
    idp_client.admin_confirm_sign_up(UserPoolId=globalConfig[cognito_config_prefix+"UserPool"],
                                     Username=result["adminUserName"])
    # add administrative user to the admins group
    idp_client.admin_add_user_to_group(UserPoolId=globalConfig[cognito_config_prefix+"UserPool"],
                                       Username=result["adminUserName"],
                                       GroupName=globalConfig[cognito_config_prefix+"UserPoolAdminGroupName"])
    # get new admin user authentication info
    idp_response = idp_client.initiate_auth(
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': result["adminUserName"],
            'PASSWORD': result["adminUserPassword"]
        },
        ClientId=globalConfig[cognito_config_prefix+"UserPoolClient"],
    )
    result["adminUserIdToken"] = idp_response["AuthenticationResult"]["IdToken"]
    result["adminUserAccessToken"] = idp_response["AuthenticationResult"]["AccessToken"]
    result["adminUserRefreshToken"] = idp_response["AuthenticationResult"]["RefreshToken"]
    return result


def clear_dynamo_tables():
    # clear all data from the tables that will be used for testing
    dbd_client = boto3.client('dynamodb')
    return


@pytest.fixture(scope='session')
def global_config(request):
    global globalConfig
    # load outputs of the stacks to test
    print("int test starting....")
    print(APPLICATION_STACK_NAME)
    globalConfig.update(get_stack_outputs(APPLICATION_STACK_NAME))
    globalConfig.update(get_stack_outputs(globalConfig['ApiAuthCognitoStackName']))
    globalConfig.update(create_cognito_accounts(globalConfig['ApiAuthCognitoStackName']))
    clear_dynamo_tables()
    return globalConfig
