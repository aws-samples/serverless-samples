# VTL Processor Lambda Function

This Lambda function processes API Gateway Apache Velocity Templates (VTL) against HTTP requests and responses.

## Features

- Processes VTL templates using Apache Velocity Engine 2.3
- Handles HTTP request and response formats
- Supports context and stage variables
- Processes both request and response mapping templates
- Returns processed output or detailed error messages
- Includes CORS headers for browser access
- Supports AWS service integration templates

## API

### Request Format

For request template processing:
```json
{
  "httpRequest": "POST /resource?param1=value1 HTTP/1.1\nHost: api.example.com\nContent-Type: application/json\n\n{\"message\":\"Hello\"}",
  "requestTemplate": "#set($inputRoot = $input.path('$'))\n{\n  \"data\": \"$inputRoot.message\"\n}",
  "contextVariables": {
    "context": {
      "accountId": "123456789012",
      "apiId": "api123",
      "httpMethod": "POST"
    },
    "stageVariables": {
      "environment": "dev"
    }
  },
  "processingType": "REQUEST_ONLY"
}
```

For response template processing:
```json
{
  "httpResponse": "HTTP/1.1 200 OK\nContent-Type: application/json\n\n{\"result\":\"success\"}",
  "responseTemplate": "#set($inputRoot = $input.path('$'))\n{\n  \"status\": \"$inputRoot.result\"\n}",
  "contextVariables": {
    "context": {
      "accountId": "123456789012"
    },
    "stageVariables": {
      "environment": "dev"
    }
  },
  "processingType": "RESPONSE_ONLY"
}
```

### Response Format

The response is the processed output as a string (typically JSON):

```
{"data":"Hello"}
```

Or in case of an error:

```
Error processing template: VTL syntax error at line 1, column 10: Encountered "}" at line 1, column 10.
```

## Local Testing

To test the Lambda function locally:

1. Build the project:
```bash
cd vtl-processor
mvn clean package
```

2. Start the local API using SAM CLI:
```bash
cd ..
./build-and-run.sh
```

3. Test the API with a request template:
```bash
curl -X POST http://localhost:3000/process-vtl \
  -H "Content-Type: application/json" \
  -d '{"httpRequest":"POST /resource HTTP/1.1\nContent-Type: application/json\n\n{\"message\":\"Hello\"}","requestTemplate":"#set($inputRoot = $input.path('\''$'\''))\n{\n  \"data\": \"$inputRoot.message\"\n}","contextVariables":{"context":{},"stageVariables":{}},"processingType":"REQUEST_ONLY"}'
```

