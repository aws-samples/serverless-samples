# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.event_handler.exceptions import BadRequestError
from aws_lambda_powertools.utilities.typing import LambdaContext
from UserAbacSession import UserAbacSession
from OrderStore import OrderStore

import urllib.parse
import requests
import boto3
from aws_requests_auth.aws_auth import AWSRequestsAuth
from datetime import datetime, timezone
import os
import json

logger = Logger()
app = APIGatewayRestResolver()

# Load environment variables
VPCE_DNS_NAME = os.environ['VPCE_DNS_NAME']
PAYMENTS_API_DNS_NAME = os.environ['PAYMENTS_API_DNS_NAME']
API_STAGE = os.environ['API_STAGE']
FULFILLMENT_QUEUE_URL = os.environ['FULFILLMENT_QUEUE_URL']

# Sigv4 signing config for accessing private payment API protected with
# IAM auth
boto3_session = boto3.Session()
credentials = boto3_session.get_credentials()
endpoint = f"https://{PAYMENTS_API_DNS_NAME}/{API_STAGE}/makePayment"

auth = AWSRequestsAuth(
    aws_access_key=credentials.access_key,
    aws_secret_access_key=credentials.secret_key,
    aws_token=credentials.token,
    aws_host=urllib.parse.urlparse(endpoint).netloc,
    aws_region=os.environ['AWS_REGION'],
    aws_service="execute-api",
)

# Initialize SQS client to publish orders to fulfillment service
sqs = boto3_session.client(
    service_name='sqs',
    endpoint_url=f"https://sqs.{os.environ['AWS_REGION']}.amazonaws.com"
)

# Payment service integration
def process_payment(cust_name, price):
    payload = {
        "id": "ABC1234",
        "name": cust_name,
        "price": price,
        "card": "xxxxxx"
    }
    try:
        res = requests.post(
            f"https://{VPCE_DNS_NAME}/{API_STAGE}/makePayment",
            auth=auth,
            headers={
                'Accept': 'application/json',
                'Host': PAYMENTS_API_DNS_NAME},
            json=payload)
        logger.info(f"Payment processing: {res.status_code}, {res.json()}")
        if res.status_code != 200:
            raise BadRequestError("payment processing error")
    except Exception as e:
        logger.error(e)
        raise BadRequestError("payment processing error")
    return res.json()

# Fulfillment service integration
def publish_to_fulfillment_service(order_id, item, order_date):
    message = {
        "order_id": order_id,
        "order_date": order_date,
        "item": item,
        "order_status": "PENDING"
    }
    # publish to sqs
    try:
        res = sqs.send_message(
            QueueUrl=FULFILLMENT_QUEUE_URL,
            MessageBody=json.dumps(message)
        )
        logger.info(f"Published to SQS: {res}")
    except Exception as e:
        logger.error(e)
        raise BadRequestError("fulfillment publish error")
    return res

# Check if user has admin priveleges based on Cognito groups claim
def is_admin(claims):
    if claims.get('cognito:groups'):
        return "Admins" in claims['cognito:groups']
    return False

# Retrieve orders
@app.get("/listOrders")
def list_orders():
    try:
        claims = app.current_event.request_context.authorizer.claims
        user_id = claims['sub']
    except Exception as e:
        logger.error(e)
        raise BadRequestError("invalid order data")

    logger.info("list_orders", extra={'user_id': user_id})
    user_session = UserAbacSession(user_id)
    order_store = OrderStore(user_session, is_admin(claims))
    return order_store.retrieve()

# Place an order
@app.post("/placeOrder")
def place_order():
    logger.info(
        "APIGatewayProxyEvent", extra={
            'APIGatewayProxyEvent': app.current_event})
    try:
        # POST payload
        order_data = app.current_event.json_body

        # user context from payload
        claims = app.current_event.request_context.authorizer.claims
        user_id = claims['sub']
        username = claims['cognito:username']
        order_data['username'] = username

        # process payment
        order_data['order_date'] = datetime.now(timezone.utc).isoformat()
        payment = process_payment(username, order_data['amount'])

        # publish to fulfillment service
        fulfillment = publish_to_fulfillment_service(
            order_data['order_id'], order_data['item'], order_data['order_date'])
    except Exception as e:
        logger.error(e)
        raise BadRequestError(f"invalid order data: {order_data}")

    logger.info(
        "place_order",
        extra={
            'user_id': user_id,
            'order_data': order_data})

    # store order
    user_session = UserAbacSession(user_id)
    order_store = OrderStore(user_session, is_admin(claims))
    return order_store.store(order_data)


def lambda_handler(event: dict, context: LambdaContext):
    logger.info("event", extra={'event': event})
    return app.resolve(event, context)
