# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import os
import pytest
import time

COGNITO_STACK_NAME = os.getenv('TF_VAR_cognito_stack_name', None)
globalConfig = {}


def get_stack_outputs(stack_name):
    result = {}
    cf_client = boto3.client('cloudformation')
    cf_response = cf_client.describe_stacks(StackName=stack_name)
    outputs = cf_response["Stacks"][0]["Outputs"]
    for output in outputs:
        result[output["OutputKey"]] = output["OutputValue"]
    return result

def get_tf_outputs():
    result = {}
    for key, value in os.environ.items():
        if key.startswith("TF_OUTPUT_"):
            output_key = key[10:]  # Remove the "TF_OUTPUT_" prefix
            result[output_key] = value
    return result

def create_cognito_accounts():
    result = {}
    sm_client = boto3.client('secretsmanager')
    idp_client = boto3.client('cognito-idp')
    # create regular user account
    sm_response = sm_client.get_random_password(ExcludeCharacters='"''`[]{}():;,$/\\<>|=&',
                                                RequireEachIncludedType=True)
    result["regularUserName"] = "regularUser@example.com"
    result["regularUserPassword"] = sm_response["RandomPassword"]
    try:
        idp_client.admin_delete_user(UserPoolId=globalConfig["UserPool"],
                                     Username=result["regularUserName"])
    except idp_client.exceptions.UserNotFoundException:
        print('Regular user haven''t been created previously')
    idp_response = idp_client.sign_up(
        ClientId=globalConfig["UserPoolClient"],
        Username=result["regularUserName"],
        Password=result["regularUserPassword"],
        UserAttributes=[{"Name": "name", "Value": result["regularUserName"]}]
    )
    result["regularUserSub"] = idp_response["UserSub"]
    idp_client.admin_confirm_sign_up(UserPoolId=globalConfig["UserPool"],
                                     Username=result["regularUserName"])
    # get new user authentication info
    idp_response = idp_client.initiate_auth(
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': result["regularUserName"],
            'PASSWORD': result["regularUserPassword"]
        },
        ClientId=globalConfig["UserPoolClient"],
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
        idp_client.admin_delete_user(UserPoolId=globalConfig["UserPool"],
                                     Username=result["adminUserName"])
    except idp_client.exceptions.UserNotFoundException:
        print('Regular user haven''t been created previously')
    idp_response = idp_client.sign_up(
        ClientId=globalConfig["UserPoolClient"],
        Username=result["adminUserName"],
        Password=result["adminUserPassword"],
        UserAttributes=[{"Name": "name", "Value": result["adminUserName"]}]
    )
    result["adminUserSub"] = idp_response["UserSub"]
    idp_client.admin_confirm_sign_up(UserPoolId=globalConfig["UserPool"],
                                     Username=result["adminUserName"])
    # add administrative user to the admins group
    idp_client.admin_add_user_to_group(UserPoolId=globalConfig["UserPool"],
                                       Username=result["adminUserName"],
                                       GroupName=globalConfig["UserPoolAdminGroupName"])
    # get new admin user authentication info
    idp_response = idp_client.initiate_auth(
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': result["adminUserName"],
            'PASSWORD': result["adminUserPassword"]
        },
        ClientId=globalConfig["UserPoolClient"],
    )
    result["adminUserIdToken"] = idp_response["AuthenticationResult"]["IdToken"]
    result["adminUserAccessToken"] = idp_response["AuthenticationResult"]["AccessToken"]
    result["adminUserRefreshToken"] = idp_response["AuthenticationResult"]["RefreshToken"]
    return result


def create_api_key():
    result = {}
    apigw_client = boto3.client('apigateway')
    # delete any pre-existing API key used for integration testing
    existing_keys = apigw_client.get_api_keys(
        nameQuery='Integration Testing API Key',
        includeValues=False
    )
    for key in existing_keys["items"]:
        response = apigw_client.delete_api_key(
            apiKey=key["id"]
        )
    # create new API key for integration testing and associate it with enterprise usage plan
    response = apigw_client.create_api_key(
        name='Integration Testing API Key',
        enabled=True
    )
    api_key_id = response["id"]
    api_key_value = response["value"]
    response = apigw_client.create_usage_plan_key(
        usagePlanId=globalConfig['api_enterprise_usage_plan'],
        keyId=api_key_id,
        keyType='API_KEY'
    )
    result["enterpriseUsagePlanApiKeyValue"] = api_key_value
    # wait for API key to be propagated 
    time.sleep(120)
    return result


def clear_dynamo_tables():
    # clear all data from the tables that will be used for testing
    dbd_client = boto3.client('dynamodb')
    db_response = dbd_client.scan(
        TableName=globalConfig['locations_table'],
        AttributesToGet=['locationid']
    )
    for item in db_response["Items"]:
        dbd_client.delete_item(
            TableName=globalConfig['locations_table'],
            Key={'locationid': {'S': item['locationid']["S"]}}
        )
    db_response = dbd_client.scan(
        TableName=globalConfig['resources_table'],
        AttributesToGet=['resourceid']
    )
    for item in db_response["Items"]:
        dbd_client.delete_item(
            TableName=globalConfig['resources_table'],
            Key={'resourceid': {'S': item['resourceid']["S"]}}
        )
    db_response = dbd_client.scan(
        TableName=globalConfig['bookings_table'],
        AttributesToGet=['bookingid']
    )
    for item in db_response["Items"]:
        dbd_client.delete_item(
            TableName=globalConfig['bookings_table'],
            Key={'bookingid': {'S': item['bookingid']["S"]}}
        )
    return


@pytest.fixture(scope='session')
def global_config(request):
    global globalConfig
    # load outputs of the stacks to test
    globalConfig.update(get_stack_outputs(COGNITO_STACK_NAME))
    globalConfig.update(get_tf_outputs())
    globalConfig.update(create_cognito_accounts())
    globalConfig.update(create_api_key())
    clear_dynamo_tables()
    return globalConfig
