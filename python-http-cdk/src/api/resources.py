# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import json
import os
import uuid
from datetime import datetime

from aws_embedded_metrics import metric_scope
from aws_xray_sdk.core import patch_all

patch_all()

RESOURCES_TABLE = os.getenv('RESOURCES_TABLE', None)
dynamodb = boto3.resource('dynamodb')
ddbTable = dynamodb.Table(RESOURCES_TABLE)


@metric_scope
def lambda_handler(event, context, metrics):
    route_key = event['routeKey']

    response_body = {'Message': 'Unsupported route'}
    status_code = 400
    headers = {'Content-Type': 'application/json'}

    # Put common business metrics using EMF
    metric_payload = {}
    metrics.put_dimensions({'Service': 'Resources'})
    metrics.put_metric('ProcessedResources', 1, 'Count')
    metrics.set_property('requestId', event['requestContext']['requestId'])
    metrics.set_property('routeKey', event['routeKey'])

    try:
        # Get all resources
        if route_key == 'GET /locations/{locationid}/resources':
            metric_payload['operation'] = 'GET'
            metric_payload['locationid'] = event['pathParameters']['locationid']
            ddb_response = ddbTable.query(
                IndexName='locationidGSI',
                KeyConditionExpression='locationid = :locationid',
                ExpressionAttributeValues={
                    ':locationid': event['pathParameters']['locationid']
                }
            )
            response_body = ddb_response['Items']
            status_code = 200
        # Resource CRUD operations
        if route_key == 'GET /locations/{locationid}/resources/{resourceid}':
            metric_payload['operation'] = 'GET'
            metric_payload['locationid'] = event['pathParameters']['locationid']
            metric_payload['resourceid'] = event['pathParameters']['resourceid']
            ddb_response = ddbTable.get_item(
                Key={'resourceid': event['pathParameters']['resourceid']}
            )
            if 'Item' in ddb_response:
                response_body = ddb_response['Item']
            else:
                response_body = {}
            status_code = 200
        if route_key == 'DELETE /locations/{locationid}/resources/{resourceid}':
            metric_payload['operation'] = 'DELETE'
            metric_payload['locationid'] = event['pathParameters']['locationid']
            metric_payload['resourceid'] = event['pathParameters']['resourceid']
            ddbTable.delete_item(
                Key={'resourceid': event['pathParameters']['resourceid']}
            )
            response_body = {}
            status_code = 200
        if route_key == 'PUT /locations/{locationid}/resources':
            request_json = json.loads(event['body'])
            request_json['locationid'] = event['pathParameters']['locationid']
            request_json['timestamp'] = datetime.now().isoformat()
            if 'resourceid' not in request_json:
                request_json['resourceid'] = str(uuid.uuid1())
            metric_payload['operation'] = 'DELETE'
            metric_payload['locationid'] = event['pathParameters']['locationid']
            metric_payload['resourceid'] = request_json['resourceid']
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
