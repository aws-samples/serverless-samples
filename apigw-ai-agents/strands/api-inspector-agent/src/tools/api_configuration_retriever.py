# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. 
# SPDX-License-Identifier: MIT-0

"""
API Gateway Endpoint Configuration Retriever Tool

This module provides functionality to retrieve Amazon API Gateway endpoint configuration

"""

import logging
from typing import Dict, Any, Optional
from strands import Agent, tool
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

@tool
async def api_configuration_retriever(api_id: str) -> Dict[str, Any]:
    """
    Collect API Gateway endpoint configuration.

    Args:
        api_id: ID of the API Gateway endpoint
    
    """

    # Initialize API Gateway client
    api_gateway = boto3.client('apigateway')
    waf_client = boto3.client('wafv2')

    try:
        # Initialize the API info dictionary with default values
        api_info = {
            'api': {},
            'stages': [],
            'stagesCount': 0,
            'authorizers': [],
            'resources': [],
            'resourcesCount': 0,
            'wafConfiguration': {},
            'models': [],
            'requestValidators': [],
            'integrations': {},
            'documentationVersions': [],
            'documentationParts': [],
            'tags': {},
            'gatewayResponses': [],
            'defaultEndpoint': False
        }
        
        # Get API details
        try:
            logger.info(f"Fetching API details for {api_id}")
            api = api_gateway.get_rest_api(restApiId=api_id)
            api_info['api'] = {
                'id': api['id'],
                'name': api['name'],
                'description': api.get('description'),
                'version': api.get('version'),
                'createdDate': api['createdDate'].isoformat(),
                'apiKeySource': api.get('apiKeySource'),
                'endpointConfiguration': api.get('endpointConfiguration'),
                'defaultEndpoint': api.get('disableExecuteApiEndpoint') != True
            }
        except ClientError as e:
            logger.error(f"Error getting API details: {str(e)}")
            raise ValueError(f"Failed to retrieve API with ID {api_id}: {str(e)}")
        
        # Get resources
        try:
            logger.info(f"Fetching resources for API {api_id}")
            resources = api_gateway.get_resources(restApiId=api_id)
            resources_count = len(resources.get('items', []))
            api_info['resourcesCount'] = resources_count
        except ClientError as e:
            logger.error(f"Error getting resources: {str(e)}")
            resources = {'items': []}
            api_info['resourcesCount'] = 0
        
        # Get detailed information about all resources
        resources_info = []
        for resource in resources.get('items', []):
            try:
                logger.info(f"Fetching details for resource {resource['id']}")
                resource_details = api_gateway.get_resource(
                    restApiId=api_id,
                    resourceId=resource['id']
                )
                # Remove ResponseMetadata from resource_details
                resource_details.pop('ResponseMetadata', None)
                resources_info.append(resource_details)
            except ClientError as e:
                logger.error(f"Error getting resource details for {resource['id']}: {str(e)}")
                resources_info.append({
                    'id': resource['id'],
                    'path': resource.get('path', ''),
                    'error': str(e)
                })
        api_info['resources'] = resources_info
        
        # Get stages
        try:
            logger.info(f"Fetching stages for API {api_id}")
            stages = api_gateway.get_stages(restApiId=api_id)
            stages_count = len(stages.get('item', []))
            api_info['stages'] = stages.get('item', [])
            api_info['stagesCount'] = stages_count
        except ClientError as e:
            logger.error(f"Error getting stages: {str(e)}")
            api_info['stages'] = []
            api_info['stagesCount'] = 0
        
        # Get authorizers
        try:
            logger.info(f"Fetching authorizers for API {api_id}")
            authorizers = api_gateway.get_authorizers(restApiId=api_id)
            api_info['authorizers'] = authorizers.get('items', [])
        except ClientError as e:
            logger.error(f"Error getting authorizers: {str(e)}")
            api_info['authorizers'] = []
    
        # Get WAF integration information
        waf_info = {}
        try:
            # Get current region
            region = boto3.session.Session().region_name
            logger.info(f"Fetching WAF configuration for API stages in region {region}")
            
            # Loop through all stages and get WAF info for each
            for stage in api_info['stages']:
                try:
                    stage_name = stage['stageName']
                    # Construct the API Gateway stage ARN
                    api_stage_arn = f"arn:aws:apigateway:{region}::/restapis/{api_id}/stages/{stage_name}"
                    logger.info(f"Checking WAF for stage {stage_name}")
                    
                    try:
                        # Get WAF information directly using the resource ARN
                        stage_waf_info = waf_client.get_web_acl_for_resource(
                            ResourceArn=api_stage_arn
                        )
                        # Remove ResponseMetadata from stage_waf_info
                        stage_waf_info.pop('ResponseMetadata', None)
                        waf_info[stage_name] = stage_waf_info
                        logger.info(f"Found WAF configuration for stage {stage_name}")
                    except ClientError as e:
                        # WAF might not be associated for this stage
                        if e.response['Error']['Code'] == 'WAFNonexistentItemException':
                            logger.info(f"No WAF associated with stage {stage_name}")
                            waf_info[stage_name] = None
                        else:
                            logger.error(f"Error getting WAF for stage {stage_name}: {str(e)}")
                            waf_info[stage_name] = {"error": str(e)}
                except Exception as e:
                    logger.error(f"Error processing stage for WAF info: {str(e)}")
                    continue
                        
        except ClientError as e:
            # Handle other WAF-related errors
            if e.response['Error']['Code'] == 'WAFNonexistentItemException':
                logger.info("No WAF configurations found")
            else:
                logger.error(f"Error getting WAF configuration: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error getting WAF configuration: {str(e)}")
        
        api_info['wafConfiguration'] = waf_info

        # Get model schemas and validators
        try:
            logger.info(f"Fetching models for API {api_id}")
            models = api_gateway.get_models(restApiId=api_id)
            api_info['models'] = models.get('items', [])
        except ClientError as e:
            logger.error(f"Error getting models: {str(e)}")
            api_info['models'] = []
            
        try:
            logger.info(f"Fetching request validators for API {api_id}")
            validators = api_gateway.get_request_validators(restApiId=api_id)
            api_info['requestValidators'] = validators.get('items', [])
        except ClientError as e:
            logger.error(f"Error getting request validators: {str(e)}")
            api_info['requestValidators'] = []
        
        # Get integrations for all resources
        integrations = {}
        logger.info(f"Fetching integrations for API {api_id} resources")
        for resource in resources.get('items', []):
            resource_integrations = {}
            resource_path = resource.get('path', 'unknown_path')
            
            for method in resource.get('resourceMethods', {}):
                try:
                    logger.info(f"Fetching integration for resource {resource['id']} method {method}")
                    integration = api_gateway.get_integration(
                        restApiId=api_id,
                        resourceId=resource['id'],
                        httpMethod=method
                    )
                    
                    # Get VPC Link info if applicable
                    if 'connectionType' in integration and integration['connectionType']=='VPC_LINK':
                        try:
                            logger.info(f"Fetching VPC link {integration['connectionId']} details")
                            vpc_link_info = api_gateway.get_vpc_link(vpcLinkId=integration['connectionId'])
                            integration['vpcLinkInfo'] = vpc_link_info
                        except ClientError as e:
                            logger.error(f"Error getting VPC link info: {str(e)}")
                            integration['vpcLinkInfo'] = {"error": str(e)}
                    
                    # Remove ResponseMetadata from integration
                    integration.pop('ResponseMetadata', None)
                    resource_integrations[method] = integration
                except ClientError as e:
                    logger.warning(f"Error getting integration for {resource_path} method {method}: {str(e)}")
                    continue
                    
            if resource_integrations:
                integrations[resource_path] = resource_integrations
        
        api_info['integrations'] = integrations

        # Get documentation versions for the API
        try:
            logger.info(f"Fetching documentation versions for API {api_id}")
            documentation_versions = api_gateway.get_documentation_versions(restApiId=api_id)
            api_info['documentationVersions'] = documentation_versions.get('items', [])
        except ClientError as e:
            logger.error(f"Error getting documentation versions: {str(e)}")
            api_info['documentationVersions'] = []
            
        # Get documentation parts for the API
        try:
            logger.info(f"Fetching documentation parts for API {api_id}")
            documentation_parts = api_gateway.get_documentation_parts(restApiId=api_id)
            api_info['documentationParts'] = documentation_parts.get('items', [])
        except ClientError as e:
            logger.error(f"Error getting documentation parts: {str(e)}")
            api_info['documentationParts'] = []
            
        # Get tags for the API
        try:
            region = boto3.session.Session().region_name
            logger.info(f"Fetching tags for API {api_id}")
            tags = api_gateway.get_tags(resourceArn=f"arn:aws:apigateway:{region}::/restapis/{api_id}")
            api_info['tags'] = tags.get('tags', {})
        except ClientError as e:
            logger.error(f"Error getting tags: {str(e)}")
            api_info['tags'] = {}
            
        # Get gateway responses for the API
        try:
            logger.info(f"Fetching gateway responses for API {api_id}")
            gateway_responses = api_gateway.get_gateway_responses(restApiId=api_id)
            api_info['gatewayResponses'] = gateway_responses.get('items', [])
        except ClientError as e:
            logger.error(f"Error getting gateway responses: {str(e)}")
            api_info['gatewayResponses'] = []
            
        logger.info("Successfully processed API configuration retrieval request")
        return api_info
        
    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {str(e)}", exc_info=True)
        raise RuntimeError(f"Request processing failed: {str(e)}")


# Export the main function for import
__all__ = ['api_configuration_retriever']


# print (api_configuration_retriever("lfw0wi4rxe"))