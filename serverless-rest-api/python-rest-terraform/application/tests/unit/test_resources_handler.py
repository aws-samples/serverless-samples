# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import os
import boto3
import uuid
import pytest
import pytest_freezegun
from moto import mock_dynamodb
from contextlib import contextmanager
from unittest.mock import patch

RESOURCES_MOCK_TABLE_NAME = 'Locations'
UUID_MOCK_VALUE = '13245678-1234-5678-1234-123456789012'


def mock_uuid():
    return UUID_MOCK_VALUE


@contextmanager
def setup_test_environment():
    with mock_dynamodb():
        set_up_dynamodb()
        put_data_dynamodb()
        yield


def set_up_dynamodb():
    conn = boto3.client(
        'dynamodb',
        aws_access_key_id='mock',
        aws_secret_access_key='mock',
    )
    conn.create_table(
        TableName=RESOURCES_MOCK_TABLE_NAME,
        KeySchema=[
            {'AttributeName': 'resourceid', 'KeyType': 'HASH'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'resourceid', 'AttributeType': 'S'},
            {'AttributeName': 'locationid', 'AttributeType': 'S'}
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'locationidGSI',
                'KeySchema': [
                    {
                        'AttributeName': 'locationid',
                        'KeyType': 'HASH'
                    },
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                },
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 2,
                    'WriteCapacityUnits': 2
                }
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
        }
    )


def put_data_dynamodb():
    conn = boto3.client(
        'dynamodb',
        aws_access_key_id='mock',
        aws_secret_access_key='mock',
    )
    conn.put_item(
        TableName=RESOURCES_MOCK_TABLE_NAME,
        Item={
            'locationid': {'S': '6db6cd70-9bd8-11eb-a21c-434bdc25fe66'},
            'resourceid': {'S': '86f0b180-9be1-11eb-a305-35487c0301a7'},
            'description': {'S': 'Venetian Level 2'},
            'name': {'S': 'Titian 2205'},
            'type': {'S': 'room'},
            'timestamp': {'S': '2021-03-30T21:57:49.860Z'}
        }
    )
    conn.put_item(
        TableName=RESOURCES_MOCK_TABLE_NAME,
        Item={
            'locationid': {'S': '6db6cd70-9bd8-11eb-a21c-434bdc25fe66'},
            'resourceid': {'S': '246396e0-9308-11eb-87e3-8f538c287bfc'},
            'description': {'S': 'Venetian Level 3'},
            'name': {'S': 'Toscana 3606, Room'},
            'type': {'S': 'room'},
            'timestamp': {'S': '2021-03-30T21:57:49.860Z'}
        }
    )


@patch.dict(os.environ, {'RESOURCES_TABLE': RESOURCES_MOCK_TABLE_NAME, 'AWS_XRAY_CONTEXT_MISSING': 'LOG_ERROR'})
def test_get_resources_by_location():
    with setup_test_environment():
        from src.api import resources
        with open('./events/event-get-resources-by-location.json', 'r') as f:
            apigw_event = json.load(f)
        expected_response = [
            {
                'locationid': '6db6cd70-9bd8-11eb-a21c-434bdc25fe66',
                'resourceid': '86f0b180-9be1-11eb-a305-35487c0301a7',
                'description': 'Venetian Level 2',
                'name': 'Titian 2205',
                'type': 'room',
                'timestamp': '2021-03-30T21:57:49.860Z',
            },
            {
                'locationid': '6db6cd70-9bd8-11eb-a21c-434bdc25fe66',
                'resourceid': '246396e0-9308-11eb-87e3-8f538c287bfc',
                'description': 'Venetian Level 3',
                'name': 'Toscana 3606, Room',
                'type': 'room',
                'timestamp': '2021-03-30T21:57:49.860Z',
            }
        ]
        ret = resources.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data == expected_response


def test_get_single_resource():
    with setup_test_environment():
        from src.api import resources
        with open('./events/event-get-resource-by-id.json', 'r') as f:
            apigw_event = json.load(f)
        expected_response = {
            'locationid': '6db6cd70-9bd8-11eb-a21c-434bdc25fe66',
            'resourceid': '86f0b180-9be1-11eb-a305-35487c0301a7',
            'description': 'Venetian Level 2',
            'name': 'Titian 2205',
            'type': 'room',
            'timestamp': '2021-03-30T21:57:49.860Z'
        }
        ret = resources.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data == expected_response


def test_get_single_resource_wrong_id():
    with setup_test_environment():
        from src.api import resources
        with open('./events/event-get-resource-by-id.json', 'r') as f:
            apigw_event = json.load(f)
        apigw_event['pathParameters']['resourceid'] = '123456789'
        expected_response = {}
        ret = resources.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data == expected_response


@patch('uuid.uuid1', mock_uuid)
@pytest.mark.freeze_time('2001-01-01')
def test_add_resource():
    with setup_test_environment():
        from src.api import resources
        with open('./events/event-put-resource.json', 'r') as f:
            apigw_event = json.load(f)
        expected_response = json.loads(apigw_event['body'])
        ret = resources.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data['resourceid'] == UUID_MOCK_VALUE
        assert data['locationid'] == apigw_event['pathParameters']['locationid']
        assert data['description'] == expected_response['description']
        assert data['name'] == expected_response['name']
        assert data['type'] == expected_response['type']
        assert data['timestamp'] == '2001-01-01T00:00:00'


@pytest.mark.freeze_time('2001-01-01')
def test_add_booking_with_id():
    with setup_test_environment():
        from src.api import resources
        with open('./events/event-put-resource.json', 'r') as f:
            apigw_event = json.load(f)
        expected_response = json.loads(apigw_event['body'])
        apigw_event['body'] = apigw_event['body'].replace('}', ', \"resourceid\":\"123456789\"}')
        ret = resources.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data['resourceid'] == '123456789'
        assert data['locationid'] == apigw_event['pathParameters']['locationid']
        assert data['description'] == expected_response['description']
        assert data['name'] == expected_response['name']
        assert data['type'] == expected_response['type']
        assert data['timestamp'] == '2001-01-01T00:00:00'


def test_delete_resource():
    with setup_test_environment():
        from src.api import resources
        with open('./events/event-delete-resource.json', 'r') as f:
            apigw_event = json.load(f)
        ret = resources.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        assert json.loads(ret['body']) == {}
