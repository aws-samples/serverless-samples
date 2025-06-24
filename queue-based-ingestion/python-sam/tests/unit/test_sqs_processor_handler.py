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
from moto import mock_aws
from botocore.response import StreamingBody

SQS_MESSAGE_STORE_TABLE_NAME = 'SQS_MESSAGE_STORE_TEST'
BATCH_SIMULATOR_FUNCTION_NAME = 'BATCH_SIMULATOR_TEST'
TEST_PAYLOAD_MESSAGE_ID= ''
MOCK_JOB_STATUS ='complete'
MOCK_PAYLOAD_LOCATION='mock_payload_location'
MOCK_PAYLOAD_KEY= 'mock_payload_key'

@contextmanager
def setup_test_environment():
    with mock_aws():
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
@patch.dict(os.environ, {'SQS_MESSAGE_STORE_TABLE_NAME': SQS_MESSAGE_STORE_TABLE_NAME, 'AWS_XRAY_CONTEXT_MISSING': 'LOG_ERROR','BATCH_SIMULATOR_FUNCTION_NAME':BATCH_SIMULATOR_FUNCTION_NAME})
@mock.patch("src.api.sqs_processor.lambda_client")
def test_process_sqs_message(mock_lambda_client):
    with setup_test_environment():
        from src.api import sqs_processor
        with open('./events/SQS_message_processor_function.txt', 'r') as f:
            sqs_event = json.load(f)            
        
        test_paylaod_message_id= sqs_event['Records'][0]['messageId'] 

        mocked_response_payload = json.dumps({'body':{'jobStatus':MOCK_JOB_STATUS,'jobPayloadLocation':MOCK_PAYLOAD_LOCATION,'jobPayloadKey':MOCK_PAYLOAD_KEY}}).encode("utf-8")
        mock_lambda_client.invoke.return_value = {'Payload': StreamingBody(io.BytesIO(mocked_response_payload), len(mocked_response_payload))}
        

        sqs_processor.lambda_handler(sqs_event, '')

        return_job_record= retrieve_job_record(test_paylaod_message_id)
        assert return_job_record['jobRequestId'] == test_paylaod_message_id
        assert return_job_record['jobStatus'] == MOCK_JOB_STATUS
        assert return_job_record['jobPayloadLocation'] == MOCK_PAYLOAD_LOCATION
        assert return_job_record['jobPayloadKey'] == MOCK_PAYLOAD_KEY

def retrieve_job_record(test_paylaod_message_id):
    mock_dynamodb_table = boto3.resource('dynamodb').Table(SQS_MESSAGE_STORE_TABLE_NAME)
    response = mock_dynamodb_table.get_item(Key={'jobRequestId':test_paylaod_message_id})
    return  response ['Item']

