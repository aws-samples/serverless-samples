# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import botocore
import os
import logging
import json
import uuid

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
        # print(event)
        api_id = event['detail']['requestParameters']['restApiId']
        logger.info(f"Detected API ID: {api_id}")
    except KeyError:
        logger.error("Could not extract API ID from event")
        return

    try:
        # Initialize the AgentCore Runtime client
        agentcore_runtime = boto3.client(
            'bedrock-agentcore',
            region_name=os.getenv("AGENTCORE_REGION"),
            config=config
        )

        payload = json.dumps({"request": f"Inspect API with ID {api_id} and provide improvement recommendations"}).encode()
        session_id= "inspector_session_"+api_id+str(uuid.uuid4())

        # Invoke AgentCore agent and get response
        response = agentcore_runtime.invoke_agent_runtime(
            agentRuntimeArn=os.getenv("AGENTCORE_AGENT_ARN"),
            runtimeSessionId=session_id,
            payload=payload
        )
        # Parse the response
        result = response["response"].read().decode('utf-8')
        logger.info(f"Successfully invoked AgentCore agent for API {api_id}")
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
