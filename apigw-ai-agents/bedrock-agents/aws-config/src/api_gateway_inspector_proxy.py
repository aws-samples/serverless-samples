# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import botocore
import os
import json
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configure boto3 client with extended timeout for Bedrock operations
config = botocore.config.Config(
    read_timeout=600,
    connect_timeout=600,
    retries={"max_attempts": 0}
)

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract resource information from AWS Config event
        invoking_event = json.loads(event['invokingEvent'])
        configuration_item = invoking_event.get('configurationItem', {})
        result_token = event.get('resultToken', '')
        
        if not configuration_item:
            logger.error("No configuration item found in the event")
            if result_token:
                boto3.client('config').put_evaluations(
                    Evaluations=[{
                        'ComplianceType': 'NOT_APPLICABLE',
                        'Annotation': 'No configuration item found in the event',
                        'OrderingTimestamp': invoking_event.get('notificationCreationTime')}],
                    ResultToken=result_token
                )
            return
        
        resource_type = configuration_item.get('resourceType')
        resource_id = configuration_item.get('resourceId')
        api_gateway_arn = configuration_item.get('ARN')
        ordering_timestamp = configuration_item.get('configurationItemCaptureTime')
        
        # Extract API ID from ARN
        api_id = api_gateway_arn.split('/')[-1]
        
        logger.info(f"Processing {resource_type} with ID: {resource_id}")
        
        if not resource_id:
            logger.error("No resource ID found in the configuration item")
            if result_token:
                boto3.client('config').put_evaluations(
                    Evaluations=[{
                        'ComplianceResourceType': resource_type,
                        'ComplianceResourceId': 'unknown',
                        'ComplianceType': 'NOT_APPLICABLE',
                        'Annotation': 'No resource ID found in the configuration item',
                        'OrderingTimestamp': ordering_timestamp}],
                    ResultToken=result_token
                )
            return
            
        if resource_type != 'AWS::ApiGateway::RestApi' and resource_type != 'AWS::ApiGatewayV2::Api':
            logger.info(f"Resource type {resource_type} is not an API Gateway, skipping processing")
            if result_token:
                boto3.client('config').put_evaluations(
                    Evaluations=[{
                        'ComplianceResourceType': resource_type,
                        'ComplianceResourceId': resource_id,
                        'ComplianceType': 'NOT_APPLICABLE',
                        'Annotation': f'Resource type {resource_type} is not supported by this rule',
                        'OrderingTimestamp': ordering_timestamp}],
                    ResultToken=result_token
                )
            return
        
        # Invoke Bedrock agent to analyze the API Gateway
        recommendations = invoke_bedrock_agent(api_id, resource_type)
        if not recommendations:
            logger.error("Failed to get recommendations from Bedrock agent")
            if result_token:
                boto3.client('config').put_evaluations(
                    Evaluations=[{
                        'ComplianceResourceType': resource_type,
                        'ComplianceResourceId': resource_id,
                        'ComplianceType': 'NON_COMPLIANT',
                        'Annotation': 'Failed to get recommendations from Bedrock agent',
                        'OrderingTimestamp': ordering_timestamp
                    }],
                    ResultToken=result_token
                )
            return
        
        # Get owner email from API Gateway tags and send recommendations
        owner_email = ""
        email_sent = False
        try:
            owner_email = get_api_gateway_owner_email(api_gateway_arn, resource_type)
            if owner_email:
                subject = f"API Gateway Inspector recommendations for API: {api_id}"
                send_recommendations_email(owner_email, subject, recommendations)
                email_sent = True
                logger.info(f"Recommendations sent to {owner_email}")
            else:
                logger.warning(f"No owner email found for {resource_type} {resource_id}. Continuing without sending recommendations.")
        except Exception as email_error:
            logger.error(f"Error sending email to API Gateway {resource_id} owner: {str(email_error)}")
        
        # Determine compliance based on recommendations
        # Always mark as NON_COMPLIANT if there are any recommendations
        compliance_type = 'NON_COMPLIANT' if '<recommendations>' in recommendations and len(recommendations.strip()) > 0 else 'COMPLIANT'
        annotation = 'Resource inspection completed successfully'
        
        try:
            # Extract recommendations section
            recommendations_text = ''
            if '<recommendations>' in recommendations and '</recommendations>' in recommendations:
                recommendations_text = recommendations.split('<recommendations>')[1].split('</recommendations>')[0].strip()
            
            # If there are any recommendations, mark as NON_COMPLIANT
            if recommendations_text:
                compliance_type = 'NON_COMPLIANT'
                annotation = f'API Gateway inspection found issues that need attention.'
            else:
                compliance_type = 'COMPLIANT'
                annotation = 'No issues found in API Gateway configuration.'

            # Add email notification information to the annotation
            if email_sent:
                annotation += f' Recommendations sent to {owner_email}'
            else:
                annotation += ' No email notification sent.'

        except Exception as e:
            logger.warning(f"Error determining compliance from recommendations: {str(e)}")
            compliance_type = 'NON_COMPLIANT'
            annotation = f'Error determining compliance from recommendations: {str(e)}'
        
        # Send the evaluation result to AWS Config
        if result_token:
            boto3.client('config').put_evaluations(
                Evaluations=[{
                    'ComplianceResourceType': resource_type,
                    'ComplianceResourceId': resource_id,
                    'ComplianceType': compliance_type,
                    'Annotation': annotation,
                    'OrderingTimestamp': ordering_timestamp}],
                ResultToken=result_token
            )
            return
     
    except Exception as e:
        logger.error(f"Error processing AWS Config event: {str(e)}")
        # Try to send an error evaluation if possible
        try:
            if 'resultToken' in event:
                boto3.client('config').put_evaluations(
                    Evaluations=[{
                        'ComplianceResourceType': 'AWS::ApiGateway::RestApi',
                        'ComplianceResourceId': 'unknown',
                        'ComplianceType': 'NON_COMPLIANT',
                        'Annotation': f'Error processing AWS Config event: {str(e)}',
                        'OrderingTimestamp': invoking_event.get('notificationCreationTime')
                    }],
                    ResultToken=event['resultToken']
                )
        except Exception as eval_error:
            logger.error(f"Error sending evaluation: {str(eval_error)}")


def invoke_bedrock_agent(api_id, api_type):
    try:
        # Initialize the Bedrock Agent Runtime client
        bedrock_agent_runtime = boto3.client(
            'bedrock-agent-runtime',
            region_name=os.getenv("REGION_FOR_BEDROCK"),
            config=config
        )
        
        # Invoke existing API Inspector Bedrock agent
        input_text = f"Inspect API Gateway with ID {api_id} and provide a detailed assessment and recommendations for improvements. Focus on security, performance, and best practices. Format your response with <assessment> and <recommendations> sections."
        logger.info(f"Invoking API Inspector Bedrock agent for API {api_id}")
        response = bedrock_agent_runtime.invoke_agent(
            agentId=os.getenv("BEDROCK_AGENT_ID"),
            agentAliasId=os.getenv("BEDROCK_AGENT_ALIAS"),
            sessionId=api_id,
            inputText=input_text
        )
        
        # Process the streaming response
        result = ""
        for event in response.get("completion"):
            result += event['chunk']['bytes'].decode('utf-8')
        
        logger.info(f"Received recommendations from Bedrock agent: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error invoking Bedrock API Gateway Inspector agent: {str(e)}")
        return ""

def get_api_gateway_owner_email(api_gateway_arn, resource_type):
    try:
        logger.info(f"Getting tags for API Gateway {api_gateway_arn}")
        
        # Determine which API Gateway client to use based on resource type
        if resource_type == 'AWS::ApiGateway::RestApi':
            client = boto3.client('apigateway')
            try:
                response = client.get_tags(resourceArn=api_gateway_arn)
                tags = response.get('tags', {})
                logger.info(f"Retrieved API Gateway tags: {tags}")
            except Exception as api_error:
                logger.warning(f"Error getting tags via API Gateway API: {str(api_error)}. Trying configuration item tags.")
                tags = {}
        else:  # AWS::ApiGatewayV2::Api
            client = boto3.client('apigatewayv2')
            try:
                response = client.get_tags(ResourceArn=api_gateway_arn)
                tags = response.get('Tags', {})
                logger.info(f"Retrieved API Gateway V2 tags: {tags}")
            except Exception as api_error:
                logger.warning(f"Error getting tags via API Gateway V2 API: {str(api_error)}. Trying configuration item tags.")
                tags = {}
        
        # Look for owner email in tags
        for key, value in tags.items():
            if key.lower() in ['owner_email', 'owner-email', 'email', 'owneremail']:
                logger.info(f"Found owner email: {value} in tag {key}")
                return value
        
        logger.warning(f"No owner email tag found for API Gateway {api_gateway_arn}")
        return ""
        
    except Exception as e:
        logger.error(f"Error getting owner email for API Gateway {api_gateway_arn}: {str(e)}")
        return ""

def send_recommendations_email(owner_email, subject, recommendations):
    if not owner_email:
        logger.error("Cannot send email: owner_email is empty")
        return
        
    try:
        ses = boto3.client('ses')
        logger.info(f"Sending email to {owner_email} from {os.getenv('SES_EMAIL')}")
        response = ses.send_email(
            Source=os.getenv("SES_EMAIL"),
            Destination={'ToAddresses': [owner_email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {
                    'Text': {'Data': recommendations}
                }
            }
        )
        logger.info(f"Email sent successfully with message ID: {response.get('MessageId')}")
        
    except Exception as e:
        logger.error(f"Error sending recommendations email to {owner_email}: {str(e)}")