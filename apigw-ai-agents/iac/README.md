# Bedrock CloudFormation Stacks

This repository contains CloudFormation templates for deploying a suite of Amazon Bedrock Agents:
- API Builder Agent
- API Expert Agent
- API Inspector Agent
- API OpenAPI Generator Agent
- API Requirements Gatherer Agent

It also includes a Bedrock Knowledge Base and Flow stack templates.

## Prerequisites

Before deploying this stack, you need to have the following stack deployed:

1. A CloudFormation stack that creates and exports a Bedrock Knowledge Base ID 
2. A CloudFormation stack that creates and exports AWS Lambda function ARNs for the agent tools 

## Agent Templates

Each agent template creates:

1. An IAM role for the Bedrock agent
2. A Bedrock agent with specific instructions and capabilities
3. An agent alias for deployment
4. Integration with Lambda function tools from the tools stack (if needed)
5. Integration with Knowledge Base function tools from the tools stack (if needed)

## Deployment

### Knowledge Base
Before deploying Amazon Bedrock Knowledge Base, you will need content in an Amazon S3 bucket that will be indexed during the deployment process. Create S3 bucket in the same AWS region you are deploying rest of your resources, upload data in the [formats supported](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-ds.html), you will need it during the deployment.

To deploy Knowledge Base for the API Expert agent use following command:
```bash
aws cloudformation deploy --template-file ./bedrock-kb-aos.yaml --stack-name api-expert-kb --capabilities CAPABILITY_IAM --parameter-overrides ExistingS3BucketName=<your-expert-s3-bucket-name-here>
```

By default, the Knowledge Base includes both your S3 documents and publicly available AWS documentation (API Gateway documentation, white papers, etc.). You can control whether to include the public documentation by using the `IncludePublicDocs` parameter:

```bash
aws cloudformation deploy --template-file ./bedrock-kb-aos.yaml --stack-name api-expert-kb --capabilities CAPABILITY_IAM --parameter-overrides ExistingS3BucketName=<your-expert-s3-bucket-name-here> IncludePublicDocs=false
```

The template uses a conditional resource creation pattern:
1. When `IncludePublicDocs` is set to "true" (default), both S3 and public documentation data sources are created
2. When `IncludePublicDocs` is set to "false", only the S3 data source is created
3. The ingestion job automatically adapts to include only the data sources that were created

*Note: You may implement a scheduled task to re-synchronize data sources on a regular basis to keep those public documents in the knowledge base up to date.*

### API Builder Agent
Creates an agent specialized in building APIs with Infrastructure as Code templates and business logic examples.

To deploy this agent:

```bash
aws cloudformation create-stack \
  --stack-name api-builder-agent \
  --template-body file://api-builder-agent.yaml \
  --capabilities CAPABILITY_IAM
```

### API Expert Agent
Creates an agent that can answer technical questions on API planning, development, testing, security, management, and governance.

To deploy this agent:

```bash
aws cloudformation create-stack \
  --stack-name api-expert-agent \
  --template-body file://api-expert-agent.yaml \
  --parameters ParameterKey=KnowledgeBaseStackName,ParameterValue=api-expert-kb \
  --capabilities CAPABILITY_IAM
```

### API Inspector Agent
Creates an agent that can analyze and provide feedback on API designs and implementations.

The API Inspector Agent can optionally use a Knowledge Base that includes internal best practices, style guides, requirements, etc. The Knowledge Base integration is conditional based on the `KnowledgeBaseStackName` parameter:

- If set to `None` (default), the agent will not use a Knowledge Base
- If set to a valid stack name, the agent will import the Knowledge Base ID from that stack

To create a Knowledge Base for the Inspector agent:

```bash
aws cloudformation deploy --template-file ./bedrock-kb-aos.yaml --stack-name api-inspector-kb --capabilities CAPABILITY_IAM --parameter-overrides ExistingS3BucketName=<your-inspector-s3-bucket-name-here> IncludePublicDocs=false
```
*Note: You can use the same Knowledge Base as the Expert agent if desired, though recommendations may be less organization-specific.*

To deploy this agent without a Knowledge Base:

```bash
aws cloudformation create-stack \
  --stack-name api-inspector-agent \
  --template-body file://api-inspector-agent.yaml \
  --parameters ParameterKey=ToolsStackName,ParameterValue=api-agent-tools \
  --capabilities CAPABILITY_IAM
```

To deploy this agent with a Knowledge Base:

```bash
aws cloudformation create-stack \
  --stack-name api-inspector-agent \
  --template-body file://api-inspector-agent.yaml \
  --parameters ParameterKey=ToolsStackName,ParameterValue=api-agent-tools \
    ParameterKey=KnowledgeBaseStackName,ParameterValue=api-inspector-kb \
  --capabilities CAPABILITY_IAM
```

### API OpenAPI Generator Agent
Creates an agent that can generate OpenAPI specifications based on requirements.

To deploy this agent:

```bash
aws cloudformation create-stack \
  --stack-name api-openapi-generator-agent \
  --template-body file://api-openapi-generator-agent.yaml \
  --parameters ParameterKey=ToolsStackName,ParameterValue=api-agent-tools \
  --capabilities CAPABILITY_IAM
```

### API Requirements Gatherer Agent
Creates an agent that helps gather and refine API requirements.

To deploy this agent:

```bash
aws cloudformation create-stack \
  --stack-name api-requirements-gatherer-agent \
  --template-body file://api-requirements-gatherer-agent.yaml \
  --capabilities CAPABILITY_IAM
```

### Bedrock Flow
Creates a Bedrock Flow with multiple agents collaborating. Uses knowledge base and agents deployed in the previous steps.

To deploy this flow:

```bash
aws cloudformation create-stack \
  --stack-name api-expert-flow \
  --template-body file://bedrock-flow.yaml \
  --parameters ParameterKey=KnowledgeBaseStackName,ParameterValue=api-expert-kb \
    ParameterKey=RequirementsGathererAgentStackName,ParameterValue=api-requirements-gatherer-agent \
    ParameterKey=APIInspectorAgentStackName,ParameterValue=api-inspector-agent \
    ParameterKey=APIBuilderAgentStackName,ParameterValue=api-builder-agent \
  --capabilities CAPABILITY_IAM
```