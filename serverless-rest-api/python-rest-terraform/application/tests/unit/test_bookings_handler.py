# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import os
from contextlib import contextmanager
from unittest.mock import patch
import boto3
import pytest
from moto import mock_dynamodb

BOOKINGS_MOCK_TABLE_NAME = 'Bookings'
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
        TableName=BOOKINGS_MOCK_TABLE_NAME,
        KeySchema=[
            {'AttributeName': 'bookingid', 'KeyType': 'HASH'},
        ],
        AttributeDefinitions=[
            {'AttributeName': 'bookingid', 'AttributeType': 'S'},
            {'AttributeName': 'userid', 'AttributeType': 'S'},
            {'AttributeName': 'resourceid', 'AttributeType': 'S'},
            {'AttributeName': 'starttimeepochtime', 'AttributeType': 'N'}
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'useridGSI',
                'KeySchema': [
                    {
                        'AttributeName': 'userid',
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
            {
                'IndexName': 'bookingsByResourceByTimeGSI',
                'KeySchema': [
                    {
                        'AttributeName': 'resourceid',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'starttimeepochtime',
                        'KeyType': 'RANGE'
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
            {
                'IndexName': 'bookingsByUserByTimeGSI',
                'KeySchema': [
                    {
                        'AttributeName': 'userid',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'starttimeepochtime',
                        'KeyType': 'RANGE'
                    },
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                },
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 2,
                    'WriteCapacityUnits': 2
                }
            }
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
        TableName=BOOKINGS_MOCK_TABLE_NAME,
        Item={
            'bookingid': {'S': '1f290bf0-9be2-11eb-9326-b188c945553f'},
            'resourceid': {'S': 'f8216640-91a2-11eb-8ab9-57aa454facef'},
            'userid': {'S': 'bf6dbddc-db2e-4f70-a892-1b165556dede'},
            'timestamp': {'S': '2021-03-30T21:57:49.860Z'},
            'starttimeepochtime': {'N': '1617278400'}
        }
    )
    conn.put_item(
        TableName=BOOKINGS_MOCK_TABLE_NAME,
        Item={
            'bookingid': {'S': '31a9f940-1234-5678-1234-67837e2c40b0'},
            'resourceid': {'S': '86f0b180-9be1-11eb-a305-35487c0301a7'},
            'userid': {'S': '123456'},
            'timestamp': {'S': '2021-03-30T21:57:49.860Z'},
            'starttimeepochtime': {'N': '1617278400'}
        }
    )


@patch.dict(os.environ, {'BOOKINGS_TABLE': BOOKINGS_MOCK_TABLE_NAME, 'AWS_XRAY_CONTEXT_MISSING': 'LOG_ERROR'})
def test_get_bookings_by_user():
    with setup_test_environment():
        from src.api import bookings
        with open('./events/event-get-bookings-by-user.json', 'r') as f:
            apigw_event = json.load(f)
        expected_response = [
            {
                'bookingid': '1f290bf0-9be2-11eb-9326-b188c945553f',
                'resourceid': 'f8216640-91a2-11eb-8ab9-57aa454facef',
                'userid': 'bf6dbddc-db2e-4f70-a892-1b165556dede',
                'timestamp': '2021-03-30T21:57:49.860Z',
                'starttimeepochtime': 1617278400
            }
        ]
        ret = bookings.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data == expected_response


def test_get_bookings_by_resource():
    with setup_test_environment():
        from src.api import bookings
        with open('./events/event-get-bookings-by-resource.json', 'r') as f:
            apigw_event = json.load(f)
        expected_response = [
            {
                'bookingid': '31a9f940-1234-5678-1234-67837e2c40b0',
                'resourceid': '86f0b180-9be1-11eb-a305-35487c0301a7',
                'userid': '123456',
                'timestamp': '2021-03-30T21:57:49.860Z',
                'starttimeepochtime': 1617278400
            }
        ]
        ret = bookings.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data == expected_response


def test_get_single_booking():
    with setup_test_environment():
        from src.api import bookings
        with open('./events/event-get-booking-by-id.json', 'r') as f:
            apigw_event = json.load(f)
        expected_response = {
            'bookingid': '1f290bf0-9be2-11eb-9326-b188c945553f',
            'resourceid': 'f8216640-91a2-11eb-8ab9-57aa454facef',
            'userid': 'bf6dbddc-db2e-4f70-a892-1b165556dede',
            'timestamp': '2021-03-30T21:57:49.860Z',
            'starttimeepochtime': 1617278400
        }
        ret = bookings.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data == expected_response


def test_get_single_booking_wrong_id():
    with setup_test_environment():
        from src.api import bookings
        with open('./events/event-get-booking-by-id.json', 'r') as f:
            apigw_event = json.load(f)
            apigw_event['pathParameters']['bookingid'] = '123456789'
        expected_response = {}
        ret = bookings.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data == expected_response


@patch('uuid.uuid1', mock_uuid)
@pytest.mark.freeze_time('2001-01-01')
def test_add_booking():
    with setup_test_environment():
        from src.api import bookings
        with open('./events/event-put-booking.json', 'r') as f:
            apigw_event = json.load(f)
        expected_response = json.loads(apigw_event['body'])
        ret = bookings.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data['resourceid'] == expected_response['resourceid']
        assert data['starttimeepochtime'] == expected_response['starttimeepochtime']
        assert data['userid'] == apigw_event['pathParameters']['userid']
        assert data['timestamp'] == '2001-01-01T00:00:00'
        assert data['bookingid'] == UUID_MOCK_VALUE


@pytest.mark.freeze_time('2001-01-01')
def test_add_booking_with_id():
    with setup_test_environment():
        from src.api import bookings
        with open('./events/event-put-booking.json', 'r') as f:
            apigw_event = json.load(f)
        expected_response = json.loads(apigw_event['body'])
        apigw_event['body'] = apigw_event['body'].replace('}', ', \"bookingid\":\"123456789\"}')
        ret = bookings.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        data = json.loads(ret['body'])
        assert data['resourceid'] == expected_response['resourceid']
        assert data['starttimeepochtime'] == expected_response['starttimeepochtime']
        assert data['userid'] == apigw_event['pathParameters']['userid']
        assert data['timestamp'] == '2001-01-01T00:00:00'
        assert data['bookingid'] == '123456789'


def test_delete_booking():
    with setup_test_environment():
        from src.api import bookings
        with open('./events/event-delete-booking.json', 'r') as f:
            apigw_event = json.load(f)
        ret = bookings.lambda_handler(apigw_event, '')
        assert ret['statusCode'] == 200
        assert json.loads(ret['body']) == {}
