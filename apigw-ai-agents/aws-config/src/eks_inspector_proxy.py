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
        cluster_arn = configuration_item.get('ARN')
        ordering_timestamp = configuration_item.get('configurationItemCaptureTime')
        
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
            
        if resource_type != 'AWS::EKS::Cluster':
            logger.info(f"Resource type {resource_type} is not an EKS cluster, skipping processing")
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
        
        # Invoke Bedrock agent to analyze the EKS cluster
        recommendations = invoke_bedrock_agent(resource_id)
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
        
        # Get owner email from EKS cluster tags and send recommendations
        owner_email = ""
        email_sent = False
        try:
            owner_email = get_cluster_owner_email(cluster_arn)
            if owner_email:
                subject = f"EKS Inspector recommendations for cluster: {resource_id}"
                send_recommendations_email(owner_email, subject, recommendations)
                email_sent = True
                logger.info(f"Recommendations sent to {owner_email}")
            else:
                logger.warning(f"No owner email found for {resource_type} {resource_id}. Continuing without sending recommendations.")
        except Exception as email_error:
            logger.error(f"Error sending email to EKS cluster {resource_id} owner: {str(email_error)}")
        
        # Determine compliance based on recommendations
        compliance_type = 'COMPLIANT'
        annotation = 'Resource inspection completed successfully'
        
        try:
            recommendations_json = json.loads(recommendations)
            critical_count = recommendations_json.get('inspection', {}).get('summary', {}).get('critical_findings', 0)
            high_count = recommendations_json.get('inspection', {}).get('summary', {}).get('high_findings', 0)
            medium_count = recommendations_json.get('inspection', {}).get('summary', {}).get('medium_findings', 0)
            low_count = recommendations_json.get('inspection', {}).get('summary', {}).get('low_findings', 0)
            
            # Mark as NON_COMPLIANT if critical or high severity findings are present
            if high_count > 0 or critical_count > 0:
                compliance_type = 'NON_COMPLIANT'
            
            annotation = f'Found issues: {critical_count} critical, {high_count} high, {medium_count} medium, {low_count} low severity findings.'

            # Add email notification information to the annotation
            if email_sent:
                annotation += f' Recommendations sent to {owner_email}'
            else:
                annotation += ' No email notification sent.'

        except json.JSONDecodeError:
            logger.warning("Could not parse recommendations as JSON, setting compliance status to NON_COMPLIANT")
            compliance_type = 'NON_COMPLIANT'
            annotation = 'Could not parse recommendations data'
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
                        'ComplianceResourceType': 'AWS::EKS::Cluster',
                        'ComplianceResourceId': 'unknown',
                        'ComplianceType': 'NON_COMPLIANT',
                        'Annotation': f'Error processing AWS Config event: {str(e)}',
                        'OrderingTimestamp': invoking_event.get('notificationCreationTime')
                    }],
                    ResultToken=event['resultToken']
                )
        except Exception as eval_error:
            logger.error(f"Error sending evaluation: {str(eval_error)}")


def invoke_bedrock_agent(cluster_id):
    try:
        # Initialize the Bedrock Agent Runtime client
        bedrock_agent_runtime = boto3.client(
            'bedrock-agent-runtime',
            region_name=os.getenv("REGION_FOR_BEDROCK"),
            config=config
        )
        
        # Invoke Bedrock EKS Inspector agent
        input_text = f"Inspect EKS cluster with ID {cluster_id} and provide improvement recommendations."
        input_text += f" Return your response as a valid JSON object with inspection results and recommendations."
        logger.info(f"Invoking EKS Inspector Bedrock agent for cluster {cluster_id}")
        response = bedrock_agent_runtime.invoke_agent(
            agentId=os.getenv("BEDROCK_AGENT_ID"),
            agentAliasId=os.getenv("BEDROCK_AGENT_ALIAS"),
            sessionId=cluster_id,
            inputText=input_text
        )
        
        # Process the streaming response
        result = ""
        for event in response.get("completion"):
            result += event['chunk']['bytes'].decode('utf-8')
        
        logger.info(f"Received recommendations from Bedrock agent: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error invoking Bedrock EKS Inspector agent: {str(e)}")
        return ""

def get_cluster_owner_email(cluster_arn):
    try:
        logger.info(f"Getting tags for EKS cluster {cluster_arn}")
        
        client = boto3.client('eks')
        try:
            response = client.list_tags_for_resource(resourceArn=cluster_arn)
            tags = response.get('tags', {})
            logger.info(f"Retrieved EKS cluster tags: {tags}")
            
            # Look for owner email in tags
            for key, value in tags.items():
                if key.lower() in ['owner_email', 'owner-email', 'email', 'owneremail']:
                    logger.info(f"Found owner email: {value} in tag {key}")
                    return value
        except Exception as eks_error:
            logger.warning(f"Error getting tags via EKS API: {str(eks_error)}. Trying configuration item tags.")
        
        # If we get here, we didn't find an email in the EKS tags or there was an error
        # Check if there are tags in the configuration item
        if 'tags' in globals() and isinstance(tags, dict) and tags:
            for key, value in tags.items():
                if key.lower() in ['owner_email', 'owner-email', 'email', 'owneremail']:
                    logger.info(f"Found owner email: {value} in configuration item tag {key}")
                    return value
        
        logger.warning(f"No owner email tag found for EKS cluster {cluster_arn}")
        return ""
        
    except Exception as e:
        logger.error(f"Error getting owner email for EKS cluster {cluster_arn}: {str(e)}")
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
