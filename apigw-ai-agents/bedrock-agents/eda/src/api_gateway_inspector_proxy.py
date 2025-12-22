# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import botocore
import os
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

config = botocore.config.Config(
    read_timeout=600,
    connect_timeout=600,
    retries={"max_attempts": 0}
)

def lambda_handler(event, context):
    
    # Extract API ID from the event
    try:
        # Try REST API event format first
        api_id = event['detail']['requestParameters']['restApiId']
        logger.info(f"Detected API ID: {api_id}")
    except KeyError:
        logger.error("Could not extract API ID from event")
        return

    try:
        # Initialize the Bedrock Agent Runtime client
        bedrock_agent_runtime = boto3.client(
            'bedrock-agent-runtime',
            region_name=os.getenv("REGION_FOR_BEDROCK"),
            config=config
        )
        # Invoke bedrock API Inspector agent and get response
        response = bedrock_agent_runtime.invoke_agent(
            agentId=os.getenv("BEDROCK_AGENT_ID"),
            agentAliasId=os.getenv("BEDROCK_AGENT_ALIAS"),
            sessionId=api_id,
            inputText=f"Inspect API with ID {api_id} and provide improvement recommendations"
        )
        result=""
        for event in response.get("completion"):
            result+=event['chunk']['bytes'].decode('utf-8')

        # logger.info(f"Recommendations: {result}")
    except Exception as e:
        logger.error(f"Error invoking API Inspector agent: {e}", exc_info=True)
        return 
    
    try:
        # Get owner email address from API tag 
        apigateway = boto3.client('apigateway')
        api_response = apigateway.get_rest_api(restApiId=api_id)
        owner_email = ""
        # Check for various possible tag names for owner email
        owner_email_tags = ['owner_email', 'owner-email', 'OwnerEmail', 'ownerEmail', 'email', 'contact', 'owner']
        for key, value in api_response['tags'].items():
            if key.lower() in [tag.lower() for tag in owner_email_tags]:
                owner_email = value
                break
        # Send email to the owner using SES
        if owner_email:
            ses = boto3.client('ses')
            ses.send_email(
                Source=os.getenv("SES_EMAIL"),
                Destination={'ToAddresses': [owner_email]},
                Message={
                    'Subject': {'Data': f"API Inspector recommendations for API with ID: {api_id}"},
                    'Body': {
                        'Text': {'Data': result}
                    }
                }
            )
            return
        else:
            # Rise an exception if owner email is not found
            raise Exception("Owner email not found in API tags")
    except Exception as e:
        logger.error(f"Error sending recommendations to the API owner: {e}", exc_info=True)
        return 

