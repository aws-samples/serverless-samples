# EKS Configuration Retriever

This Lambda function retrieves detailed configuration information for Amazon EKS clusters. It is designed to be used as a tool by Amazon Bedrock Agents to analyze EKS cluster configurations and provide recommendations based on best practices.

## Features

The function retrieves the following information about an EKS cluster:

- Cluster details (version, status, endpoint, etc.)
- Node groups configuration
- Fargate profiles
- Add-ons and their versions
- OIDC provider configuration
- IAM roles used by the cluster
- Security groups

## Usage

The function expects an event with the following format:

```json
{
  "cluster_name": "my-eks-cluster",
  "region": "us-east-1"  // Optional, defaults to Lambda's region
}
```

### Response Format

The function returns a JSON object with the following structure:

```json
{
  "statusCode": 200,
  "body": {
    "cluster": { /* Cluster details */ },
    "nodeGroups": [ /* Node group configurations */ ],
    "fargateProfiles": [ /* Fargate profile configurations */ ],
    "addons": [ /* Add-on configurations */ ],
    "oidcProvider": { /* OIDC provider details */ },
    "iamRoles": { /* IAM roles used by the cluster */ },
    "securityGroups": [ /* Security group configurations */ ]
  }
}
```

## Permissions

The function requires the following permissions:

- eks:DescribeCluster
- eks:ListNodegroups
- eks:DescribeNodegroup
- eks:ListFargateProfiles
- eks:DescribeFargateProfile
- eks:ListAddons
- eks:DescribeAddon
- ec2:DescribeSecurityGroups
- iam:GetOpenIDConnectProvider
- sts:GetCallerIdentity

## Deployment

This function is deployed as part of the API Agent Tools Stack using AWS SAM.