# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import os
import time
import requests

RESOURCES_STACK_NAME = "fraud-detector-resources"
MODEL_ID = 'transaction_model'
# Use sample dataset used in the blog post https://aws.amazon.com/blogs/machine-learning/detect-online-transaction-fraud-with-new-amazon-fraud-detector-features/
SAPLE_DATA_URL="https://aws-ml-blog.s3.amazonaws.com/artifacts/fraud-detector-transaction-fraud-insights/synthetic_txn_data_new.csv"
SAMPLE_DATASET_NAME = "sample_data.csv"
model_arn = "<none>"

sts = boto3.client("sts")
account_id = sts.get_caller_identity()["Account"]

# Get resources stack outputs used in the code
print("Getting outputs from the resources stack ("+RESOURCES_STACK_NAME+") ...")
fraud_detector_bucket = account_id+"-fraud-detector-data"
fraud_detector_data_access_iam_role = ""
event_type = 'transaction_event'
cfn = boto3.client('cloudformation')
resources_outputs = (cfn.describe_stacks(StackName=RESOURCES_STACK_NAME))[
    "Stacks"][0]["Outputs"]
for output in resources_outputs:
    if output["OutputKey"] == "SampleDataS3Bucket":
        fraud_detector_bucket = output["OutputValue"]
    if output["OutputKey"] == "TransactionEventType":
        event_type = output["OutputValue"].rsplit('/', 1)[-1]
    if output["OutputKey"] == "FraudDetectorDataAccessRole":
        fraud_detector_data_access_iam_role = output["OutputValue"]

# Get sample dataset
print("Downloading sample data ...")
data = requests.get(SAPLE_DATA_URL, allow_redirects=True)
open(SAMPLE_DATASET_NAME, 'wb').write(data.content)
print("Preparing sample data ...")
# Sample data file contains outdated data. We will bring it up to date by replacing 2020 and 2021 in the dataset
with open(SAMPLE_DATASET_NAME, 'rt') as file:
    data = file.read()
    data = data.replace("2020-", "2022-")
    data = data.replace("2021-", "2023-")
with open(SAMPLE_DATASET_NAME, 'wt') as file:
    file.write(data)
# Upload sample data to S3 bucket
s3 = boto3.client('s3')
with open(SAMPLE_DATASET_NAME, "rb") as f:
    s3.upload_fileobj(f, fraud_detector_bucket,
                      MODEL_ID+"/input/"+SAMPLE_DATASET_NAME)
# Delete temporary files if any
if os.path.exists(SAMPLE_DATASET_NAME):
    os.remove(SAMPLE_DATASET_NAME)
if os.path.exists(SAPLE_DATA_URL.rsplit('/', 1)[-1]):
    os.remove(SAPLE_DATA_URL.rsplit('/', 1)[-1])

fraudDetector = boto3.client('frauddetector')

print("Starting data import process. It may take 5 minutes or more ...")
result = fraudDetector.create_batch_import_job(
    jobId='transaction_sample_data_import',
    inputPath='s3://'+fraud_detector_bucket+"/"+MODEL_ID+"/input/"+SAMPLE_DATASET_NAME,
    outputPath='s3://'+fraud_detector_bucket+"/"+MODEL_ID+"/output/",
    eventTypeName=event_type,
    iamRoleArn="arn:aws:iam::"+account_id +
    ":role/"+fraud_detector_data_access_iam_role
)

import_job_status = 'IN_PROGRESS'
while import_job_status in ['IN_PROGRESS', 'IN_PROGRESS_INITIALIZING', 'CANCEL_IN_PROGRESS']:
    time.sleep(60)
    response = fraudDetector.get_batch_import_jobs(
        jobId='transaction_sample_data_import',
        maxResults=1,
        nextToken='next_token'
    )
    import_job_status = response['batchImports'][0]['status']

if import_job_status == 'COMPLETE':
    print("Creating model ...")
    result = fraudDetector.create_model(
        modelId=MODEL_ID,
        eventTypeName=event_type,
        modelType='TRANSACTION_FRAUD_INSIGHTS')
    print("Starting model training process. It may take 30 minutes or more ...")
    result = fraudDetector.create_model_version(
        modelId=MODEL_ID,
        modelType='TRANSACTION_FRAUD_INSIGHTS',
        trainingDataSource='INGESTED_EVENTS',
        trainingDataSchema={
            'modelVariables': ['phone', 'user_agent', 'billing_zip', 'order_price', 'customer_job', 'billing_state',
                               'merchant', 'customer_name', 'card_bin', 'payment_currency', 'billing_city', 'customer_email', 'billing_street',
                               'product_category', 'billing_latitude', 'ip_address', 'billing_longitude'],
            'labelSchema': {
                'labelMapper': {
                    'FRAUD': ['1'],
                    'LEGIT': ['0']
                },
                'unlabeledEventsTreatment': 'IGNORE'
            }
        }
    )
    model_version_status = 'TRAINING_IN_PROGRESS'
    while model_version_status == 'TRAINING_IN_PROGRESS':
        time.sleep(60)
        response = fraudDetector.get_model_version(
            modelId=MODEL_ID,
            modelType='TRANSACTION_FRAUD_INSIGHTS',
            modelVersionNumber='1.0'
        )
        model_version_status = response['status']
    if model_version_status == 'TRAINING_COMPLETE':
        model_arn = response['arn']
        print("Activating model version. It may take 10 minutes or more ...")
        result = fraudDetector.update_model_version_status(
            modelId=MODEL_ID,
            modelType='TRANSACTION_FRAUD_INSIGHTS',
            modelVersionNumber='1.0',
            status='ACTIVE'
        )
        model_version_status = 'ACTIVATE_REQUESTED'
        while model_version_status in ['ACTIVATE_REQUESTED','ACTIVATE_IN_PROGRESS']:
            time.sleep(60)
            response = fraudDetector.get_model_version(
                modelId=MODEL_ID,
                modelType='TRANSACTION_FRAUD_INSIGHTS',
                modelVersionNumber='1.0'
            )
            model_version_status = response['status']
        print("Model preparation completed.")
        if model_version_status == 'ACTIVE':
            print("Model ARN: "+model_arn)
        else:
            print("Model activation failed")
    else:
        print("Model version training failed: "+str(result))
else:
    print("Training data import failed:" + str(result))

