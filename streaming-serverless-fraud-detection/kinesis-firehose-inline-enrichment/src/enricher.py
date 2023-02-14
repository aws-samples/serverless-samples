# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import base64
import json
import boto3

FRAUD_DETECTOR_ID = os.getenv("FRAUD_DETECTOR_ID", None)
client = boto3.client("frauddetector")


def lambda_handler(event, context):
    output = []
    for record in event["records"]:
        payload = json.loads(base64.b64decode(record["data"]).decode("utf-8"))

        # Call Amazon Fraud Detector with the record data and enrich payload
        response = client.get_event_prediction(
            detectorId=FRAUD_DETECTOR_ID,
            eventId=payload["transaction_id"],
            eventTypeName="transaction_event",
            entities=[{"entityType": "customer", "entityId": "unknown"}],
            eventTimestamp=payload["transaction_timestamp"],
            eventVariables={
                "customer_email": payload["customer_email"],
                "order_price": payload["order_price"],
                "product_category": payload["product_category"],
                "ip_address": payload["ip_address"],
                "card_bin": payload["card_bin"]
            }
        )

        # enrich the payload with fraud detection results
        payload["fraud_detection_outcome"] = response["ruleResults"][0]["outcomes"][0]
        payload["fraud_detection_response"] = response

        # return data to the Kinesis Firehose
        output_record = {
            "recordId": record["recordId"],
            "result": "Ok",
            "data": base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
        }
        output.append(output_record)

    print('Successfully processed {} records.'.format(len(event['records'])))
        
    return {"records": output}
