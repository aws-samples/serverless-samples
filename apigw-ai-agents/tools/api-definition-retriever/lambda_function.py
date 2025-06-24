# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. 
# SPDX-License-Identifier: MIT-0

import json
import boto3

def get_rest_api(api_id, stage_name):
    """
    Get REST API details from API Gateway
    """
    client = boto3.client('apigateway')
    try:
        response = client.get_export(
            restApiId=api_id,
            stageName=stage_name,  # This exports the entire API, not stage-specific
            exportType='oas30',
            accepts='application/yaml',
            parameters={
                'extensions': 'apigateway'  # Include API Gateway extensions
            }
        )
        return response['body'].read().decode('utf-8')
    except client.exceptions.NotFoundException:
        return None
    except Exception as e:
        print(f"Error getting API details: {str(e)}")
        raise

def get_first_stage_name(api_id):
    """
    Get name of first stage for given API ID
    """
    client = boto3.client('apigateway')
    try:
        # Get list of stages for the API
        response = client.get_stages(restApiId=api_id)
        
        # Return first stage name if stages exist
        if response['item']:
            return response['item'][0]['stageName']
        return None
        
    except client.exceptions.NotFoundException:
        return None
    except Exception as e:
        print(f"Error getting stages: {str(e)}")
        raise        


def lambda_handler(event, context):
    """
    Lambda handler to export OpenAPI definition
    """
    # Extract API ID from event
    api_id=event["parameters"][0]["value"]
    if not api_id:
        raise ValueError('apiId is required')

    # Get API definition
    api_definition = get_rest_api(api_id, get_first_stage_name(api_id))
    if api_definition is None:
        raise ValueError('API not found')

    returnValue={
        'messageVersion': "1.0",
        'response': {
            'actionGroup': event.get('actionGroup'),
            'function': event.get('function'),
            'functionResponse': {
            'responseBody': {
                    "TEXT": { 
                        'body': json.dumps(api_definition)
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