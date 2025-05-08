# API Gateway Account Inspector Lambda Function

This Lambda function collects and returns detailed information about AWS API Gateway account settings and resources. It can be used as a standalone Lambda function or integrated with Amazon Q API Expert Agent.

## Project Overview

The API Gateway Account Inspector retrieves comprehensive information about an AWS account's API Gateway configuration, including account settings, VPC links, custom domains, API keys, usage plans, client certificates, and service quotas. This information can be used for auditing, documentation, or analysis purposes.

## Directory Structure

```
api-account-inspector/
├── lambda_function.py    # Lambda function handler
├── requirements.txt      # Python dependencies
└── template.yaml         # AWS SAM template
```

## Prerequisites

- [Python](https://www.python.org/) (v3.9 or later)
- [AWS CLI](https://aws.amazon.com/cli/) configured with appropriate credentials
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)

## Setup and Installation

1. Clone this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Deployment with AWS SAM

1. Build the application:

```bash
sam build
```

2. Deploy the application:

```bash
sam deploy --guided
```

Follow the prompts to configure your deployment. For subsequent deployments, you can use:

```bash
sam deploy
```

### Deployment Parameters

- **Stack Name**: Name for your CloudFormation stack
- **AWS Region**: Region to deploy to
- **Confirm changes before deploy**: Recommended to set to "Yes" for production deployments
- **Allow SAM CLI IAM role creation**: Set to "Yes" if you want SAM to create IAM roles
- **Disable rollback**: Set to "No" for production deployments

## Usage

The function accepts requests with the following structure:

```json
{
  "parameters": [],
  "actionGroup": "APIAccountInspector",
  "function": "inspectAccount",
  "sessionAttributes": {},
  "promptSessionAttributes": {}
}
```

### Response Format

```json
{
  "messageVersion": "1.0",
  "response": {
    "actionGroup": "APIAccountInspector",
    "function": "inspectAccount",
    "functionResponse": {
      "responseBody": {
        "TEXT": {
          "body": "{\"accountSettings\":{...},\"vpcLinks\":[...],\"customDomains\":[...],\"apiKeysCount\":0,\"usagePlansCount\":0,\"clientCertificatesCount\":0,\"apigwQuotas\":[...]}"
        }
      }
    },
    "sessionAttributes": {},
    "promptSessionAttributes": {}
  }
}
```

## Integration with Amazon Q API Expert Agent

This Lambda function can be integrated with Amazon Q API Expert Agent to provide API Gateway account inspection capabilities. To integrate:

1. Deploy this Lambda function using the SAM template
2. Configure the Amazon Q API Expert Agent to use this function as a tool

## Required IAM Permissions

The Lambda function requires the following minimum IAM permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "apigateway:GET",
        "apigateway:Get*",
        "wafv2:GetWebACL",
        "wafv2:ListWebACLs",
        "wafv2:GetWebACLForResource",
        "wafv2:ListResourcesForWebACL",
        "servicequotas:ListServiceQuotas"
      ],
      "Resource": "*"
    }
  ]
}
```

## Information Collected

The function collects the following information:

- API Gateway account settings
- VPC links configuration
- Custom domain names and base path mappings
- API keys count
- Usage plans count
- Client certificates count
- API Gateway service quotas

## Error Handling

If an error occurs during account inspection, the function will return an appropriate error message in the response body.

## Cleanup

To remove all resources created by this SAM application:

```bash
sam delete
```
