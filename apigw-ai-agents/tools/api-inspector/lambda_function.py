# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. 
# SPDX-License-Identifier: MIT-0

import json
import boto3
from botocore.exceptions import ClientError

# Initialize API Gateway client
api_gateway = boto3.client('apigateway')
waf_client = boto3.client('wafv2')  

def lambda_handler(event, context):
    """
    Lambda function to collect information about API Gateway endpoints
    """
    # Extract API Gateway ID and resource path from event
    api_id=event["parameters"][0]["value"]
    
    if not api_id:
        raise ValueError('API Gateway ID is required')

    # Get API details
    api = api_gateway.get_rest_api(restApiId=api_id)
    
    # Get resources
    resources = api_gateway.get_resources(restApiId=api_id)
    resources_count=len(resources['items'])
    
    # Get detailed information about all resources
    resources_info = []
    for resource in resources['items']:
        resource_details = api_gateway.get_resource(
            restApiId=api_id,
            resourceId=resource['id']
        )
        # Remove ResponseMetadata from resource_details
        resource_details.pop('ResponseMetadata', None)
        resources_info.append(resource_details)
    
    # Get stages
    stages = api_gateway.get_stages(restApiId=api_id)
    stages_count=len(stages['item'])
    
    # Get authorizers
    authorizers = api_gateway.get_authorizers(restApiId=api_id)
    
    # Get WAF integration information
    waf_info = {}
    try:
        # Get current region
        region = boto3.session.Session().region_name
        
        # Loop through all stages and get WAF info for each
        for stage in stages['item']:
            stage_name = stage['stageName']
            # Construct the API Gateway stage ARN
            api_stage_arn = f"arn:aws:apigateway:{region}::/restapis/{api_id}/stages/{stage_name}"
            
            try:
                # Get WAF information directly using the resource ARN
                stage_waf_info = waf_client.get_web_acl_for_resource(
                    ResourceArn=api_stage_arn
                )
                # Remove ResponseMetadata from stage_waf_info
                stage_waf_info.pop('ResponseMetadata', None)
                waf_info[stage_name] = stage_waf_info
            except ClientError as e:
                # WAF might not be associated for this stage
                if e.response['Error']['Code'] == 'WAFNonexistentItemException':
                    waf_info[stage_name] = None
                else:
                    raise e
                    
    except ClientError as e:
        # Handle other WAF-related errors
        if e.response['Error']['Code'] == 'WAFNonexistentItemException':
            pass
        else:
            raise e

        
    # Get model schemas and validators
    models = api_gateway.get_models(restApiId=api_id)
    validators = api_gateway.get_request_validators(restApiId=api_id)
    
    # Get integrations for all resources
    integrations = {}
    for resource in resources['items']:
        resource_integrations = {}
        for method in resource.get('resourceMethods', {}):
            try:
                integration = api_gateway.get_integration(
                    restApiId=api_id,
                    resourceId=resource['id'],
                    httpMethod=method
                )
                if 'connectionType' in integration and integration['connectionType']=='VPC_LINK':                    
                    vpc_link_info = api_gateway.get_vpc_link(vpcLinkId=integration['connectionId'])
                    integration['vpcLinkInfo'] = vpc_link_info
                # remove ResponseMetadata from integration
                integration.pop('ResponseMetadata', None)
                resource_integrations[method] = integration
            except ClientError:
                continue
        if resource_integrations:
            integrations[resource['path']] = resource_integrations

    # Get documentation versions for the API
    documentation_versions = api_gateway.get_documentation_versions(restApiId=api_id)
    # Get documentation parts for the API
    documentation_parts = api_gateway.get_documentation_parts(restApiId=api_id)
    # Get tags for the API
    tags = api_gateway.get_tags(resourceArn=f"arn:aws:apigateway:{region}::/restapis/{api_id}")
    # Get gateway responses for the API
    gateway_responses = api_gateway.get_gateway_responses(restApiId=api_id)
    
    # Compile all information
    api_info = {
        'api': {
            'id': api['id'],
            'name': api['name'],
            'description': api.get('description'),
            'version': api.get('version'),
            'createdDate': api['createdDate'].isoformat(),
            'apiKeySource': api.get('apiKeySource'),
            'endpointConfiguration': api.get('endpointConfiguration')
        },
        'stages': stages['item'],
        'stagesCount': stages_count,
        'authorizers': authorizers['items'],
        'resources': resources_info,
        'resourcesCount': resources_count,
        'wafConfiguration': waf_info,
        'models': models.get('items', []),
        'requestValidators': validators.get('items', []),
        'integrations': integrations,
        'documentationVersions': documentation_versions.get('items', []),
        'documentationParts': documentation_parts.get('items', []),
        'tags': tags.get('tags', {}),
        'gatewayResponses': gateway_responses.get('items', []),
        'defaultEndpoint': api.get('disableExecuteApiEndpoint') != True
    }
    
    returnValue={
        'messageVersion': "1.0",
        'response': {
            'actionGroup': event.get('actionGroup'),
            'function': event.get('function'),
            'functionResponse': {
            'responseBody': {
                    "TEXT": { 
                        'body': json.dumps(api_info, default=str)                            
                    }
                }
            },
            'sessionAttributes': event.get('sessionAttributes'),
            'promptSessionAttributes': event.get('promptSessionAttributes')
        }
    }

    # Remove all double spaces from the returnValue JSON
    while '  ' in returnValue:
        returnValue=returnValue.replace('  ', ' ')
    return returnValue