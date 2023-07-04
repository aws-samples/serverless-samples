# python-cdk

This is implementation of the Queue-based ingestion with API Gateway using Python and AWS CDK.

## Prerequisites

Make sure you have AWS CDK installed and bootstrapped before proceeding with the following steps. For more information on setting up CDK see [documentation](https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html)

**Install Docker** You can refer to this [installation guide](https://docs.docker.com/get-docker/)

**CDK Bootstrap**
If the AWS CDK and its prerequisites have been installed in a Python environment, the next step is to bootstrap each AWS region and account where any CDK stack will be deployed. This is a process that only needs to occur once per region per account, which means that every additional region requires bootstrapping of both accounts using `cdk bootstrap` command.
Use the cdk bootstrap command to bootstrap one or more AWS environments. In its basic form, this command bootstraps one or more specified AWS environments

```bash
cdk bootstrap aws://ACCOUNT-NUMBER-1/REGION-1
```

You can follow these reference for more information and guidance: [CDK bootstrap](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html)

## Project structure

This project contains source code and supporting files for a serverless application that you can deploy with the AWS CDK command line interface (CLI). It includes the following files and folders:

- `src\api` - Code for the application's Lambda functions and Lambda Authorizer.
- `events` - Invocation events that you can use to invoke the function.
- `tests/unit` - Unit tests for the application code.
- `tests/integration` - Integration tests for the API.
- `lib` - CDK application modules directory
- `app.py` - CDK application 'main' (entry point)
- `cdk.json` - configuration file for CDK
- `setup.py` - defines the Python package
- `requirements.txt` - Python requirements file for the CDK application

## CDK Python project setup

If virtualenv is needed, please create as and activate, you can find instructions in [Setup and Deployment](./../README.md#setup-and-deployment) section. Once virtualenv is activated, you can install the required dependencies for AWS CDK and API implementation.
**\*Note:** Please verify that current directory is <repository path>/serverless-samples/queue-based-ingestion/python-cdk

```
pip install -r requirements.txt
pip install -r ./src/api/requirements.txt
```

**Note**: Please ensure that Docker application is running.
At this point you can now synthesize the CloudFormation template for this code.

```
cdk synth
```

The cdk synth command executes your app, which causes the resources defined in it to be translated into an AWS CloudFormation template. The displayed output of cdk synth is a YAML-format template. Following, you can see the beginning of our app's output. The template is also saved in the cdk.out directory in JSON format.

## Amazon Cognito setup

This example uses AWS CDK stack that deploys Amazon Cognito resources. The stack will be deployed automatically if you use CI/CD pipeline. To deploy it manually you can use following command:

**\*Note:** Please verify that current directory is <repository path>/serverless-samples/queue-based-ingestion/python-cdk

```bash
cdk deploy apigw-queue-ingestion-cdk-cognito
```

After stack is created manually you will need to create user account for authentication/authorization. Deployment by CI/CD pipeline will perform these steps for you automatically.

- You need to create and coonfirm user signups, you can use AWS Console to complete this process.

- As an alternative to the AWS Console you can use AWS CLI to create and confirm user signup:
  Note down UserPoolClient Id from output of CDK deploy command and use that value in below commands.

```bash
    aws cognito-idp sign-up --client-id <cognito user pool application client id> --username <username> --password <password> --user-attributes Name="name",Value="<username>"

   aws cognito-idp admin-confirm-sign-up --user-pool-id <user pool id> --username <username>

```

While using command line or third party tools such as Postman to test APIs, you will need to provide Identity Token in the request "Authorization" header. You can authenticate with Amazon Cognito User Pool using AWS CLI and use IdToken value present in the output of the command:

```bash
aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH --client-id <cognito user pool application client id> --auth-parameters USERNAME=<username>,PASSWORD=<password>
```

## Manually deploy the sample application

**\*Note:**: Before deploying application manually first time you will need to deploy shared Cognito stack, see previous section for details.

To build and deploy your application for the first time, run the following in your shell:

```bash
cdk deploy apigw-queue-ingestion-cdk
```

This command will package and deploy your application to AWS

The Amazon API Gateway endpoint API will be displayed in the outputs when the deployment is complete.

**\*Note:**:API_STACK_NAME inside app.py is used to create S3 Bucket with same name,  so if error duplicate bucket name error observed during cdk deploy then please update API_STACK_NAME  variable with unique name and run cdk synth and cdk deploy commands again.


## Unit tests

Unit tests are defined in the `tests\unit` folder in this project. Use `pip` to install the `./tests/requirements.txt` and run unit tests.

```bash
pip install -r ./tests/requirements.txt
python -m pytest tests/unit -v
```

## Testing

To test end to end flow of application, use below steps

1. To test any of the APIs created via command line or third-party tools such as Postman , you will need to provide an Token (IdToken) in the "Authorization" header. You can authenticate with Amazon Cognito User Pool using AWS CLI and use IdToken value present in the output of the command (it is available in the stack outputs as well):

```bash
    aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH --client-id <cognito user pool application client id> --auth-parameters USERNAME=<username>,PASSWORD=<password>
```

2. Submit a new Job Request via API call using /submit-job-request endpoint. This API call sends message to Amazon SQS queue and triggers job process. For the API call, you need to use the IdToken generated in the previous step.<br>
   Below is a sample CURL command, in HTTP Body provide a payload specific to job process, this payload will be published to Amazon SQS queue.
   ```bash
    curl --location --request POST 'https://<API Gateway Sender API Endpoint>/submit-job-request'  -H 'Content-Type: application/json' --data-raw '< Batch process JSON Payload>' -H 'Authorization:<IdToken>'
   ```
3. Once the message is published to Amazon SQS via Amazon API Gateway endpoint, SendMessageResponse payload will be provided as part of HTTP response. Note down the MessageId attribute from response.<br>
   Sample SendMessageResponse payload

```bash
<?xml version="1.0" encoding="UTF-8"?>
<SendMessageResponse xmlns="http://queue.amazonaws.com/doc/2012-11-05/">
   <SendMessageResult>
      <MessageId>696093f8-1129-448f-849c-6e9f40e5b441</MessageId>
      <MD5OfMessageBody>1781569b4b9b7a0fbf6d8cb1cc459124</MD5OfMessageBody>
   </SendMessageResult>
   <ResponseMetadata>
      <RequestId>e08e055b-7af5-5b42-98ea-5fccfef82ae6</RequestId>
   </ResponseMetadata>
</SendMessageResponse>
```

4. Use the /job-status endpoint to check the status of a Job Request. Provide MessageId captured from above step as a url path parameter, and provide a cognito IdToken for authorization purpose.

```bash
curl --location 'https://<API Gateway Sender API Endpoint>/job-status/<messageId>' -H 'Content-Type: application/json' -H 'Authorization:<IdToken>'
```

5. Job Status API will have a JSON response with a pre-signed URL for Amazon S3 bucket to download the payload generated by Job process. The presigned URL will be populated as part of `jobProcessedPayload` attribute. <br>
   Below is sample reponse from job-status API

```bash
{"jobStatus": "complete",
"jobId": "696093f8-1129-448f-849c-6e9f40e5b441",
"jobProcessedPayload": "<Presigned URL link to payload object in S3 bucket>"}
```

6. Use curl command to download the job payload via the pre-signed URL (jobProcessedPayload).

```bash
curl '<presigned URL>' -o batch-payload-output.txt
```

## Deploy CI/CD pipeline for the application

To create the pipeline you will need to run the following command:

```bash
cdk deploy apigw-queue-ingestion-cdk-pipeline
```

The pipeline will attempt to run and will fail at the SourceCodeRepo stage as there is no code in the AWS CodeCommit yet.

**\*Note:** Please verify that current directory is <repository path>/serverless-samples/queue-based-ingestion/python-cdk

To verify it run command basename "pwd" - it should return python-cdk as an end of directory path.

**\*Note:** You may need to set up AWS CodeCommit repository access for HTTPS users [using Git credentials](https://docs.aws.amazon.com/codecommit/latest/userguide/setting-up-gc.html?icmpid=docs_acc_console_connect_np) and [set up the AWS CLI Credential Helper](https://docs.aws.amazon.com/console/codecommit/connect-tc-alert-np).

```bash
git remote rename origin upstream
git remote add origin <URL to AWS CodeCommit repository>
git push origin main
git remote rename upstream origin
```

Navigate to the AWS CodePipeline in AWS Management Console and release this change if needed by clicking "Release change" button.

![CodePipeline](../assets/CDK-cicd-pipeline.png)

Note that same Amazon Cognito stack is used in both testing and production deployment stages, same user credentials can be used for testing and API access.

## Cleanup

To delete the sample application that you created, use the AWS CLI:

```bash
cdk destroy apigw-queue-ingestion-cdk
cdk destroy apigw-queue-ingestion-cdk-cognito

```

If you created CI/CD pipeline you will need to delete it as well, including all testing and deployment stacks created by the pipeline. Please note that actual stack names may differ in your case, depending on the pipeline stack name you used.

```bash
cdk destroy apigw-queue-ingestion-cdk-pipeline/cdk-pipeline-deployment/app
cdk destroy apigw-queue-ingestion-cdk-pipeline/cdk-pipeline-deployment/Cognito
cdk destroy apigw-queue-ingestion-cdk-pipeline/cdk-pipeline-int-test/app
cdk destroy apigw-queue-ingestion-cdk-pipeline/cdk-pipeline-int-test/Cognito
cdk destroy apigw-queue-ingestion-cdk-pipeline

```
