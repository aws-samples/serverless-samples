# Python Test Samples

This project contains automated test sample code supporting files for a serverless application. The project uses the [AWS Serverless Application Model](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html) (SAM) CLI for configuration, testing and deployment. It includes the following files and folders:

- src - Code for the application's Lambda function.
- events - Invocation events that you can use to invoke the function.
- tests - Unit and integration tests for the application code. 
- template.yaml - A template that defines the application's AWS resources.

This application contains several AWS resources, including a Lambda function and an API Gateway. These resources are defined in the `template.yaml` file in this project. You can update the template to add AWS resources through the same deployment process that updates your application code.

## Prerequesites

The Serverless Application Model Command Line Interface (SAM CLI) is an extension of the AWS CLI that adds functionality for building and testing Lambda applications. It uses Docker to run your functions in an Amazon Linux environment that matches Lambda. It can also emulate your application's build environment and API.

To use the SAM CLI, you need the following tools.

* SAM CLI - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
* [Python 3 installed](https://www.python.org/downloads/)
* Docker - [Install Docker community edition](https://hub.docker.com/search/?type=edition&offering=community)

## Using local emulators

Local emulation of AWS services may offer a convenient way to build and test cloud native applications using local resources. Local emulation can speed up the build and deploy cycle creating faster feedback loops for application developers. Local emulation has several limitations. Cloud services evolve rapidly, so local emulators are unlikely to have feature parity with their counterpart services in the cloud. Local emulators may not be able to provide an accurate representation of IAM permissions or service quotas. Local emulators do not exist for every AWS service.

SAM provides local emulation features for [AWS Lambda](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-using-invoke.html) and [Amazon API Gateway](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-using-start-api.html). AWS provides [Amazon DynamoDB Local](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html) as well as [AWS Step Functions Local](https://docs.aws.amazon.com/step-functions/latest/dg/sfn-local.html).  

Third party vendors like [LocalStack](https://docs.localstack.cloud/overview/) may provide emulation for additional AWS services. 

This project demonstrates local emulation of Lambda and API Gateway with SAM.

### Build with SAM

Build your application with the `sam build --use-container` command.

```bash
python-test-samples$ sam build --use-container
```

The SAM CLI installs dependencies defined in `src/requirements.txt`, creates a deployment package, and saves it in the `.aws-sam/build` folder.

### Working with events

Test the handler function with Lambda local emulation by invoking it with a synthetic test event. Synthetic events are JSON documents that represent the input that a Lambda function receives from the event source. A sample test event is included in the `events` folder in this project. SAM provides the capability of generating additional synthetic events from a variety of AWS services. To learn how to generate additional events run the command `sam local generate-event`. 

Generate a synthetic event.
```bash
python-test-samples$ sam local generate-event
```

### Use the SAM Lambda emulator 

The SAM CLI can emulate a Lambda function inside a Docker container deployed to your local desktop. To use this feature, invoke the function with the `sam local invoke` command passing a synthetic event. Print statements log to standard out.

```bash
python-test-samples$ sam local invoke PythonTestDemo --event events/event.json
```

### Use the SAM API Gateway emulator

The SAM CLI can also emulate your application's API. Use the `sam local start-api` to run the API locally on port 3000.

```bash
python-test-samples$ sam local start-api
python-test-samples$ curl http://localhost:3000/hello
```

The SAM CLI reads the application template to determine the API's routes and the functions that they invoke. The `Events` property on each function's definition includes the route and method for each path.

```yaml
      Events:
        HelloWorld:
          Type: Api
          Properties:
            Path: /hello
            Method: get
```

### Use a mock framework to run unit tests

Lambda functions are frequently used to call other AWS or 3rd party services. In these cases, mock frameworks are useful to simulate the response of a service when you test the function from your local desktop. Mock frameworks can speed the development process by enabling rapid feedback iterations. This project uses the [moto](http://docs.getmoto.org/en/latest/) dependency library to mock an external service call to Amazon S3. The `moto` library can simulate responses from [a variety of AWS services](http://docs.getmoto.org/en/latest/docs/services/index.html). 

Our mock tests test the internal logic of our Lambda function. Tests using mocks are defined in the `tests/unit` folder. Use `pip` to install test dependencies and `pytest` to run the unit test.

```bash
# install dependencies
python-test-samples$ pip install -r tests/requirements.txt --user

# run unit test
python-test-samples$ python -m pytest -s tests/unit -v
```

### Run integration tests against cloud resources

To build and deploy your application, run the following in your shell:

```bash
sam build --use-container
sam deploy --guided
```

The first command will build the source of your application. The second command will package and deploy your application to AWS, with a series of prompts:

* **Stack Name**: The name of the stack to deploy to CloudFormation. This should be unique to your account and region, and a good starting point would be something matching your project name.
* **AWS Region**: The AWS region you want to deploy your app to.
* **Confirm changes before deploy**: If set to yes, any change sets will be shown to you before execution for manual review. If set to no, the AWS SAM CLI will automatically deploy application changes.
* **Allow SAM CLI IAM role creation**: Many AWS SAM templates, including this example, create AWS IAM roles required for the AWS Lambda function(s) included to access AWS services. By default, these are scoped down to minimum required permissions. To deploy an AWS CloudFormation stack which creates or modifies IAM roles, the `CAPABILITY_IAM` value for `capabilities` must be provided. If permission isn't provided through this prompt, to deploy this example you must explicitly pass `--capabilities CAPABILITY_IAM` to the `sam deploy` command.
* **Save arguments to samconfig.toml**: If set to yes, your choices will be saved to a configuration file inside the project, so that in the future you can just re-run `sam deploy` without parameters to deploy changes to your application.

You can find your API Gateway Endpoint URL in the output values displayed after deployment. Take note of this URL for use in the logging section below.

On subsequent deploys you can run `sam deploy` without the `--guided` flag.

The integration tests run against cloud resources. Since unit tests cannot adequately test IAM permissions, our integration tests confirm that permissions are properly configured. Run integration tests against your deployed cloud resources:

```bash
# Create the env variable AWS_SAM_STACK_NAME with the name of the stack you specified prior to deploy
python-test-samples$ AWS_SAM_STACK_NAME=<stack-name> python -m pytest -s tests/integration -v
```

## Fetch, tail, and filter Lambda function logs

To simplify troubleshooting, SAM CLI has a command called `sam logs`. The `sam logs` command lets you fetch logs generated by your deployed Lambda function from the command line. In addition to printing the logs on the terminal, this command has several features to help you quickly find your bug.

`NOTE`: This command works for all AWS Lambda functions; not just the ones you deploy using SAM.

```bash
python-test-samples$ sam logs -n PythonTestDemo --stack-name python-test-samples --tail
```

In a new terminal, curl the API Gateway and watch the log output.

```bash
python-test-samples$ curl <API Gateway url>
```

You can find more information and examples about filtering Lambda function logs in the [SAM CLI Documentation](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-logging.html).


## Cleanup

To delete the sample application that you created, use the AWS CLI. Assuming you used your project name for the stack name, you can run the following:

```bash
aws cloudformation delete-stack --stack-name python-test-samples
```

## Resources

See the [AWS SAM developer guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html) for an introduction to SAM specification, the SAM CLI, and serverless application concepts.

Next, you can use AWS Serverless Application Repository to deploy ready to use Apps that go beyond hello world samples and learn how authors developed their applications: [AWS Serverless Application Repository main page](https://aws.amazon.com/serverless/serverlessrepo/)
