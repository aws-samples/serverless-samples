# AWS Lambda Streaming with Bedrock Model

This project demonstrates how to create an AWS Lambda function that invokes a Bedrock model and streams the responses back to the client through API Gateway.

## Architecture

1. API Gateway receives HTTP POST requests at `/ask` endpoint
2. API Gateway invokes Lambda function with streaming response mode
3. Lambda function calls Amazon Bedrock Nova Lite model
4. Bedrock model processes the text and returns a streaming response
5. Lambda function streams the response back through API Gateway to the client in real-time

## Prerequisites

- AWS CLI installed and configured
- AWS SAM CLI installed
- Node.js 18.x or later
- Access to Amazon Bedrock models

## Deployment

1. Build and deploy the application using SAM CLI:

```bash
sam build
sam deploy
```

For first-time deployment, use guided mode:

```bash
sam deploy --guided
```

## Usage

After deployment, the API will be available at the `/ask` endpoint. Send a POST request with a JSON payload containing a `message` field:

**Endpoint**: `POST /ask`

**Request Body**:
```json
{
  "message": "Your question for the Bedrock model"
}
```

**Example using curl**:
```bash
curl -X POST https://[api-id].execute-api.us-west-1.amazonaws.com/Prod/ask \
  -H "Content-Type: application/json" \
  -d '{"message": "Explain quantum computing in simple terms"}'
```

The API streams responses from Amazon Nova Lite model in real-time.


## Cleanup

To delete the deployed resources:

```bash
sam delete
```