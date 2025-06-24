# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import boto3
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.batch import (
    BatchProcessor,
    EventType,
    process_partial_response,
)
from aws_lambda_powertools.utilities.data_classes.sqs_event import SQSRecord
from aws_lambda_powertools.utilities.typing import LambdaContext

processor = BatchProcessor(event_type=EventType.SQS)
logger = Logger()

FULFILLMENT_TABLE = os.environ['FULFILLMENT_TABLE']
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(FULFILLMENT_TABLE)

logger = Logger()

# process each message in batch
def record_handler(record: SQSRecord):
    # if json string data, otherwise record.body for str
    payload: str = record.json_body
    logger.info(payload)
    try:
        response = table.put_item(Item=payload)
        logger.info("saved to DDB", extra={'response': response})
    except Exception as e:
        logger.error(e)
        raise e


@logger.inject_lambda_context
def lambda_handler(event, context: LambdaContext):
    return process_partial_response(
        event=event,
        record_handler=record_handler,
        processor=processor,
        context=context,
    )
