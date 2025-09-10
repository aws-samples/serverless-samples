# API Expert Agent

A serverless AI agent built with the Strands framework that provides expert guidance on Amazon API Gateway development, best practices, and troubleshooting by leveraging a comprehensive knowledge base.

## Features

- **Knowledge Base Integration**: Retrieves relevant information from a curated knowledge base of API Gateway documentation and best practices
- **AI-Powered Responses**: Uses Amazon Bedrock (Nova Pro) to provide intelligent, contextual answers
- **Expert Guidance**: Covers API Gateway configuration, security, performance optimization, and troubleshooting
- **Real-time Retrieval**: Dynamically searches knowledge base content based on user queries
- **Confidence Scoring**: Filters responses based on relevance scores to ensure quality answers

## Architecture

The agent consists of:
- **AWS Lambda**: Serverless function (Python 3.13) for processing queries
- **Strands Framework**: Agent orchestration with knowledge base retrieval tools
- **Amazon Bedrock**: AI model for intelligent response generation (Nova Pro)
- **Amazon Bedrock Knowledge Base**: Centralized repository of API Gateway expertise

## Prerequisites

1. **Knowledge Base Stack**: Deploy the knowledge base stack first (default: `api-expert-kb`)
2. **AWS SAM CLI**: Install the [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
3. **Python 3.13**: Required runtime for the Lambda function
4. **Bedrock Model Access**: Ensure you have access to the `amazon.nova-pro-v1:0` model in Amazon Bedrock

## Deployment

### 1. Deploy Knowledge Base (if not already deployed)

Ensure you have deployed the knowledge base stack first. The agent depends on it for retrieving API Gateway expertise.

### 2. Build the application

```bash
sam build
```

### 3. Deploy the application

```bash
sam deploy --guided --capabilities CAPABILITY_IAM
```

Configuration parameters:
- **Stack Name**: Your preferred stack name
- **AWS Region**: Target deployment region
- **KnowledgeBaseStackName**: Name of existing knowledge base stack (default: `api-expert-kb`)
- **BedrockModel**: Bedrock model ID (default: `amazon.nova-pro-v1:0`)

### 4. Subsequent deployments

```bash
sam build && sam deploy
```

## Usage

The agent provides expert guidance on API Gateway topics by searching the knowledge base and generating intelligent responses.

### Direct Lambda Invocation

```bash
aws lambda invoke \
  --function-name <function-name> \
  --payload '{"request": "How do I implement rate limiting in API Gateway?"}' \
  response.json
```

### Example Queries

1. **Configuration Questions**:
   ```json
   {
     "request": "What are the best practices for API Gateway caching?"
   }
   ```

2. **Security Guidance**:
   ```json
   {
     "request": "How do I secure my API Gateway endpoints with Lambda authorizers?"
   }
   ```

3. **Performance Optimization**:
   ```json
   {
     "request": "What are the throttling limits for API Gateway and how can I optimize performance?"
   }
   ```

4. **Troubleshooting**:
   ```json
   {
     "request": "My API Gateway is returning 502 errors. What could be the cause?"
   }
   ```

## Configuration

### Environment Variables

- `BEDROCK_MODEL`: Bedrock model ID for AI-powered responses
- `KNOWLEDGE_BASE_ID`: Knowledge base ID (imported from knowledge base stack)
- `MIN_SCORE`: Minimum confidence score for knowledge base retrieval (default: 0.4)

### Dependencies

- `strands-agents`: Core agent framework
- `strands-agents-tools`: Knowledge base retrieval tools

### IAM Permissions

The Lambda function requires:
- **Bedrock**: Model invocation and knowledge base retrieval
- **CloudWatch**: Log creation and writing

## Knowledge Base Integration

The agent uses the `retrieve` tool from strands-agents-tools to:
- Search the knowledge base for relevant content based on user queries
- Filter results using confidence scoring (MIN_SCORE threshold)
- Provide contextual information to the AI model for generating responses
- Ensure answers are grounded in authoritative API Gateway documentation

## Response Quality

- **Confidence Filtering**: Only uses knowledge base content above the minimum score threshold
- **Contextual Answers**: Combines retrieved knowledge with AI reasoning
- **Source Grounding**: Responses are based on curated API Gateway expertise
- **Real-time Retrieval**: Searches knowledge base dynamically for each query

## Monitoring

- **CloudWatch Logs**: Detailed execution logs with query and retrieval information
- **CloudWatch Metrics**: Standard Lambda metrics plus custom agent metrics
- **Knowledge Base Analytics**: Track retrieval success rates and confidence scores

## Cleanup

```bash
sam delete
```

## Troubleshooting

### Common Issues

1. **Model Access**: Ensure you have access to the `amazon.nova-pro-v1:0` model in Bedrock
2. **Knowledge Base**: Verify the knowledge base stack exists and exports `KnowledgeBaseId`
3. **Low Quality Responses**: Adjust `MIN_SCORE` if responses lack relevance
4. **Empty Responses**: Check if knowledge base contains relevant content for the query

### Debugging

Check CloudWatch Logs for:
- Knowledge base retrieval results and scores
- Agent initialization and tool loading
- Error messages and stack traces

