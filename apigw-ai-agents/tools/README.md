# API Agent Tools

Collection of API-related tools for inspection, validation, and management deployed as a single AWS SAM application.

## Tools Included

- **OpenAPI Linter**: Validates OpenAPI definitions using the Spectral validator
- **API Account Inspector**: Inspects API Gateway configurations at the account level
- **API Inspector**: Inspects specific API Gateway configurations
- **API Definition Retriever**: Exports OpenAPI definitions from API Gateway

## Deployment Instructions

### Prerequisites

- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
- AWS credentials configured

### Deploy the Stack

1. Build the application:
   ```bash
   sam build 
   ```

2. Deploy the application:
   ```bash
   sam deploy --guided --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND
   ```
   
   Follow the prompts to configure your deployment:
   - Stack Name: `api-agent-tools` (or your preferred name)
   - AWS Region: Your preferred region
   - Confirm changes before deployment: `Y`
   - Allow SAM CLI to create IAM roles: `Y`
   - Save arguments to samconfig.toml: `Y`

### Subsequent Deployments

For subsequent deployments, you can simply run:
```bash
sam build && sam deploy
```

## Cleanup

To remove all resources created by this stack:

```bash
sam delete
```


