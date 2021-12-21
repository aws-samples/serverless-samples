# javascript-ecs-nlb-sam
This is implementation of the backend API using AWS API Gateway HTTP endpoint, Node.js and AWS SAM. 

## Project structure
This project contains source code and supporting files for a serverless application that you can deploy with the AWS Serverless Application Model (AWS SAM) command line interface (CLI). It includes the following files and folders:

- `src/api` - Code for the application's containers
- `src/api/bookings` - Application code for the Bookings Service
- `src/api/bookings/__tests__` - Unit tests for the Bookings Service
- `src/api/locations` - Application code for the Locations Service
- `src/api/locations/__tests__` - Unit tests for the Locations Service
- `src/api/resources` - Application code for the Resources Service
- `src/api/resources/__tests__` - Unit tests for the Resources Service
- `__tests__/integration` - Integration tests for the API. 
- `__tests__/testspec.yml` - A template that defines the API's test process used by the CI/CD pipeline (both unit and integration testing).
- `template.yaml` - A template that defines the application's AWS resources.
- `pipeline.yaml` - A template that defines the application's CI/CD pipeline.
- `buildspec.yml` - A template that defines the application's build process used by the CI/CD pipeline.

The application uses shared Amazon Cognito stack for authentication/authorization and a VPC stack for ECS networking. These stacks are included as nested stacks within `template.yaml`. 

## Deploying with CI/CD pipeline
You will use the CloudFormation CLI to deploy the stack defined within `pipeline.yaml`. This will deploy the required foundation which will allow you to make changes to your application and deploy them in a CI/CD fashion. 
    The following resources will be created:
        - CodeCommit repository for application code source control
        - Elastic Container Registry repositories for housing the application's container images
        - CodeBuild project for building and testing the application
        - CodePipeline for orchestrating the CI/CD process

To create the CI/CD pipeline we will split out code for this set of examples from the serverless-samples repository into a separate directory and use it as a codebase for our pipeline. 

First, navigate to the root directory of the repository. To verify it run command *basename "$PWD"* - it should return serverless-samples as an output. Then run the following commands:

```bash
git subtree split -P fargate-rest-api -b fargate-rest-api
mkdir ../fargate-rest-api-cicd && cd ../fargate-rest-api-cicd
git init -b main
git pull ../serverless-samples fargate-rest-api
cd javascript-rest-ecs-sam
```

To create the pipeline you will need to run the following command:

```bash

# Let's save our stack name so we can use it in other commands
export STACK_NAME=fargate-rest-api-pipeline

aws cloudformation deploy --stack-name $STACK_NAME --template-file ./pipeline.yaml --capabilities CAPABILITY_IAM
```

Once the stack is created, the pipeline will attempt to run and will fail at the SourceCodeRepo stage as there is no code in the AWS CodeCommit yet.

***NOTE:** If you change stack name, avoid stack names longer than 25 characters. IUn case you need longer stack names check comments in the pipeline.yaml and update accordingly.*

***Note:** You may need to set up AWS CodeCommit repository access for HTTPS users [using Git credentials](https://docs.aws.amazon.com/codecommit/latest/userguide/setting-up-gc.html?icmpid=docs_acc_console_connect_np) and [set up the AWS CLI Credential Helper](https://docs.aws.amazon.com/console/codecommit/connect-tc-alert-np).*

To view the CodeCommit URLs, run the following:
```bash
aws cloudformation describe-stacks --stack-name $STACK_NAME | jq -r '.Stacks[0].Outputs[] | select(.OutputKey == "CodeCommitRepositoryHttpUrl" or .OutputKey == "CodeCommitRepositorySshUrl")'
```

Copy the desired URL (i.e. HTTPS, SSH) and run the following command:

```bash
git remote add origin <URL to AWS CodeCommit repository>
git push origin main
```

This will trigger a new deployment in CodePipeline. Navigate to the CodePipeline in AWS Management Console to see the process and status. You can also release changes manually by clicking the "Release change" button.

![CodePipeline](./assets/CodePipeline.png)

## Amazon Cognito setup
Amazon Cognito is automatically deployed with the application as part of the CI/CD pipeline. A distinct user pool is used for each of the Testing and Production environments.

After the application is deployed, you will need to create user account for authentication/authorization:

- Navigate to URL specified in the shared stack template outputs as CognitoLoginURL and click link "Sign Up". After filling in new user registration form you should receive email with verification code, use it to confirm your account. 

- After this first step step your new user account will be able to access public data and create new bookings. To add locations and resources you will need to navigate to AWS Console, pick Amazon Cognito service, select User Pool instance that was created during this deployment, navigate to "Users and Groups", and add your user to administrative users group. 

- As an alternative to the AWS Console you can use AWS CLI to create and confirm user signup:
```bash
    aws cognito-idp sign-up --client-id <cognito user pool application client id> --username <username> --password <password> --user-attributes Name="name",Value="<username>"
    aws cognito-idp admin-confirm-sign-up --user-pool-id <cognito user pool id> --username <username> 
```

While using command line or third party tools such as Postman to test APIs, you will need to provide Identity Token in the request "Authorization" header. You can authenticate with Amazon Cognito User Pool using AWS CLI (this command is also available in SAM template outputs) and use IdToken value present in the output of the command:

```bash
aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH --client-id <cognito user pool application client id> --auth-parameters USERNAME=<username>,PASSWORD=<password>
```

## Unit tests
Unit tests are defined in the `__tests__` folder iwithin each service (i.e. `src/api/locations`). Use `npm` to install the [Jest test framework](https://jestjs.io/) and run unit tests.

```bash
npm install
npm run test:unit
```

## Cleanup

To delete the sample application that you created, use the AWS CLI:

```bash
# Delete the application stacks
aws cloudformation delete-stack --stack-name fargate-rest-api-pipeline-Testing
aws cloudformation delete-stack --stack-name fargate-rest-api-pipeline-Deployment

# Wait for the deletions to complete before deleting the pipeline stacks
aws cloudformation wait stack-delete-complete --stack-name fargate-rest-api-pipeline-Testing
aws cloudformation wait stack-delete-complete --stack-name fargate-rest-api-pipeline-Deployment

# Delete/empty ECR repositories and S3 buckets
pipelineStackOutputs=$(aws cloudformation describe-stacks --stack-name $STACK_NAME | jq -r '.Stacks[0].Outputs')
bookingsRepositoryName=$(echo "$pipelineStackOutputs" | jq -r '.[] | select(.OutputKey == "BookingsServiceRepositoryName") | .OutputValue')
locationsRepositoryName=$(echo "$pipelineStackOutputs" | jq -r '.[] | select(.OutputKey == "LocationsServiceRepositoryName") | .OutputValue')
resourcesRepositoryName=$(echo "$pipelineStackOutputs" | jq -r '.[] | select(.OutputKey == "ResourcesServiceRepositoryName") | .OutputValue')

aws ecr delete-repository --repository-name $bookingsRepositoryName --force
aws ecr delete-repository --repository-name $locationsRepositoryName --force
aws ecr delete-repository --repository-name $resourcesRepositoryName --force

artifactBucketName=$(echo "$pipelineStackOutputs" | jq -r '.[] | select(.OutputKey == "BuildArtifactS3Bucket") | .OutputValue')

aws s3 rm s3://$artifactBucketName --recursive

# Delete pipeline stack
aws cloudformation delete-stack --stack-name $STACK_NAME
aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME
```