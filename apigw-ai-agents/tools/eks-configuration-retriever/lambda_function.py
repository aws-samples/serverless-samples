# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import json
import logging
import os
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract parameters from Bedrock agent format
        cluster_name = None
        region = os.environ.get('AWS_REGION')
        
        if 'parameters' in event and isinstance(event['parameters'], list):
            for param in event['parameters']:
                if param['name'] == 'cluster_name':
                    cluster_name = param['value']
                elif param['name'] == 'region':
                    region = param['value']
        
        # Validate cluster_name
        if not cluster_name:
            error_msg = "Missing required parameter: cluster_name"
            logger.error(error_msg)
            return format_bedrock_response(event, {'error': error_msg})
        
        logger.info(f"Retrieving configuration for EKS cluster: {cluster_name} in region: {region}")
        
        # Initialize EKS client
        eks_client = boto3.client('eks', region_name=region)
        
        # Get cluster details
        cluster_details = get_cluster_details(eks_client, cluster_name)
        
        # Get node groups
        node_groups = get_node_groups(eks_client, cluster_name)
        
        # Get Fargate profiles
        fargate_profiles = get_fargate_profiles(eks_client, cluster_name)
        
        # Get add-ons
        addons = get_addons(eks_client, cluster_name)
        
        # Get OIDC provider if exists
        oidc_provider = get_oidc_provider(eks_client, cluster_name, cluster_details)
        
        # Compile the complete configuration
        cluster_config = {
            'cluster': cluster_details,
            'nodeGroups': node_groups,
            'fargateProfiles': fargate_profiles,
            'addons': addons,
            'oidcProvider': oidc_provider
        }
        
        # Get IAM roles used by the cluster
        iam_roles = get_iam_roles(cluster_config)
        cluster_config['iamRoles'] = iam_roles
        
        # Get security groups
        security_groups = get_security_groups(cluster_details, region)
        cluster_config['securityGroups'] = security_groups
        
        logger.info(f"Successfully retrieved configuration for EKS cluster {cluster_name}: {cluster_config}")
        
        # Return in Bedrock agent format
        return format_bedrock_response(event, cluster_config)
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        logger.error(f"AWS Error ({error_code}): {error_msg}")
        
        error_response = {
            'error': f"AWS Error: {error_code}",
            'message': error_msg
        }
        
        return format_bedrock_response(event, error_response)
    except Exception as e:
        logger.error(f"Error retrieving EKS configuration: {str(e)}")
        
        error_response = {
            'error': "Internal Error",
            'message': str(e)
        }
        
        return format_bedrock_response(event, error_response)

def format_bedrock_response(event, response_data):
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': event.get('actionGroup'),
            'function': event.get('function'),
            'functionResponse': {
                'responseBody': {
                    'TEXT': {
                        'body': json.dumps(response_data, default=str)
                    }
                }
            },
            'sessionAttributes': event.get('sessionAttributes'),
            'promptSessionAttributes': event.get('promptSessionAttributes')
        }
    }

def get_cluster_details(eks_client, cluster_name):
    try:
        response = eks_client.describe_cluster(name=cluster_name)
        return response['cluster']
    except ClientError as e:
        logger.error(f"Error getting cluster details: {e}")
        raise

def get_node_groups(eks_client, cluster_name):
    try:
        # List all node groups
        response = eks_client.list_nodegroups(clusterName=cluster_name)
        nodegroup_names = response.get('nodegroups', [])
        
        # Get details for each node group
        nodegroups = []
        for ng_name in nodegroup_names:
            ng_details = eks_client.describe_nodegroup(
                clusterName=cluster_name,
                nodegroupName=ng_name
            )
            nodegroups.append(ng_details['nodegroup'])
        
        return nodegroups
    except ClientError as e:
        logger.error(f"Error getting node groups: {e}")
        return []

def get_fargate_profiles(eks_client, cluster_name):
    try:
        # List all Fargate profiles
        response = eks_client.list_fargate_profiles(clusterName=cluster_name)
        profile_names = response.get('fargateProfileNames', [])
        
        # Get details for each Fargate profile
        profiles = []
        for profile_name in profile_names:
            profile_details = eks_client.describe_fargate_profile(
                clusterName=cluster_name,
                fargateProfileName=profile_name
            )
            profiles.append(profile_details['fargateProfile'])
        
        return profiles
    except ClientError as e:
        logger.error(f"Error getting Fargate profiles: {e}")
        return []

def get_addons(eks_client, cluster_name):
    try:
        # List all add-ons
        response = eks_client.list_addons(clusterName=cluster_name)
        addon_names = response.get('addons', [])
        
        # Get details for each add-on
        addons = []
        for addon_name in addon_names:
            addon_details = eks_client.describe_addon(
                clusterName=cluster_name,
                addonName=addon_name
            )
            addons.append(addon_details['addon'])
        
        return addons
    except ClientError as e:
        logger.error(f"Error getting add-ons: {e}")
        return []

def get_oidc_provider(eks_client, cluster_name, cluster_details):
    try:
        if 'identity' in cluster_details and 'oidc' in cluster_details['identity']:
            oidc_issuer = cluster_details['identity']['oidc'].get('issuer')
            if oidc_issuer:
                # Get OIDC provider details from IAM
                iam_client = boto3.client('iam')
                # Extract provider ID from the issuer URL
                provider_id = oidc_issuer.replace('https://', '')
                
                try:
                    response = iam_client.get_open_id_connect_provider(
                        OpenIDConnectProviderArn=f"arn:aws:iam::{boto3.client('sts').get_caller_identity()['Account']}:oidc-provider/{provider_id}"
                    )
                    return {
                        'url': oidc_issuer,
                        'arn': f"arn:aws:iam::{boto3.client('sts').get_caller_identity()['Account']}:oidc-provider/{provider_id}",
                        'clientIDs': response.get('ClientIDList', []),
                        'thumbprint': response.get('ThumbprintList', [])
                    }
                except ClientError:
                    # Provider might exist but not in IAM
                    return {
                        'url': oidc_issuer,
                        'configured': False
                    }
        return None
    except Exception as e:
        logger.error(f"Error getting OIDC provider: {e}")
        return None

def get_iam_roles(cluster_config):
    roles = {}
    iam_client = boto3.client('iam')
    
    # Helper function to get role name from ARN
    def get_role_name_from_arn(role_arn):
        return role_arn.split('/')[-1] if '/' in role_arn else role_arn.split(':')[-1]
    
    # Helper function to get policies for a role
    def get_role_policies(role_arn):
        role_name = get_role_name_from_arn(role_arn)
        policies = []
        
        try:
            # Get managed policies
            managed_policies = iam_client.list_attached_role_policies(RoleName=role_name)
            for policy in managed_policies.get('AttachedPolicies', []):
                policies.append({
                    'policyName': policy['PolicyName'],
                    'policyArn': policy['PolicyArn'],
                    'type': 'managed'
                })
            
            # Get inline policies
            inline_policies = iam_client.list_role_policies(RoleName=role_name)
            for policy_name in inline_policies.get('PolicyNames', []):
                policy_document = iam_client.get_role_policy(
                    RoleName=role_name,
                    PolicyName=policy_name
                )
                policies.append({
                    'policyName': policy_name,
                    'policyDocument': policy_document.get('PolicyDocument'),
                    'type': 'inline'
                })
                
            return policies
        except ClientError as e:
            logger.warning(f"Error getting policies for role {role_name}: {e}")
            return [{'error': str(e)}]
    
    # Cluster role
    if 'roleArn' in cluster_config['cluster']:
        role_arn = cluster_config['cluster']['roleArn']
        roles['clusterRole'] = {
            'roleArn': role_arn,
            'policies': get_role_policies(role_arn)
        }
    
    # Node group roles
    for ng in cluster_config['nodeGroups']:
        if 'nodeRole' in ng:
            role_arn = ng['nodeRole']
            roles[f"nodeGroup_{ng['nodegroupName']}"] = {
                'roleArn': role_arn,
                'policies': get_role_policies(role_arn)
            }
    
    # Fargate profile roles
    for profile in cluster_config['fargateProfiles']:
        if 'podExecutionRoleArn' in profile:
            role_arn = profile['podExecutionRoleArn']
            roles[f"fargateProfile_{profile['fargateProfileName']}"] = {
                'roleArn': role_arn,
                'policies': get_role_policies(role_arn)
            }
    
    return roles

def get_security_groups(cluster_details, region):
    try:
        if 'resourcesVpcConfig' not in cluster_details:
            return []
        
        security_group_ids = cluster_details['resourcesVpcConfig'].get('securityGroupIds', [])
        cluster_sg = cluster_details['resourcesVpcConfig'].get('clusterSecurityGroupId')
        
        if cluster_sg:
            security_group_ids.append(cluster_sg)
        
        if not security_group_ids:
            return []
        
        # Get security group details
        ec2_client = boto3.client('ec2', region_name=region)
        response = ec2_client.describe_security_groups(GroupIds=security_group_ids)
        
        return response.get('SecurityGroups', [])
    except ClientError as e:
        logger.error(f"Error getting security groups: {e}")
        return []