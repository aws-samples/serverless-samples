# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import boto3
import json
import requests
import base64

README_BASE_URL = "https://dash.readme.com/api/v1/api-specification/"
PARAMETERS_PREFIX = os.getenv("PARAMETERS_PREFIX", None)
APIGW_SDK_CLIENT_NAME = os.getenv("APIGW_SDK_CLIENT_NAME", "apigateway")

# get configuration from AWS Systems Manager Parameter Store
parameters_client = boto3.client('ssm')
parameters = parameters_client.get_parameters_by_path(
    Path=PARAMETERS_PREFIX)['Parameters']
apigw_id = [data for data in parameters if data["Name"]
            == PARAMETERS_PREFIX+'APIGW-ID'][0]['Value']
apigw_stage = [data for data in parameters if data["Name"]
               == PARAMETERS_PREFIX+'APIGW-Stage'][0]['Value']
apigw_type = [data for data in parameters if data["Name"]
              == PARAMETERS_PREFIX+'APIGW-Type'][0]['Value']
rm_definition_id = [data for data in parameters if data["Name"]
                    == PARAMETERS_PREFIX+'RM-APIDefinitionID'][0]['Value']
rm_project_version = [data for data in parameters if data["Name"]
                      == PARAMETERS_PREFIX+'RM-ProjectVersion'][0]['Value']

# get secrets from AWS Secrets Manager
secrets_client = boto3.client('secretsmanager')
rm_api_key = secrets_client.get_secret_value(
    SecretId=PARAMETERS_PREFIX+'RM-APIKey')['SecretString']

# initialize Amazon API Gateway client 
apigw_client = boto3.client(APIGW_SDK_CLIENT_NAME)


def lambda_handler(event, context):
    # Chack what operation on the API had been performed and what actions need to be taken
    if event["detail"]["eventName"] in ["CreateDeployment", "UpdateStage"]:
        # Existing API updated, synchronize definition to ReadMe
        print("Update definition-"+event["detail"]["eventName"])
        update_readme_api_definition()

    if event["detail"]["eventName"] in ["DeleteStage", "DeleteApi", "DeleteRestApi"]:
        # API or stage deleted, delete definition from ReadMe
        print("Delete definition-"+event["detail"]["eventName"])
        # delete_readme_api_definition()

    return


def export_apigw_openapi_definition():
    # export OpenAPI definition. Use appropriate API call depending on API Gateway endpint type (REST/HTTP)
    api_definition = {}
    if apigw_type == "REST":
        api_definition = json.loads(apigw_client.get_export(
            restApiId=apigw_id, accepts='application/json', exportType='oas30', 
            parameters={'extensions': 'apigateway'}, #, 'extensions': 'apigateway', 'extensions': 'authorizers'}, 
            stageName = apigw_stage)['body'].read().decode('utf-8'))
    else:
        api_definition=json.loads(apigw_client.export_api(ApiId = apigw_id, IncludeExtensions = True,
                                    OutputType = 'JSON', Specification = 'OAS30', 
                                    StageName = apigw_stage)['body'].read().decode('utf-8'))

    # If override version is specified, update API definition metadata so it matches ReadMe project version
    if rm_project_version != "" and rm_project_version.upper() != "NONE":
        api_definition["info"]["version"]=rm_project_version

    return api_definition


def update_readme_api_definition():
    global rm_definition_id
    
    api_definition=export_apigw_openapi_definition()

    # upload OpenAPI definition
    url=README_BASE_URL
    auth=base64.b64encode(rm_api_key.encode("utf-8"))
    headers={
        "Accept": "application/json",
        "Authorization": "Basic "+auth.decode("utf-8")
    }
    # Check if API definition ID is specified and create new one if it is empty
    if rm_definition_id.upper() == "NONE":
        # ReadMe API definition does not exist, create new one
        headers["x-readme-version"]=rm_project_version
        response=requests.post(
            url, files={"spec": json.dumps(api_definition)}, headers=headers)
        # Update AWS Systems Manager Parameter Store with the new ReadMe API definition ID
        rm_definition_id=response.json()["_id"]
        parameters_client.put_parameter(Name=PARAMETERS_PREFIX+'RM-APIDefinitionID',
                                        Value=rm_definition_id, Type='String', Overwrite=True)
    else:
        # ReadMe API definition exists, update it
        response=requests.put(
            url+rm_definition_id, files={"spec": json.dumps(api_definition)}, headers=headers)

    # check if API definition upload request succeeded
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        # log request information for troubleshooting
        print("URL: " + url)
        # uncomment following line in case you will need to troublesoot authentication errors. Keep in mind that senstive information will be stored in your logs
        # print("Headers: "+headers)
        print("API definition:" + json.dumps(api_definition))

        # raise exception as ReadMe returned error message to be handled by Lambda service itself
        raise Exception(response.text)

    # received ReadMe response status code 200 - log response text
    print(response.text)
    return


def delete_readme_api_definition():
    # delete API definition in ReadMe using API key for authentication
    url=README_BASE_URL+rm_definition_id
    auth=base64.b64encode(rm_api_key.encode("utf-8"))
    headers={
        "Accept": "application/json",
        "Authorization": "Basic "+auth.decode("utf-8")
    }
    response=requests.delete(url, headers=headers)

    # check if request succeeded
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        # log request information for troubleshooting
        print("URL: " + url)
        # uncomment following line in case you will need to troublesoot authentication errors. Keep in mind that senstive information will be stored in your logs
        # print("Headers: "+headers)

        # raise exception as ReadMe returned error message
        raise Exception(response.text)

    # received ReadMe response status code 200 - log response text
    print(response.text)
    return
