# Amazon Fraud Detector automation

These scripts will create necessary resources, download data from a shared storage, train model and create detector. AWS CloudFormation does not support some steps and will require running a script written in Python.

This example uses Python 3 and the [AWS Serverless Application Model (AWS SAM)](https://aws.amazon.com/serverless/sam/) to deploy private APIs with custom domain names. Visit the [documentation](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html) to install it in your environment.

## Step 1: Create resources used by the model
First, you will need to deploy resources necessary for Amazon Fraud Detector model configuration and training (outcomes, variables, labels, etc.), Amazon S3 bucket for training data, and Fraud Detector permissions necessary to access the bucket. Run the following commands to deploy the CloudFormation stack using SAM:

```
sam build --template resources.yaml
sam deploy --guided --stack-name fraud-detector-resources --template resources.yaml
```

## Step 2: prepare model
CloudFormation cannot implement some data preparation, loading, and model training. We will use Python script to automate it.

First, we set up the environment. We set this project up like a standard Python project.  
Create a virtualenv:

```
python3 -m venv .venv
```

After the init process completes and we created the virtualenv, use the following step to activate it:

```
source .venv/bin/activate
```

Once you activated the virtualenv, install the required dependencies:

```
pip install -r requirements.txt
```

Now, run the model preparation script:

```
python3 ./prepare_model.py
```
Note: If you changed stack name in the previous steps, change RESOURCES_STACK_NAME in the script accordingly.

The script will perform the following steps:
 - Get output values from the resources stack exports - Amazon S3 bucket name for the sample data, Amazon IAM role for Amazon Fraud Detector, event type name for transaction.
 - Download sample dataset used in the [blog post](https://aws.amazon.com/blogs/machine-learning/detect-online-transaction-fraud-with-new-amazon-fraud-detector-features/) referred in the project [README.md](../README.md)
 - Change dates in the sample dataset - model training cannot use data older than 18 months.
 - Upload dataset to the S3 bucket created in the previous steps
 - Delete any temporary files created by download and data updates
 - Import sample data into Amazon Fraud Detector - this step may take 5 minutes or more
 - Once import completed, create a model and train it using sample data - this step may take 20 minutes or more
  - Activate trained model version to be used by client applications
 
 Note model ARN in the output - you will need it in the next step
 
## Step 3: Create Detector

Once model training completes, create a detector running following commands to deploy a detector CloudFormation stack using SAM:

```
sam build --template detector.yaml
sam deploy --guided --stack-name fraud-detector --template detector.yaml
```

## Cleanup
To delete resources created, follow these steps:
 - Navigate to Amazon Fraud Detector in the [AWS Management Console](https://us-east-1.console.aws.amazon.com/frauddetector/home)
 - Click on "Models" in the left navigation bar
 - Click on "transaction_model" in the models list
 - Click on the version "1.0" in the model versions list
 - Select "Undeploy model version" from the "Actions" drop-down menu on the right, follow instructions to undeploy model version
 - Wait until the model version is undeployed, select "Delete" from the "Actions" drop-down menu on the right, follow instructions to delete the model version
 - Select "Delete model" from the "Actions" drop-down menu of the "transaction_model", follow instructions to delete model
 - Click on "Events" in the left navigation bar
 - Click on transaction_event in the list of events
 - Click on "Stored events" tab
 - Toggle off "Event ingestion turned off for this event type"
 - Click on "Delete stored events" button
 - Click on transaction_sample_data_import in the "Import events data" list
 - Select "Delete import job" from the "Actions" drop-down menu on the right, follow instructions to delete import job
 - Navigate to S3 in [AWS Management Console](https://s3.console.aws.amazon.com/s3/buckets)
 - Select Fraud Detector sample data bucket and click "Empty" button, follow instructions on emptying bucket content 
- Run following commands to delete Cloud Formation stacks:
    ```
    sam delete --stack-name fraud-detector-resources
    sam delete --stack-name fraud-detector
    ```
