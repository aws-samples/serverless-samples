# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. 
# SPDX-License-Identifier: MIT-0

import json
import boto3
import logging
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_rest_api(api_id, stage_name):
    """
    Get REST API details from API Gateway
    """
    client = boto3.client('apigateway')
    logger.info(f"Attempting to export API definition for API ID: {api_id}, Stage: {stage_name}")
    
    try:
        response = client.get_export(
            restApiId=api_id,
            stageName=stage_name,  
            exportType='oas30',
            accepts='application/yaml',
            parameters={
                'extensions': 'apigateway'  
            }
        )
        logger.info(f"Successfully exported API definition for {api_id}")
        return response['body'].read().decode('utf-8')
    except client.exceptions.NotFoundException as e:
        logger.error(f"API or stage not found: {str(e)}")
        return None
    except ClientError as e:
        logger.error(f"AWS API error getting API details: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting API details: {str(e)}", exc_info=True)
        raise

def get_first_stage_name(api_id):
    """
    Get name of first stage for given API ID
    """
    client = boto3.client('apigateway')
    logger.info(f"Fetching stages for API ID: {api_id}")
    
    try:
        response = client.get_stages(restApiId=api_id)
        
        # Return first stage name if stages exist
        if response.get('item', []):
            stage_name = response['item'][0]['stageName']
            logger.info(f"Found stage: {stage_name}")
            return stage_name
            
        logger.warning(f"No stages found for API ID: {api_id}")
        return None
        
    except client.exceptions.NotFoundException as e:
        logger.error(f"API not found: {str(e)}")
        return None
    except ClientError as e:
        logger.error(f"AWS API error getting stages: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting stages: {str(e)}", exc_info=True)
        raise


def lambda_handler(event, context):
    """
    Lambda handler to export OpenAPI definition
    """
    logger.info(f"Processing event: {json.dumps(event, default=str)}")
    
    try:
        # Extract API ID from event
        try:
            api_id = event["parameters"][0]["value"]
            if not api_id:
                logger.error("API ID is missing")
                raise ValueError('apiId is required')
            logger.info(f"Processing API with ID: {api_id}")
        except (KeyError, IndexError) as e:
            logger.error(f"Error extracting API ID from event: {str(e)}")
            raise ValueError(f"Invalid event format: {str(e)}")

        # Get first stage name
        stage_name = get_first_stage_name(api_id)
        if not stage_name:
            logger.error(f"No stages found for API ID: {api_id}")
            raise ValueError(f"No stages found for API with ID {api_id}")
            
        # Get API definition
        api_definition = get_rest_api(api_id, stage_name)
        if api_definition is None:
            logger.error(f"Failed to retrieve API definition for API ID: {api_id}")
            raise ValueError(f"API with ID {api_id} not found or could not be exported")

        logger.info(f"Successfully retrieved API definition for API ID: {api_id}")
        
        # Prepare the response
        returnValue = {
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
        while '  ' in str(returnValue):
            returnValue = json.loads(json.dumps(returnValue).replace('  ', ' '))
            
        logger.info("Successfully processed API definition retrieval request")
        return returnValue
        
    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {str(e)}", exc_info=True)
        # Return a formatted error response
        error_response = {
            'messageVersion': "1.0",
            'response': {
                'actionGroup': event.get('actionGroup'),
                'function': event.get('function'),
                'functionResponse': {
                    'responseBody': {
                        "TEXT": { 
                            'body': json.dumps({
                                'error': f"An error occurred while retrieving the API definition: {str(e)}",
                                'status': 'error'
                            })                            
                        }
                    }
                },
                'sessionAttributes': event.get('sessionAttributes'),
                'promptSessionAttributes': event.get('promptSessionAttributes')
            }
        }
        return error_response