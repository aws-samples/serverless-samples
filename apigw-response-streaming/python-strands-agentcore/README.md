# API Gateway Streaming Example Agent - Strands Agents + Amazon Bedrock AgentCore

This project demonstrates how to stream responses in Amazon API Gateway using a simple AI agent hosted on Amazon Bedrock AgentCore runtime as an integration. The agent uses Strands Agents and a foundational model on Bedrock.

## Architecture

1. API Gateway receives HTTP POST requests at `/ask` endpoint
2. API Gateway sends request to an agent application hosted on Amazon Bedrock AgentCore Runtime
3. Agent code calls Amazon Bedrock Nova Lite model
4. Bedrock model processes the text and returns a streaming response
5. Agent code streams the response back through API Gateway to the client in real-time

## Prerequisites

1. **Install AgentCore CLI**

   ```bash
   pip install bedrock-agentcore-starter-toolkit
   ```

2. **Configure AWS Credentials**

   ```bash
   aws configure
   ```

## Quick Start
### Configure environment

The deployment script uses the following environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_NAME` | `api_streaming_sample_agent` | Name of the agent |
| `ENTRYPOINT` | `src/agent.py` | Python file containing agent code |
| `PYTHON_RUNTIME` | `PYTHON_3_13` | Python runtime version |
| `AWS_REGION` | `us-east-1` | AWS region for deployment |

Create `.env` file and update it as needed:

```bash
cp env.example .env
```

### Setup OAuth Identity 

The following script sets up AgentCore Identity using an Amazon Cognito user pool. You can use other identity providers; see [documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity-idps.html) for more details.

The API Gateway in this example does not have a Cognito authorizer configured and passes the authorization header value to the AgentCore runtime. Enable the Cognito Authorizer in API Gateway to reject unauthorized requests instead of passing them through. See [documentation](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-integrate-with-cognito.html) for more details on Cognito Authorizer.

**Note** API Gateway Cognito Authorizer expects an identity token unless the OAuth Scopes option isn't specified, while AgentCore uses an access token. Use the resource server and specify OAuth scopes to use the access token for method authorization in API Gateway.

```bash
./idenity_setup.sh
```

_Note: You may see an error message that workload identity already existis if you run this script more than once, ignore the error message._

### Deploy the agent to the Bedrock AgentCore runtime and create an API Gateway endpoint

The deployment script performs the following actions:
 - configures the Bedrok AgentCore runtime
 - deploys agent code
 - creates an IAM policy that allows the agent to invoke foundation models and attaches it to the agent execution role (you can modify this policy to include additional resources and actions based on your agent logic)
 - creates an API Gateway REST API and deploys it to stage `prod`

```bash
./deploy.sh
```

Note API endpoint and API Gateway ID values in the script output; you will need them for testing

### Test
#### Get access token:

```bash
export $(grep -v '^#' .agentcore_identity_user.env | xargs)
export TOKEN=$(agentcore identity get-cognito-inbound-token )
```

#### Test the agent

```bash
agentcore invoke '{"prompt": "Explain quantum computing in simple terms"}' --bearer-token "$TOKEN"
```

#### Test the API

```bash
curl -v -X POST "<API endpoint value in the deployment scripot outputs>" \
-H "Authorization: Bearer ${TOKEN}" \
-d '{"prompt": "Explain quantum computing in simple terms"}'
```

## Cleanup
### Delete API Gateway

```bash
aws apigateway delete-rest-api --rest-api-id <API Gateway ID>
rm api-gateway-config.yaml
```

### Destroy Agent

```bash
agentcore identity cleanup
agentcore destroy
rm .env
```

Check if the Amazon Bedrock Identity Outbound Auth, Amazon Cognito AgentCore Identity Pool and AgentCore Resource Pool have been deleted, clean up manually if needed.

## Additional Resources

- [Strands Framework Documentation](https://github.com/strands-agents)
- [Amazon Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html)
- [AgentCore CLI Reference](https://pypi.org/project/bedrock-agentcore-starter-toolkit/)





