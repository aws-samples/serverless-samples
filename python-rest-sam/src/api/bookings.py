# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Implementation of the API backend for bookings
import boto3
import decimal
import json
import os
import uuid
from datetime import datetime

from aws_embedded_metrics import metric_scope

# Patch libraries to instrument downstream calls
# See https://docs.aws.amazon.com/xray/latest/devguide/xray-sdk-python-patching.html for more details
from aws_xray_sdk.core import patch_all
patch_all()

# Prepare DynamoDB client
BOOKINGS_TABLE = os.getenv('BOOKINGS_TABLE', None)
dynamodb = boto3.resource('dynamodb')
ddbTable = dynamodb.Table(BOOKINGS_TABLE)


# JSON serializer fix, 
# based on https://stackoverflow.com/questions/1960516/python-json-serialize-a-decimal-object
def decimal_default_json(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError


@metric_scope
def lambda_handler(event, context, metrics):
    route_key = f"{event['httpMethod']} {event['resource']}"

    # Set default response, override with data from DynamoDB if any
    response_body = {'Message': 'Unsupported route'}
    status_code = 400
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
        }

    # Initialize putting common business metrics using EMF
    metric_payload = {}
    metrics.put_dimensions({'Service': 'Bookings'})
    metrics.put_metric('ProcessedBookings', 1, 'Count')
    metrics.set_property('requestId', event['requestContext']['requestId'])
    metrics.set_property('routeKey', route_key)

    try:
        # Get bookings for resource
        if route_key == 'GET /locations/{locationid}/resources/{resourceid}/bookings':
            # add business metrics for the route
            metric_payload['operation'] = 'GET'
            metric_payload['locationid'] = event['pathParameters']['locationid']
            metric_payload['resourceid'] = event['pathParameters']['resourceid']
            # get data from the database
            ddb_response = ddbTable.query(
                IndexName='bookingsByResourceByTimeGSI',
                KeyConditionExpression='resourceid = :resourceid',
                ExpressionAttributeValues={
                    ':resourceid': event['pathParameters']['resourceid']
                }
            )
            # return list of items instead of full DynamoDB response
            response_body = ddb_response['Items']
            status_code = 200
        # Get bookings for user
        if route_key == 'GET /users/{userid}/bookings':
            # generate business metrics for the route
            metric_payload['operation'] = 'GET'
            metric_payload['userid'] = event['pathParameters']['userid']
            # get data from the database
            ddb_response = ddbTable.query(
                IndexName='useridGSI',
                KeyConditionExpression='userid = :userid',
                ExpressionAttributeValues={
                    ':userid': event['pathParameters']['userid']
                }
            )
            # return list of items instead of full DynamoDB response
            response_body = ddb_response['Items']
            status_code = 200
        # Booking CRUD operations
        if route_key == 'GET /users/{userid}/bookings/{bookingid}':
            # generate business metrics for the route
            metric_payload['operation'] = 'GET'
            metric_payload['bookingid'] = event['pathParameters']['bookingid']
            metric_payload['userid'] = event['pathParameters']['userid']
            # get data from the database
            ddb_response = ddbTable.get_item(
                Key={'bookingid': event['pathParameters']['bookingid']}
            )
            # return list of items instead of full DynamoDB response
            if 'Item' in ddb_response:
                response_body = ddb_response['Item']
            else:
                response_body = {}
            status_code = 200
        if route_key == 'DELETE /users/{userid}/bookings/{bookingid}':
            # generate business metrics for the route
            metric_payload['operation'] = 'DELETE'
            metric_payload['bookingid'] = event['pathParameters']['bookingid']
            metric_payload['userid'] = event['pathParameters']['userid']
            # delete item in the database
            ddbTable.delete_item(
                Key={'bookingid': event['pathParameters']['bookingid']}
            )
            response_body = {}
            status_code = 200
        if route_key == 'PUT /users/{userid}/bookings':
            request_json = json.loads(event['body'])
            request_json['userid'] = event['pathParameters']['userid']
            request_json['timestamp'] = datetime.now().isoformat()
            # generate unique id if it isn't present in the request
            if 'bookingid' not in request_json:
                request_json['bookingid'] = str(uuid.uuid1())
            # generate business metrics for the route
            metric_payload['operation'] = 'PUT'
            metric_payload['bookingid'] = request_json['bookingid']
            metric_payload['userid'] = event['pathParameters']['userid']
            # update the database
            ddbTable.put_item(
                Item=request_json
            )
            response_body = request_json
            status_code = 200
    except Exception as err:
        status_code = 400
        response_body = {'Error:': str(err)}
        print(str(err))
    # Add route specific business metrics
    metrics.set_property("Payload", metric_payload)
    return {
        'statusCode': status_code,
        'body': json.dumps(response_body, default=decimal_default_json),
        'headers': headers
    }
