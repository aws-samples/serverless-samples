# API Gateway Inspector Lambda Function

This Lambda function collects and returns detailed information about AWS API Gateway REST APIs. It can be used as a standalone Lambda function or integrated with Amazon Q API Expert Agent.

## Project Overview

The API Gateway Inspector retrieves comprehensive information about a specified API Gateway REST API, including resources, stages, authorizers, WAF configurations, models, integrations, and more. This information can be used for auditing, documentation, or analysis purposes.

## Directory Structure

```
api-inspector/
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
  "parameters": [
    {
      "value": "your-api-gateway-id"
    }
  ],
  "actionGroup": "APIGatewayInspector",
  "function": "inspectAPI",
  "sessionAttributes": {},
  "promptSessionAttributes": {}
}
```

### Response Format

```json
{
  "messageVersion": "1.0",
  "response": {
    "actionGroup": "APIGatewayInspector",
    "function": "inspectAPI",
    "functionResponse": {
      "responseBody": {
        "TEXT": {
          "body": "{\"api\":{...},\"stages\":[...],\"resources\":[...],\"wafConfiguration\":{...},\"models\":[...],\"integrations\":{...}}"
        }
      }
    },
    "sessionAttributes": {},
    "promptSessionAttributes": {}
  }
}
```

## Integration with Amazon Q API Expert Agent

This Lambda function can be integrated with Amazon Q API Expert Agent to provide API Gateway inspection capabilities. To integrate:

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

## Error Handling

If an error occurs during API inspection, the function will return an appropriate error message in the response body.


## Cleanup

To remove all resources created by this SAM application:

```bash
sam delete
```