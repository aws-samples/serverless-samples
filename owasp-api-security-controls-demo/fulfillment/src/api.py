# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.event_handler.exceptions import BadRequestError
from aws_lambda_powertools.utilities.typing import LambdaContext
from boto3.dynamodb.conditions import Key

import boto3
import os

logger = Logger()
app = APIGatewayRestResolver()

FULFILLMENT_TABLE = os.environ['FULFILLMENT_TABLE_NAME']
ORDER_STATUS_INDEX = os.environ['ORDER_STATUS_INDEX']

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(FULFILLMENT_TABLE)

# List outstanding orders
@app.get("/listPendingOrders")
def list_orders():
    try:
        response = table.query(
            IndexName=ORDER_STATUS_INDEX,
            KeyConditionExpression=Key('order_status').eq("PENDING")
        )
        logger.info(f"Pending orders: {response}")
    except Exception as e:
        logger.error(e)
        raise BadRequestError("invalid order data")
    return response

# Update order status
@app.post("/updateOrderStatus")
def place_order():
    logger.info(
        "APIGatewayProxyEvent", extra={
            'APIGatewayProxyEvent': app.current_event})
    try:
        order_data = app.current_event.json_body
        response = table.update_item(
            Key={
                'order_id': order_data['order_id'],
                'order_date': order_data['order_date']
            },
            UpdateExpression="set order_status=:s",
            ExpressionAttributeValues={
                ':s': order_data['order_status']
            },
            ReturnValues="UPDATED_NEW"
        )
    except Exception as e:
        logger.error(e)
        raise BadRequestError(f"invalid order data: {order_data}")

    return response["Attributes"]


def lambda_handler(event: dict, context: LambdaContext):
    logger.info("event", extra={'event': event})
    return app.resolve(event, context)
