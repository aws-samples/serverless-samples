# javascript-appsync-sam
This is implementation of the backend GraphQL API using Node.js and AWS Serverless Application Model (AWS SAM). AWS SAM had been chosen for future extensibility and ease of development of Serverless resources, such as Lambda Resolvers or Lambda Authorizers. 

## Project structure
This project contains source code and supporting files for a serverless application that you can deploy with the AWS SAM command line interface (CLI). It includes the following files and folders:

- `template.yaml` - A template that defines the application's AWS resources.
- `pipeline.yaml` - A template that defines the application's CI/CD pipeline.
- `buildspec.yml` - A template that defines the application's build process.
- `src\resolvers`- AWS AppSync [JavaScript resolvers' code](https://docs.aws.amazon.com/appsync/latest/devguide/resolver-reference-overview-js.html)
- `__tests__/integration` - Integration tests for the API. 
- `__tests__/unit` - Unit tests for the API. 
- `__tests__/testspec.yml` - A template that defines the API's test process.

The application uses shared Amazon Cognito stack for authentication/authorization. You will need to create this stack and update `template.yaml` parameters section with the stack name. See next section for details
## Amazon Cognito setup
This example uses shared stack that deploys Amazon Cognito resources. The shared stack will be deployed automatically if you use CI/CD pipeline. See [README.md](../shared/README.md) in shared resources directory for the stack manual deployment instructions. After manual deployment is finished make sure to update your AWS SAM template file `template.yaml` parameter CognitoStackName with the shared Amazon Cognito stack name. 

After stack is created manually you will need to create user account for authentication/authorization. Deployment by CI/CD pipeline will perform following steps for you automatically. 

- Navigate to URL specified in the shared stack template outputs as CognitoLoginURL and click link "Sign Up". After filling in new user registration form you should receive email with verification code, use it to confirm your account. 

- After this first step step your new user account will be able to access public data and create new bookings. To add locations and resources you will need to navigate to AWS Console, pick Amazon Cognito service, select User Pool instance that was created during this deployment, navigate to "Users and Groups", and add your user to administrative users group. 

- As an alternative to the AWS Console you can use AWS CLI to create and confirm user signup:
```bash
    aws cognito-idp sign-up --client-id <cognito user pool application client id> --username <username> --password <password> --user-attributes Name="name",Value="<username>"
    aws cognito-idp admin-confirm-sign-up --user-pool-id <cognito user pool id> --username <username> 
```

While using command line or third party tools such as Postman to test APIs, you will need to provide Access Token in the request "Authorization" header. You can authenticate with Amazon Cognito User Pool using AWS CLI (this command is also available in AWS SAM template outputs) and use IdToken value present in the output of the command:

```bash
aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH --client-id <cognito user pool application client id> --auth-parameters USERNAME=<username>,PASSWORD=<password>
```

## Manually deploy the sample application
***Note:** Before deploying application manually first time you will need to deploy shared Amazon Cognito stack, see previous section for details.*

To build and deploy your application for the first time, run the following in your shell:

```bash
npm install
sam build
sam deploy --guided --stack-name javascript-appsync-sam
```

The first command will build the source of your application. The second command will package and deploy your application to AWS, with a series of prompts:

* **Stack Name**: The name of the stack to deploy to AWS CloudFormation. This should be unique to your account and region, and a good starting point would be something matching your project name.
* **AWS Region**: The AWS region you want to deploy your app to.
* **Parameter CognitoStackName**: The shared Amazon Cognito stack name 
* **Confirm changes before deploy**: If set to yes, any change sets will be shown to you before execution for manual review. If set to no, the AWS SAM CLI will automatically deploy application changes.
* **Allow AWS SAM CLI IAM role creation**: Many AWS SAM templates, including this example, create AWS IAM roles required for the AWS Lambda function(s) included to access AWS services. By default, these are scoped down to minimum required permissions. To deploy an CloudFormation stack which creates or modifies IAM roles, the `CAPABILITY_IAM` value for `capabilities` must be provided. If permission isn't provided through this prompt, to deploy this example you must explicitly pass `--capabilities CAPABILITY_IAM` to the `sam deploy` command.
* **Save arguments to samconfig.toml**: If set to yes, your choices will be saved to a configuration file inside the project, so that in the future you can just re-run `sam deploy` without parameters to deploy changes to your application.

The AWS AppSync endpoint API will be displayed in the outputs when the deployment is complete.

## Testing
Unit tests are defined in the `__tests__\unit` folder in this project. Integration tests are defined in the `__tests__\integration` folder.

Use `npm` to install the [Jest test framework](https://jestjs.io/) and run the tests:

```bash
my-application$ npm install
```

Unit tests use AWS SDK to evaluate AWS AppSync resolver code. They use mock data, not the integrations with the backend services. Use following command to run unit tests:
```bash
npm run test:unit
```

Integration tests send GraphQL queries to the AWS AppSync endpoint and verify responses received. In addition, integration tests use WebSocket connection to the AWS AppSync for GraphQL subscriptions. You should run the test initialization script first, to create necessary accounts in Amazon Cognito and retrieve access tokens. Also make sure to cleanup after integration testing is over:

```bash
eval "$(./__tests__/integration/test_init.sh)" 
npm run test:integration
eval "$(./__tests__/integration/test_cleanup.sh)" 
```

## Deploy CI/CD pipeline for the application
To create the CI/CD pipeline we will split out code for this set of examples from the serverless-samples repository into a separate directory and use it as a codebase for our pipeline. 

First, navigate to the root directory of the repository. To verify it run command *basename "$PWD"* - it should return serverless-samples as an output. Then run the following commands:

```bash
git subtree split -P serverless-graphql-api -b serverless-graphql-api
mkdir ../serverless-graphql-api-cicd && cd ../serverless-graphql-api-cicd
git init -b main
git pull ../serverless-samples serverless-graphql-api
cd javascript-appsync-sam
```

To create the pipeline you will need to run the following command:

```bash
aws cloudformation create-stack --stack-name serverless-api-pipeline --template-body file://pipeline.yaml --capabilities CAPABILITY_IAM
```
The pipeline will attempt to run and will fail at the SourceCodeRepo stage as there is no code in the AWS CodeCommit yet.

***NOTE:** If you change stack name, avoid stack names longer than 25 characters. IUn case you need longer stack names check comments in the pipeline.yaml and update accordingly.*

***Note:** You may need to set up AWS CodeCommit repository access for HTTPS users [using Git credentials](https://docs.aws.amazon.com/codecommit/latest/userguide/setting-up-gc.html?icmpid=docs_acc_console_connect_np) and [set up the AWS CLI Credential Helper](https://docs.aws.amazon.com/console/codecommit/connect-tc-alert-np).*

Once you have access to the code repository, navigate to javascript-appsync-sam folder, and, if you changed stack name, make sure that Parameters section of template.yaml is updated with the output values from the shared Amazon Cognito stack, and push code base to CodeCommit to start automated deployments:

```bash
git remote add origin <URL to AWS CodeCommit repository>
git push origin main
```

Navigate to the AWS CodePipeline in AWS Management Console and release this change if needed by clicking "Release change" button.

![CodePipeline](./assets/CodePipeline.png)

Note that same Amazon Cognito stack is used in both testing and production deployment stages, same user credentials can be used for testing and API access.

## Cleanup

To delete the sample application that you created, use the AWS CLI:

```bash
aws cloudformation delete-stack --stack-name serverless-api
```

If you created CI/CD pipeline you will need to delete it as well, including all testing and deployment stacks created by the pipeline. Please note that actual stack names may differ in your case, depending on the pipeline stack name you used.

CI/CD pipeline stack deletion may fail if build artifact Amazon S3 bucket is not empty. In such case get bucket name using following command and looking for BuildArtifactsBucket resource's PhysicalResourceId:

```bash
aws cloudformation list-stack-resources --stack-name serverless-api-pipeline
```

Then open AWS Management Console, navigate to S3 bucket with build artifacts and empty it.

After that delete all stacks created by the CI/CD pipeline and pipeline itself:

```bash
aws cloudformation delete-stack --stack-name serverless-api-pipeline-Testing
aws cloudformation delete-stack --stack-name serverless-api-pipeline-Cognito-Testing
aws cloudformation delete-stack --stack-name serverless-api-pipeline-Deployment
aws cloudformation delete-stack --stack-name serverless-api-pipeline-Cognito-Deployment
aws cloudformation delete-stack --stack-name serverless-api-pipeline
```
