# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import botocore
import os

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
        print(f"Detected API ID: {api_id}")
    except KeyError:
        # Try HTTP API event format if REST didn't work
        try:
            api_id = event['detail']['requestParameters']['4litaeygd5']
            print(f"Detected API ID: {api_id}")
        except KeyError:
            print("Error: Could not extract API ID from event")
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

        # print(f"Recommendations: {result}")
    except Exception as e:
        print(f"Error invoking API Inspector agent: {e}")
        return 
    
    try:
        # Get owner email address from API tag 
        apigateway = boto3.client('apigateway')
        api_response = apigateway.get_rest_api(restApiId=api_id)
        owner_email = ""
        for key, value in api_response['tags'].items():
            if key == 'owner_email':
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
        print(f"Error sending recommendations to the API owner: {e}")
        return 

