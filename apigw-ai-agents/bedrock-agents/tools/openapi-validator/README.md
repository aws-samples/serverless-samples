# OpenAPI Validator Lambda Function

This Lambda function validates OpenAPI definitions using the Spectral validator. It can be used as a standalone Lambda function or integrated with API Expert Agent.

## Project Overview

The validator uses Spectral, a popular linting tool for OpenAPI specifications, to validate OpenAPI definitions against standard rules. The function accepts input in YAML format and returns detailed validation results.

## Directory Structure

```
openapi-linter/
├── index.js              # Lambda function handler
├── package.json          # Node.js dependencies
├── package-lock.json     # Dependency lock file
└── template.yaml         # AWS SAM template
```

## Prerequisites

- [Node.js](https://nodejs.org/) (v18.x or later)
- [AWS CLI](https://aws.amazon.com/cli/) configured with appropriate credentials
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)

## Setup and Installation

1. Clone this repository
2. Install dependencies:

```bash
npm install
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
      "value": "... OpenAPI definition in YAML format ..."
    }
  ],
  "actionGroup": "OpenAPIValidator",
  "function": "validateOpenAPI",
  "sessionAttributes": {},
  "promptSessionAttributes": {}
}
```

### Response Format

```json
{
  "messageVersion": "1.0",
  "response": {
    "actionGroup": "OpenAPIValidator",
    "function": "validateOpenAPI",
    "functionResponse": {
      "responseBody": {
        "TEXT": {
          "body": "{\"validationResults\":[{\"code\":\"rule-code\",\"path\":\"path.to.issue\",\"message\":\"validation message\",\"severity\":0,\"line\":1,\"character\":1}]}"
        }
      }
    },
    "sessionAttributes": {},
    "promptSessionAttributes": {}
  }
}
```


## Error Handling

If an error occurs during validation, the function will return an appropriate error message in the response body.

## Customization

You can customize the validation rules by modifying the ruleset in `index.js`. The default ruleset is the standard OpenAPI ruleset from Spectral.

```markdown

## Cleanup

To remove all resources created by this SAM application:

```bash
sam delete
```