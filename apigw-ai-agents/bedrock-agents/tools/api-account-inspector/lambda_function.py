# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. 
# SPDX-License-Identifier: MIT-0

import json
import boto3
import logging
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize API Gateway client
api_gateway = boto3.client('apigateway')
quotas_client = boto3.client('service-quotas')

def lambda_handler(event, context):
    """
    Lambda function to collect information about account that API Gateway runs in
    """
    logger.info(f"Processing event: {json.dumps(event, default=str)}")
    
    try:
        # Initialize the API info dictionary with default values
        api_info = {
            'accountSettings': {},
            'vpcLinks': [],
            'vpcLinksCount': 0,
            'customDomains': [],
            'domainNamesCount': 0,
            'apiKeysCount': 0,
            'usagePlansCount': 0,
            'clientCertificatesCount': 0,
            'apigwQuotas': []
        }
        
        # Get API Gateway account settings
        try:
            logger.info("Fetching API Gateway account settings")
            account = api_gateway.get_account()
            # Remove ResponseMetadata from account
            account.pop('ResponseMetadata', None)
            api_info['accountSettings'] = account
        except ClientError as e:
            logger.error(f"Error getting account settings: {str(e)}")
            api_info['accountSettings'] = {'error': str(e)}
        
        # Get custom domain names and their base path mappings
        try:
            logger.info("Fetching custom domain names")
            domain_names = api_gateway.get_domain_names()
            domain_names_count = len(domain_names.get('items', []))
            domain_info = []
            
            for domain in domain_names.get('items', []):
                try:
                    logger.info(f"Fetching base path mappings for domain: {domain['domainName']}")
                    base_paths = api_gateway.get_base_path_mappings(domainName=domain['domainName'])
                    domain_info.append({
                        'domainName': domain['domainName'],
                        'basePathMappings': base_paths.get('items', []),
                        'configuration': domain
                    })
                except ClientError as e:
                    logger.error(f"Error getting base path mappings for {domain['domainName']}: {str(e)}")
                    domain_info.append({
                        'domainName': domain['domainName'],
                        'basePathMappings': [],
                        'configuration': domain,
                        'error': str(e)
                    })
            
            api_info['customDomains'] = domain_info
            api_info['domainNamesCount'] = domain_names_count
        except ClientError as e:
            logger.error(f"Error getting domain names: {str(e)}")
            api_info['customDomains'] = []
            api_info['domainNamesCount'] = 0
        
        # Get VPC links
        try:
            logger.info("Fetching VPC links")
            vpc_links = api_gateway.get_vpc_links()
            api_info['vpcLinks'] = vpc_links.get('items', [])
            api_info['vpcLinksCount'] = len(vpc_links.get('items', []))
        except ClientError as e:
            logger.error(f"Error getting VPC links: {str(e)}")
            api_info['vpcLinks'] = []
            api_info['vpcLinksCount'] = 0
        
        # Get API keys count
        try:
            logger.info("Fetching API keys")
            api_keys = api_gateway.get_api_keys(limit=100)
            api_info['apiKeysCount'] = len(api_keys.get('items', []))
        except ClientError as e:
            logger.error(f"Error getting API keys: {str(e)}")
            api_info['apiKeysCount'] = 0
        
        # Get usage plans count
        try:
            logger.info("Fetching usage plans")
            usage_plans = api_gateway.get_usage_plans(limit=100)
            api_info['usagePlansCount'] = len(usage_plans.get('items', []))
        except ClientError as e:
            logger.error(f"Error getting usage plans: {str(e)}")
            api_info['usagePlansCount'] = 0
        
        # Get client certificates count
        try:
            logger.info("Fetching client certificates")
            client_certificates = api_gateway.get_client_certificates(limit=100)
            api_info['clientCertificatesCount'] = len(client_certificates.get('items', []))
        except ClientError as e:
            logger.error(f"Error getting client certificates: {str(e)}")
            api_info['clientCertificatesCount'] = 0
        
        # Get API Gateway service quotas for the account
        try:
            logger.info("Fetching API Gateway service quotas")
            apigw_quotas = quotas_client.list_service_quotas(ServiceCode='apigateway')
            api_info['apigwQuotas'] = apigw_quotas.get('Quotas', [])
        except ClientError as e:
            logger.error(f"Error getting API Gateway quotas: {str(e)}")
            api_info['apigwQuotas'] = []
    
        # Prepare the response
        logger.info("Preparing response with collected API information")
        returnValue = {
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
        while '  ' in str(returnValue):
            returnValue = json.loads(json.dumps(returnValue).replace('  ', ' '))
            
        logger.info("Successfully processed request")
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
                                'error': f"An error occurred while processing your request: {str(e)}",
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

