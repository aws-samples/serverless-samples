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
from moto import mock_s3

BATCH_SIMULATOR_BUCKET_NAME = 'BATCH_SIMULATOR_TEST_BUCKET1'
@contextmanager
def setup_test_environment():
    with mock_s3():
        setup_mock_s3()
        yield
@mock_s3
def setup_mock_s3():
    s3_client = boto3.client(
        "s3",
        aws_access_key_id='mock',
        aws_secret_access_key='mock',
        region_name="us-east-1"
        )
    s3_client.create_bucket(Bucket=BATCH_SIMULATOR_BUCKET_NAME)

@patch.dict(os.environ, {'BATCH_SIMULATOR_BUCKET_NAME': BATCH_SIMULATOR_BUCKET_NAME, 'AWS_XRAY_CONTEXT_MISSING': 'LOG_ERROR', 'WEATHER_DATA_STORE':'./src/api/weather_sample_data.dat'})
def test_batch_simulator_sucess():
    with setup_test_environment():
        from src.api import batch_simulator
        with open('./events/batch_Simulator_function.txt', 'r') as f:
            batch_simulator_event = json.load(f)            
        job_message_id = batch_simulator_event["jobRequestId"]

        result = batch_simulator.lambda_handler(batch_simulator_event,'')
        assert result["body"]["jobStatus"] == "complete"
        assert result["body"]["jobPayloadLocation"] == BATCH_SIMULATOR_BUCKET_NAME
        assert result["body"]["jobPayloadKey"] == job_message_id
