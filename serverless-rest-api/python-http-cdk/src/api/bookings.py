# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import decimal
import json
import os
import uuid
from datetime import datetime

from aws_embedded_metrics import metric_scope
from aws_xray_sdk.core import patch_all

patch_all()

BOOKINGS_TABLE = os.getenv('BOOKINGS_TABLE', None)
dynamodb = boto3.resource('dynamodb')
ddbTable = dynamodb.Table(BOOKINGS_TABLE)


def decimal_default_json(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError


@metric_scope
def lambda_handler(event, context, metrics):
    route_key = event['routeKey']

    response_body = {'Message': 'Unsupported route'}
    status_code = 400
    headers = {'Content-Type': 'application/json'}

    # Put common business metrics using EMF
    metric_payload = {}
    metrics.put_dimensions({'Service': 'Bookings'})
    metrics.put_metric('ProcessedBookings', 1, 'Count')
    metrics.set_property('requestId', event['requestContext']['requestId'])
    metrics.set_property('routeKey', event['routeKey'])

    try:
        # Get bookings for resource
        if route_key == 'GET /locations/{locationid}/resources/{resourceid}/bookings':
            metric_payload['operation'] = 'GET'
            metric_payload['locationid'] = event['pathParameters']['locationid']
            metric_payload['resourceid'] = event['pathParameters']['resourceid']
            ddb_response = ddbTable.query(
                IndexName='bookingsByResourceByTimeGSI',
                KeyConditionExpression='resourceid = :resourceid',
                ExpressionAttributeValues={
                    ':resourceid': event['pathParameters']['resourceid']
                }
            )
            response_body = ddb_response['Items']
            status_code = 200
        # Get bookings for user
        if route_key == 'GET /users/{userid}/bookings':
            metric_payload['operation'] = 'GET'
            metric_payload['userid'] = event['pathParameters']['userid']
            ddb_response = ddbTable.query(
                IndexName='useridGSI',
                KeyConditionExpression='userid = :userid',
                ExpressionAttributeValues={
                    ':userid': event['pathParameters']['userid']
                }
            )
            response_body = ddb_response['Items']
            status_code = 200
        # Booking CRUD operations
        if route_key == 'GET /users/{userid}/bookings/{bookingid}':
            metric_payload['operation'] = 'GET'
            metric_payload['bookingid'] = event['pathParameters']['bookingid']
            metric_payload['userid'] = event['pathParameters']['userid']
            ddb_response = ddbTable.get_item(
                Key={'bookingid': event['pathParameters']['bookingid']}
            )
            if 'Item' in ddb_response:
                response_body = ddb_response['Item']
            else:
                response_body = {}
            status_code = 200
        if route_key == 'DELETE /users/{userid}/bookings/{bookingid}':
            metric_payload['operation'] = 'DELETE'
            metric_payload['bookingid'] = event['pathParameters']['bookingid']
            metric_payload['userid'] = event['pathParameters']['userid']
            ddbTable.delete_item(
                Key={'bookingid': event['pathParameters']['bookingid']}
            )
            response_body = {}
            status_code = 200
        if route_key == 'PUT /users/{userid}/bookings':
            request_json = json.loads(event['body'])
            request_json['userid'] = event['pathParameters']['userid']
            request_json['timestamp'] = datetime.now().isoformat()
            if 'bookingid' not in request_json:
                request_json['bookingid'] = str(uuid.uuid1())
            metric_payload['operation'] = 'PUT'
            metric_payload['bookingid'] = request_json['bookingid']
            metric_payload['userid'] = event['pathParameters']['userid']
            ddbTable.put_item(
                Item=request_json
            )
            response_body = request_json
            status_code = 200
    except Exception as err:
        status_code = 400
        response_body = {'Error:': str(err)}
        print(str(err))
    metrics.set_property("Payload", metric_payload)
    return {
        'statusCode': status_code,
        'body': json.dumps(response_body, default=decimal_default_json),
        'headers': headers
    }
