# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Implementation of the API backend for resources
import boto3
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
RESOURCES_TABLE = os.getenv('RESOURCES_TABLE', None)
dynamodb = boto3.resource('dynamodb')
ddbTable = dynamodb.Table(RESOURCES_TABLE)


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
    metrics.put_dimensions({'Service': 'Resources'})
    metrics.put_metric('ProcessedResources', 1, 'Count')
    metrics.set_property('requestId', event['requestContext']['requestId'])
    metrics.set_property('routeKey', route_key)

    try:
        # Get all resources
        if route_key == 'GET /locations/{locationid}/resources':
            # generate business metrics for the route
            metric_payload['operation'] = 'GET'
            metric_payload['locationid'] = event['pathParameters']['locationid']
            # get data from the database
            ddb_response = ddbTable.query(
                IndexName='locationidGSI',
                KeyConditionExpression='locationid = :locationid',
                ExpressionAttributeValues={
                    ':locationid': event['pathParameters']['locationid']
                }
            )
            # return list of items instead of full DynamoDB response
            response_body = ddb_response['Items']
            status_code = 200
        # Resource CRUD operations
        if route_key == 'GET /locations/{locationid}/resources/{resourceid}':
            # generate business metrics for the route
            metric_payload['operation'] = 'GET'
            metric_payload['locationid'] = event['pathParameters']['locationid']
            metric_payload['resourceid'] = event['pathParameters']['resourceid']
            # get data from the database
            ddb_response = ddbTable.get_item(
                Key={'resourceid': event['pathParameters']['resourceid']}
            )
            # return list of items instead of full DynamoDB response
            if 'Item' in ddb_response:
                response_body = ddb_response['Item']
            else:
                response_body = {}
            status_code = 200
        if route_key == 'DELETE /locations/{locationid}/resources/{resourceid}':
            # generate business metrics for the route
            metric_payload['operation'] = 'DELETE'
            metric_payload['locationid'] = event['pathParameters']['locationid']
            metric_payload['resourceid'] = event['pathParameters']['resourceid']
            # delete item in the database
            ddbTable.delete_item(
                Key={'resourceid': event['pathParameters']['resourceid']}
            )
            response_body = {}
            status_code = 200
        if route_key == 'PUT /locations/{locationid}/resources':
            request_json = json.loads(event['body'])
            request_json['locationid'] = event['pathParameters']['locationid']
            request_json['timestamp'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            # generate unique id if it isn't present in the request
            if 'resourceid' not in request_json:
                request_json['resourceid'] = str(uuid.uuid1())
            # generate business metrics for the route
            metric_payload['operation'] = 'DELETE'
            metric_payload['locationid'] = event['pathParameters']['locationid']
            metric_payload['resourceid'] = request_json['resourceid']
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
        'body': json.dumps(response_body),
        'headers': headers
    }
