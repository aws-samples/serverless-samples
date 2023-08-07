# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import os
from contextlib import contextmanager
import mock
from unittest.mock import patch
import boto3
import pytest
import io
from moto import mock_dynamodb
from moto import mock_s3

from botocore.response import StreamingBody

SQS_MESSAGE_STORE_TABLE_NAME = 'SQS_MESSAGE_STORE_TEST'
BATCH_SIMULATOR_BUCKET_NAME = 'BATCH_SIMULATOR_TEST_BUCKET'
INVALID_JOB_ID = '38573c4b-07ad-4ccf-8241-869ffe16d566'
INVALID_JOB_ID_ERROR_MSG= "No Job data found for Job Id" 
JOB_STAUS_INCOMPLETE = "submiited"
JOB_STAUS_COMPLETE = "complete"

@contextmanager
def setup_test_environment():
    with mock_dynamodb():
        set_up_dynamodb()
        yield


def set_up_dynamodb():
    conn = boto3.client(
        'dynamodb',
        aws_access_key_id='mock',
        aws_secret_access_key='mock',
    )
    conn.create_table(
        TableName=SQS_MESSAGE_STORE_TABLE_NAME,
        KeySchema=[
            {'AttributeName': 'jobRequestId', 'KeyType': 'HASH'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'jobRequestId', 'AttributeType': 'S'}
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
        }
    )

@mock_s3
def setup_mock_s3():
    s3_client = boto3.client(
        "s3",
        region_name='us-east-1',
        aws_access_key_id='mock',
        aws_secret_access_key='mock'            
        )
    s3_client.create_bucket(Bucket=BATCH_SIMULATOR_BUCKET_NAME)

@patch.dict(os.environ, {'SQS_MESSAGE_STORE_TABLE_NAME': SQS_MESSAGE_STORE_TABLE_NAME, 'AWS_XRAY_CONTEXT_MISSING': 'LOG_ERROR','BATCH_SIMULATOR_BUCKET_NAME':BATCH_SIMULATOR_BUCKET_NAME})
def test_get_job_status_valid_job_id():
    with setup_test_environment():
        from src.api import get_job_status
        with open('./events/get_job_status_function.txt', 'r') as f:
            get_job_status_event = json.load(f)            
        

        store_mock_job_record(get_job_status_event["pathParameters"]["job-id"], JOB_STAUS_COMPLETE)

        response = get_job_status.lambda_handler(get_job_status_event, '')
        
        response_data = response.get("body")
        response_data = response_data.replace("\'", "\"")
        response_body =json.loads(response_data)


        assert response_body['jobRequestId'] == get_job_status_event["pathParameters"]["job-id"]
        assert response_body['jobStatus'] == JOB_STAUS_COMPLETE
        assert BATCH_SIMULATOR_BUCKET_NAME in response_body['jobProcessedPayloadLink']

@patch.dict(os.environ, {'SQS_MESSAGE_STORE_TABLE_NAME': SQS_MESSAGE_STORE_TABLE_NAME, 'AWS_XRAY_CONTEXT_MISSING': 'LOG_ERROR','BATCH_SIMULATOR_BUCKET_NAME':BATCH_SIMULATOR_BUCKET_NAME})
def test_get_job_status_invalid_job_id():
    with setup_test_environment():
        from src.api import get_job_status
        with open('./events/get_job_status_function.txt', 'r') as f:
            get_job_status_event = json.load(f)            
        
        store_mock_job_record(INVALID_JOB_ID, JOB_STAUS_COMPLETE)

        response = get_job_status.lambda_handler(get_job_status_event, '')
        assert INVALID_JOB_ID_ERROR_MSG in response['Error Message']

@patch.dict(os.environ, {'SQS_MESSAGE_STORE_TABLE_NAME': SQS_MESSAGE_STORE_TABLE_NAME, 'AWS_XRAY_CONTEXT_MISSING': 'LOG_ERROR','BATCH_SIMULATOR_BUCKET_NAME':BATCH_SIMULATOR_BUCKET_NAME})
def test_get_job_status_job_in_complete():
    with setup_test_environment():
        from src.api import get_job_status
        with open('./events/get_job_status_function.txt', 'r') as f:
            get_job_status_event = json.load(f)            
        
        store_mock_job_record(get_job_status_event["pathParameters"]["job-id"], JOB_STAUS_INCOMPLETE)

        response = get_job_status.lambda_handler(get_job_status_event, '')
        
        response_data = response.get("body")
        response_data = response_data.replace("\'", "\"")
        response_body =json.loads(response_data)


        assert response_body['jobRequestId'] == get_job_status_event["pathParameters"]["job-id"]
        assert response_body['jobStatus'] == JOB_STAUS_INCOMPLETE
        assert 'jobProcessedPayloadLink' not in response

def store_mock_job_record(mock_job_url_parameter, mock_job_status):
    mock_dynamodb_table = boto3.resource('dynamodb').Table(SQS_MESSAGE_STORE_TABLE_NAME)
    mock_job_record= {
        "jobPayloadLocation":BATCH_SIMULATOR_BUCKET_NAME,
        "jobStatus":mock_job_status,
        "jobPayloadKey":mock_job_url_parameter,
        "jobRequestId":mock_job_url_parameter
    }    
    response= mock_dynamodb_table.put_item(Item=mock_job_record)

