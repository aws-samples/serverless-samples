# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import os
import boto3
import uuid
import pytest
import pytest_freezegun
from moto import mock_aws
from contextlib import contextmanager
from unittest.mock import patch

LOCATIONS_MOCK_TABLE_NAME = 'Locations'
UUID_MOCK_VALUE = 'f8216640-91a2-11eb-8ab9-57aa454facef'


def mock_uuid():
    return UUID_MOCK_VALUE

@contextmanager
def setup_test_environment():
    with mock_aws():
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
        TableName=LOCATIONS_MOCK_TABLE_NAME,
        KeySchema=[
            {'AttributeName': 'locationid', 'KeyType': 'HASH'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'locationid', 'AttributeType': 'S'}
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
        TableName=LOCATIONS_MOCK_TABLE_NAME,
        Item={
            'locationid': {'S': 'f8216640-91a2-11eb-8ab9-57aa454facef'},
            'description': {'S': 'Las Vegas'},
            'name': {'S': 'The Venetian'},
            'timestamp': {'S': '2021-03-30T21:57:49.860Z'}
        }
    )
    conn.put_item(
        TableName=LOCATIONS_MOCK_TABLE_NAME,
        Item={
            'locationid': {'S': '31a9f940-917b-11eb-9054-67837e2c40b0'},
            'description': {'S': 'Las Vegas'},
            'name': {'S': 'Encore'},
            'timestamp': {'S': '2021-03-30T17:13:06.516Z'}
        }
    )


@patch.dict(os.environ, {'LOCATIONS_TABLE': LOCATIONS_MOCK_TABLE_NAME, 'AWS_XRAY_CONTEXT_MISSING': 'LOG_ERROR'})
def test_get_list_of_locations():
    with setup_test_environment():
        from src.api import locations
        with open('./events/event-get-all-locations.json', 'r') as f:
            apigw_get_all_locations_event = json.load(f)
        expected_response = [
            {
                'locationid': '31a9f940-917b-11eb-9054-67837e2c40b0',
                'description': 'Las Vegas',
                'name': 'Encore',
                'timestamp': '2021-03-30T17:13:06.516Z'
            },
            {
                'locationid': 'f8216640-91a2-11eb-8ab9-57aa454facef',
                'description': 'Las Vegas',
                'name': 'The Venetian',
                'timestamp': '2021-03-30T21:57:49.860Z'
            }
        ]
        ret = locations.lambda_handler(apigw_get_all_locations_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data == expected_response


def test_get_single_location():
    with setup_test_environment():
        from src.api import locations
        with open('./events/event-get-location-by-id.json', 'r') as f:
            apigw_event = json.load(f)
        expected_response = {
            'locationid': 'f8216640-91a2-11eb-8ab9-57aa454facef',
            'description': 'Las Vegas',
            'name': 'The Venetian',
            'timestamp': '2021-03-30T21:57:49.860Z'
        }
        ret = locations.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data == expected_response


def test_get_single_location_wrong_id():
    with setup_test_environment():
        from src.api import locations
        with open('./events/event-get-location-by-id.json', 'r') as f:
            apigw_event = json.load(f)
            apigw_event['pathParameters']['locationid'] = '123456789'
            apigw_event['rawPath'] = '/locations/123456789'
        ret = locations.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        assert json.loads(ret['body']) == {}


@patch('uuid.uuid1', mock_uuid)
@pytest.mark.freeze_time('2001-01-01')
def test_add_location():
    with setup_test_environment():
        from src.api import locations
        with open('./events/event-put-location.json', 'r') as f:
            apigw_event = json.load(f)
        expected_response = json.loads(apigw_event['body'])
        ret = locations.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data['locationid'] == UUID_MOCK_VALUE
        assert data['timestamp'] == '2001-01-01T00:00:00'
        assert data['description'] == expected_response['description']
        assert data['name'] == expected_response['name']
        assert data['imageUrl'] == expected_response['imageUrl']


@pytest.mark.freeze_time('2001-01-01')
def test_add_location_with_id():
    with setup_test_environment():
        from src.api import locations
        with open('./events/event-put-location.json', 'r') as f:
            apigw_event = json.load(f)
        expected_response = json.loads(apigw_event['body'])
        apigw_event['body'] = apigw_event['body'].replace('}', ', \"locationid\":\"123456789\"}')
        ret = locations.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data['locationid'] == '123456789'
        assert data['timestamp'] == '2001-01-01T00:00:00'
        assert data['description'] == expected_response['description']
        assert data['name'] == expected_response['name']
        assert data['imageUrl'] == expected_response['imageUrl']


def test_delete_location():
    with setup_test_environment():
        from src.api import locations
        with open('./events/event-delete-location.json', 'r') as f:
            apigw_event = json.load(f)
        ret = locations.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        assert json.loads(ret['body']) == {}
