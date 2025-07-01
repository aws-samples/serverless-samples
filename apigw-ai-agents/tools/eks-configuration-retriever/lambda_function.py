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
        
        # Initialize AWS clients - reuse across functions
        eks_client = boto3.client('eks', region_name=region)
        ec2_client = boto3.client('ec2', region_name=region)
        iam_client = boto3.client('iam')
        sts_client = boto3.client('sts')
        
        # Get account ID once
        account_id = sts_client.get_caller_identity()['Account']
        
        # Get cluster details
        cluster_details = get_cluster_details(eks_client, cluster_name)
        
        # Get node groups
        node_groups = get_node_groups(eks_client, cluster_name)
        
        # Get Fargate profiles
        fargate_profiles = get_fargate_profiles(eks_client, cluster_name)
        
        # Get add-ons
        addons = get_addons(eks_client, cluster_name)
        
        # Get OIDC provider if exists
        oidc_provider = get_oidc_provider(iam_client, account_id, cluster_details)
        
        # Get control plane logging status
        control_plane_logging = get_control_plane_logging_data(cluster_details)
        
        # Get API endpoint access configuration
        api_endpoint_access = get_api_endpoint_config(cluster_details)
        
        # Get Kubernetes version information
        kubernetes_version_info = get_kubernetes_version_data(eks_client, cluster_details)
        
        # Get AZ distribution data
        az_distribution = get_az_distribution_data(ec2_client, cluster_name)
        
        # Get tagging data
        tagging_data = get_tagging_data(cluster_details)
        
        # Get encryption configuration data
        encryption_config = get_encryption_config_data(ec2_client, cluster_details)
        
        # Get Karpenter configuration data
        karpenter_data = get_karpenter_data(eks_client, ec2_client, cluster_name, addons)
        
        # Get EKS Auto Mode data
        eks_auto_mode_data = get_eks_auto_mode_data(cluster_details, node_groups, ec2_client, cluster_name)
        
        # Compile the complete configuration
        cluster_config = {
            'cluster': cluster_details,
            'nodeGroups': node_groups,
            'fargateProfiles': fargate_profiles,
            'addons': addons,
            'oidcProvider': oidc_provider,
            'controlPlaneLogging': control_plane_logging,
            'apiEndpointAccess': api_endpoint_access,
            'kubernetesVersion': kubernetes_version_info,
            'azDistribution': az_distribution,
            'tagging': tagging_data,
            'encryptionConfig': encryption_config,
            'karpenter': karpenter_data,
            'eksAutoMode': eks_auto_mode_data
        }
        
        # Get IAM roles used by the cluster
        iam_roles = get_iam_roles(iam_client, cluster_config)
        cluster_config['iamRoles'] = iam_roles
        
        # Get security groups
        security_groups = get_security_groups_data(ec2_client, cluster_details)
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

def get_oidc_provider(iam_client, account_id, cluster_details):
    try:
        if 'identity' in cluster_details and 'oidc' in cluster_details['identity']:
            oidc_issuer = cluster_details['identity']['oidc'].get('issuer')
            if oidc_issuer:
                # Extract provider ID from the issuer URL
                provider_id = oidc_issuer.replace('https://', '')
                oidc_arn = f"arn:aws:iam::{account_id}:oidc-provider/{provider_id}"
                
                try:
                    response = iam_client.get_open_id_connect_provider(
                        OpenIDConnectProviderArn=oidc_arn
                    )
                    return {
                        'url': oidc_issuer,
                        'arn': oidc_arn,
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

def get_iam_roles(iam_client, cluster_config):
    roles = {}
    
     # Helper function to get policies for a role
    def get_role_policies(role_arn):
        role_name = role_arn.split('/')[-1] if '/' in role_arn else role_arn.split(':')[-1]
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

def get_security_groups_data(ec2_client, cluster_details):
    try:
        if 'resourcesVpcConfig' not in cluster_details:
            return []
        
        security_group_ids = cluster_details['resourcesVpcConfig'].get('securityGroupIds', [])
        cluster_sg = cluster_details['resourcesVpcConfig'].get('clusterSecurityGroupId')
        
        if cluster_sg and cluster_sg not in security_group_ids:
            security_group_ids.append(cluster_sg)
        
        if not security_group_ids:
            return []
        
        # Get security group details
        response = ec2_client.describe_security_groups(GroupIds=security_group_ids)
        
        return response.get('SecurityGroups', [])
    except ClientError as e:
        logger.error(f"Error getting security groups: {e}")
        return []



def get_control_plane_logging_data(cluster_details):
    """
    Get the status of EKS control plane logging
    """
    try:
        # Use the cluster details we already have instead of making another API call
        logging_config = cluster_details.get('logging', {}).get('clusterLogging', [])
        
        enabled_types = []
        disabled_types = []
        
        for config in logging_config:
            if config.get('enabled'):
                enabled_types.extend(config.get('types', []))
            else:
                disabled_types.extend(config.get('types', []))
        
        return {
            'enabled': enabled_types,
            'disabled': disabled_types
        }
    except Exception as e:
        logger.error(f"Error getting control plane logging: {e}")
        return {'error': str(e)}

def get_api_endpoint_config(cluster_details):
    """
    Get the API endpoint access configuration
    """
    vpc_config = cluster_details.get('resourcesVpcConfig', {})
    
    return {
        'public_access': vpc_config.get('endpointPublicAccess', False),
        'private_access': vpc_config.get('endpointPrivateAccess', False),
        'public_access_cidrs': vpc_config.get('publicAccessCidrs', [])
    }

def get_kubernetes_version_data(eks_client, cluster_details):
    """
    Get the Kubernetes version information
    """
    current_version = cluster_details.get('version')
    
    try:
        # Get available versions
        response = eks_client.describe_addon_versions()
        
        # Extract all available Kubernetes versions
        available_versions = set()
        for addon in response.get('addons', []):
            for version in addon.get('addonVersions', []):
                for compatibility in version.get('compatibilities', []):
                    if 'clusterVersion' in compatibility:
                        available_versions.add(compatibility['clusterVersion'])
        
        available_versions = sorted(list(available_versions), reverse=True)
        latest_version = available_versions[0] if available_versions else current_version
        
        return {
            'current_version': current_version,
            'latest_version': latest_version,
            'available_versions': available_versions[:5]  # Return top 5 versions
        }
    except Exception as e:
        logger.error(f"Error getting Kubernetes version data: {e}")
        return {
            'current_version': current_version,
            'error': str(e)
        }

def get_az_distribution_data(ec2_client, cluster_name):
    """
    Get the distribution of nodes across availability zones
    """
    try:
        node_count_by_az = {}
        total_nodes = 0
        
        # Get all instances with the cluster tag
        filters = [{'Name': 'tag:eks:cluster-name', 'Values': [cluster_name]}]
        
        paginator = ec2_client.get_paginator('describe_instances')
        for page in paginator.paginate(Filters=filters):
            for reservation in page.get('Reservations', []):
                for instance in reservation.get('Instances', []):
                    if instance.get('State', {}).get('Name') == 'running':
                        az = instance.get('Placement', {}).get('AvailabilityZone')
                        if az:
                            if az not in node_count_by_az:
                                node_count_by_az[az] = 0
                            node_count_by_az[az] += 1
                            total_nodes += 1
        
        # Get all available AZs in the region
        available_azs = ec2_client.describe_availability_zones(
            Filters=[{'Name': 'state', 'Values': ['available']}]
        )
        all_azs = [az['ZoneName'] for az in available_azs.get('AvailabilityZones', [])]
        
        return {
            'node_count_by_az': node_count_by_az,
            'total_nodes': total_nodes,
            'available_azs': all_azs,
            'azs_with_nodes': list(node_count_by_az.keys())
        }
    except Exception as e:
        logger.error(f"Error getting AZ distribution data: {e}")
        return {'error': str(e)}

def get_tagging_data(cluster_details):
    """
    Get the tagging data of the cluster
    """
    tags = cluster_details.get('tags', {})
    
    return {
        'tags': tags,
        'tag_count': len(tags)
    }

def get_encryption_config_data(ec2_client, cluster_details):
    """
    Get the encryption configuration data for the cluster
    """
    try:
        # Check for EKS secrets encryption
        encryption_config = cluster_details.get('encryptionConfig', [])
        secrets_encryption_enabled = len(encryption_config) > 0
        
        # Check for EBS encryption by default in the region
        ebs_encryption_by_default = False
        
        try:
            ebs_encryption = ec2_client.get_ebs_encryption_by_default()
            ebs_encryption_by_default = ebs_encryption.get('EbsEncryptionByDefault', False)
        except ClientError as e:
            logger.warning(f"Could not determine EBS encryption by default: {e}")
        
        return {
            'secrets_encryption': {
                'enabled': secrets_encryption_enabled,
                'config': encryption_config
            },
            'ebs_encryption': {
                'default_encryption': ebs_encryption_by_default
            }
        }
    except Exception as e:
        logger.error(f"Error getting encryption configuration data: {e}")
        return {'error': str(e)}

def get_karpenter_data(eks_client, ec2_client, cluster_name, addons):
    """
    Get enhanced Karpenter configuration data using only AWS APIs
    """
    try:
        # Look for EC2 instances with Karpenter tags/labels
        filters = [
            {'Name': 'tag:eks:cluster-name', 'Values': [cluster_name]},
            {'Name': 'tag:karpenter.sh/provisioner-name', 'Values': ['*']}
        ]
        
        try:
            karpenter_instances = ec2_client.describe_instances(Filters=filters)
            karpenter_detected = len(karpenter_instances.get('Reservations', [])) > 0
        except ClientError:
            karpenter_detected = False
            
        # Check for Karpenter add-on with improved version detection
        karpenter_addon = False
        karpenter_version = "unknown"
        
        # Check EKS add-ons for Karpenter
        for addon in addons:
            addon_name = addon.get('addonName', '').lower()
            if 'karpenter' in addon_name:
                karpenter_addon = True
                karpenter_version = addon.get('addonVersion', 'unknown')
                break
                
        # Check for Karpenter-specific IAM roles
        iam_client = boto3.client('iam')
        try:
            # Look for roles with Karpenter in the name or path
            roles = iam_client.list_roles(PathPrefix='/')
            for role in roles.get('Roles', []):
                if 'karpenter' in role['RoleName'].lower():
                    karpenter_detected = True
                    break
        except ClientError as e:
            logger.warning(f"Could not check IAM roles for Karpenter: {e}")
            
        # Check for Karpenter-specific security groups
        try:
            sg_filters = [
                {'Name': 'tag:eks:cluster-name', 'Values': [cluster_name]},
                {'Name': 'group-name', 'Values': ['*karpenter*']}
            ]
            security_groups = ec2_client.describe_security_groups(Filters=sg_filters)
            if security_groups.get('SecurityGroups'):
                karpenter_detected = True
        except ClientError as e:
            logger.warning(f"Could not check security groups for Karpenter: {e}")
            
        # Get provisioned node information
        provisioned_nodes = 0
        instance_types = set()
        
        if karpenter_detected:
            # Get more details about Karpenter-provisioned instances
            for reservation in karpenter_instances.get('Reservations', []):
                for instance in reservation.get('Instances', []):
                    if instance.get('State', {}).get('Name') == 'running':
                        provisioned_nodes += 1
                        instance_types.add(instance.get('InstanceType', 'unknown'))
        
        return {
            'detected': karpenter_detected or karpenter_addon,
            'provisioned_nodes': provisioned_nodes,
            'addon_installed': karpenter_addon,
            'version': karpenter_version,
            'instance_types': list(instance_types),
            'detection_method': 'aws_api'
        }
    except Exception as e:
        logger.error(f"Error getting Karpenter data: {e}")
        return {
            'detected': False,
            'error': str(e)
        }

def get_eks_auto_mode_data(cluster_details, node_groups, ec2_client, cluster_name):
    """
    Determine if the cluster is using EKS Auto Mode with improved checks
    """
    try:
        # EKS Auto Mode indicators:
        # 1. No managed node groups
        # 2. No self-managed node groups
        # 3. Nodes exist in the cluster
        # 4. Karpenter is detected
        
        # Check if there are any managed node groups
        has_managed_node_groups = len(node_groups) > 0
        
        # Check if there are any self-managed node groups
        # This is a more targeted approach than converting the entire object to a string
        has_self_managed_nodes = False
        if cluster_details.get('nodeGroups') or cluster_details.get('selfManagedNodeGroups'):
            has_self_managed_nodes = True
            
        # Also check for specific fields that indicate self-managed nodes
        if cluster_details.get('resources', {}).get('autoScalingGroups'):
            for asg in cluster_details.get('resources', {}).get('autoScalingGroups', []):
                if asg.get('instanceType'):
                    has_self_managed_nodes = True
                    break
        
        # Check if there are nodes in the cluster
        has_nodes = cluster_details.get('status') == 'ACTIVE'
        
        # Check for EKS Auto Mode specific tags on nodes
        auto_mode_tags_detected = False
        auto_mode_instance_count = 0
        auto_scaling_groups = set()
        
        try:
            # Get instances with the cluster tag
            filters = [{'Name': 'tag:eks:cluster-name', 'Values': [cluster_name]}]
            response = ec2_client.describe_instances(Filters=filters)
            
            # Check for EKS Auto Mode specific tags and patterns
            for reservation in response.get('Reservations', []):
                for instance in reservation.get('Instances', []):
                    tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
                    
                    # Look for tags that indicate EKS Auto Mode
                    if 'eks:auto-mode' in tags or 'eks:auto-scaling-group' in tags:
                        auto_mode_tags_detected = True
                        auto_mode_instance_count += 1
                    
                    # Check for auto-scaling group tags
                    asg_name = tags.get('aws:autoscaling:groupName')
                    if asg_name:
                        auto_scaling_groups.add(asg_name)
                        
                    # Check for node naming patterns that suggest Auto Mode
                    if instance.get('PrivateDnsName', '').startswith('eks-auto-'):
                        auto_mode_tags_detected = True
                        auto_mode_instance_count += 1
        except Exception as e:
            logger.warning(f"Could not check for EKS Auto Mode tags: {e}")
        
        # Check CloudFormation stacks for EKS Auto Mode resources
        try:
            cfn_client = boto3.client('cloudformation')
            stacks = cfn_client.list_stacks(StackStatusFilter=['CREATE_COMPLETE', 'UPDATE_COMPLETE'])
            
            for stack in stacks.get('StackSummaries', []):
                if 'eks-auto-mode' in stack.get('StackName', '').lower():
                    auto_mode_tags_detected = True
                    break
        except Exception as e:
            logger.warning(f"Could not check CloudFormation stacks: {e}")
        
        # Determine if EKS Auto Mode is likely being used based on multiple indicators
        likely_auto_mode = (has_nodes and not has_managed_node_groups and not has_self_managed_nodes) or auto_mode_tags_detected
        
        return {
            'likely_enabled': likely_auto_mode,
            'managed_node_groups': has_managed_node_groups,
            'self_managed_nodes': has_self_managed_nodes,
            'auto_mode_tags_detected': auto_mode_tags_detected,
            'auto_mode_instance_count': auto_mode_instance_count,
            'auto_scaling_groups': list(auto_scaling_groups),
            'detection_confidence': 'high' if auto_mode_tags_detected else 'medium' if likely_auto_mode else 'low'
        }
    except Exception as e:
        logger.error(f"Error determining EKS Auto Mode: {e}")
        return {
            'likely_enabled': False,
            'error': str(e)
        }