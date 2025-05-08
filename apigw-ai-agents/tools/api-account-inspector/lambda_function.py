# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. 
# SPDX-License-Identifier: MIT-0

import json
import boto3
from botocore.exceptions import ClientError

# Initialize API Gateway client
api_gateway = boto3.client('apigateway')
quotas_client=boto3.client('service-quotas')

def lambda_handler(event, context):
    """
    Lambda function to collect information about account that API Gateway runs in
    """
   
    # Get API Gateway account settings
    account = api_gateway.get_account()
    # Remove ResponseMetadata from account
    account.pop('ResponseMetadata', None)
    
    # Get custom domain names and their base path mappings
    domain_names = api_gateway.get_domain_names()
    domain_names_count=len(domain_names['items'])
    domain_info = []
    for domain in domain_names['items']:
        base_paths = api_gateway.get_base_path_mappings(domainName=domain['domainName'])
        domain_info.append({
            'domainName': domain['domainName'],
            'basePathMappings': base_paths.get('items', []),
            'configuration': domain
        })
        
    # Get VPC links
    vpc_links = api_gateway.get_vpc_links()
    # Get API keys count 
    api_keys = api_gateway.get_api_keys(limit=100)
    api_keys_count = len(api_keys.get('items', []))
    # Get usage plans count 
    usage_plans = api_gateway.get_usage_plans(limit=100)
    usage_plans_count = len(usage_plans.get('items', []))
    # Get client certificates count 
    client_certificates = api_gateway.get_client_certificates(limit=100)
    client_certificates_count = len(client_certificates.get('items', []))
    # Get API Gateway service quotas for the account
    apigw_quotas=quotas_client.list_service_quotas(ServiceCode='apigateway')
    
    # Compile all information
    api_info = {
        'accountSettings': account,
        'vpcLinks': vpc_links.get('items', []),
        'vpcLinksCount': len(vpc_links.get('items', [])),
        'customDomains': domain_info,
        'domainNamesCount': domain_names_count,
        'apiKeysCount': api_keys_count,
        'usagePlansCount': usage_plans_count,
        'clientCertificatesCount': client_certificates_count,
        'apigwQuotas': apigw_quotas.get('Quotas', [])
    }
    
    returnValue= {
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

