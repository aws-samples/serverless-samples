# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import uuid
import os
import boto3
from datetime import datetime
from aws_xray_sdk.core import patch_all
from aws_embedded_metrics import metric_scope

patch_all()

LOCATIONS_TABLE = os.getenv('LOCATIONS_TABLE', None)
dynamodb = boto3.resource('dynamodb')
ddbTable = dynamodb.Table(LOCATIONS_TABLE)


@metric_scope
def lambda_handler(event, context, metrics):
    route_key = event['routeKey']

    response_body = {'Message': 'Unsupported route'}
    status_code = 400
    headers = {'Content-Type': 'application/json'}

    # Put common business metrics using EMF
    metric_payload = {}
    metrics.put_dimensions({'Service': 'Locations'})
    metrics.put_metric('ProcessedLocations', 1, 'Count')
    metrics.set_property('requestId', event['requestContext']['requestId'])
    metrics.set_property('routeKey', event['routeKey'])

    try:
        # Get all locations
        if route_key == 'GET /locations':
            metric_payload['operation'] = 'GET'
            ddb_response = ddbTable.scan(Select='ALL_ATTRIBUTES')
            response_body = ddb_response['Items']
            status_code = 200
        # Location CRUD operations
        if route_key == 'GET /locations/{locationid}':
            metric_payload['operation'] = 'GET'
            metric_payload['locationid'] = event['pathParameters']['locationid']
            ddb_response = ddbTable.get_item(
                Key={'locationid': event['pathParameters']['locationid']}
            )
            if 'Item' in ddb_response:
                response_body = ddb_response['Item']
            else:
                response_body = {}
            status_code = 200
        if route_key == 'DELETE /locations/{locationid}':
            metric_payload['operation'] = 'DELETE'
            metric_payload['locationid'] = event['pathParameters']['locationid']
            ddbTable.delete_item(
                Key={'locationid': event['pathParameters']['locationid']}
            )
            response_body = {}
            status_code = 200
        if route_key == 'PUT /locations':
            request_json = json.loads(event['body'])
            request_json['timestamp'] = datetime.now().isoformat()
            if 'locationid' not in request_json:
                request_json['locationid'] = str(uuid.uuid1())
            metric_payload['operation'] = 'PUT'
            metric_payload['locationid'] = request_json['locationid']
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
        'body': json.dumps(response_body),
        'headers': headers
    }
