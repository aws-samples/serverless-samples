# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import boto3
import json
import base64

FRAUD_DETECTION_WORKFLOW = os.getenv('FRAUD_DETECTION_WORKFLOW', None)
client = boto3.client('stepfunctions')

def lambda_handler(event, context):
    #print("Received event: " + json.dumps(event))
    batch_data_array=[]

    # Build array of the transactions records to be passed to the Step Functions workflow execution
    for record in event['Records']:
        # Kinesis data is base64 encoded so decode here
        payload = base64.b64decode(record['kinesis']['data']).decode('utf-8')
        batch_data_array.append (json.loads(payload))
    
    #print(batch_data_array)
    response = client.start_execution(
        stateMachineArn=FRAUD_DETECTION_WORKFLOW,
        name=context.aws_request_id,
        input=json.dumps(batch_data_array)
    )
    return 
