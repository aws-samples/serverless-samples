# API Definition Retriever Lambda Function

This Lambda function exports and retrieves OpenAPI definitions from AWS API Gateway REST APIs. It can be used as a standalone Lambda function or integrated with API Expert Agent.

## Project Overview

The API Definition Retriever exports the OpenAPI 3.0 definition of a specified API Gateway REST API, including API Gateway extensions. This allows users to obtain a complete and standardized representation of their API for documentation, analysis, or sharing purposes.

## Directory Structure

```
api-definition-retriever/
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
  "actionGroup": "APIDefinitionRetriever",
  "function": "retrieveDefinition",
  "sessionAttributes": {},
  "promptSessionAttributes": {}
}
```

### Response Format

```json
{
  "messageVersion": "1.0",
  "response": {
    "actionGroup": "APIDefinitionRetriever",
    "function": "retrieveDefinition",
    "functionResponse": {
      "responseBody": {
        "TEXT": {
          "body": "\"openapi: 3.0.1\\ninfo:\\n  title: Example API\\n  version: '1.0'\\npaths:\\n  /resource:\\n    get:\\n      responses:\\n        '200':\\n          description: OK\""
        }
      }
    },
    "sessionAttributes": {},
    "promptSessionAttributes": {}
  }
}
```

## Integration with API Expert Agent

This Lambda function can be integrated with API Expert Agent to provide API definition retrieval capabilities. To integrate:

1. Deploy this Lambda function using the SAM template
2. Configure the API Expert Agent to use this function as a tool

## Required IAM Permissions

The Lambda function requires the following minimum IAM permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "apigateway:GET"
      ],
      "Resource": "arn:aws:apigateway:*::/restapis/*"
    }
  ]
}
```

## How It Works

1. The function receives an API Gateway ID as input
2. It retrieves the first stage name for the specified API
3. It exports the OpenAPI 3.0 definition of the API with API Gateway extensions
4. The definition is returned in YAML format as a JSON-escaped string

## Error Handling

If an error occurs during API definition retrieval, the function will return an appropriate error message in the response body. Common errors include:

- API not found
- Missing API ID parameter
- Insufficient permissions

## Cleanup

To remove all resources created by this SAM application:

```bash
sam delete
```
