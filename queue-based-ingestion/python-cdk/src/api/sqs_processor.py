# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import json
import os
lambda_client = boto3.client('lambda')
def lambda_handler(event, context):
    dynamo_table_name = os.environ['SQS_MESSAGE_STORE_TABLE_NAME']
    simulator_function_name = os.environ['BATCH_SIMULATOR_FUNCTION_NAME']
    dynamo_client = boto3.resource('dynamodb').Table(dynamo_table_name)
    
    print('incoming request payload from SQS'+ str(event)) 
    for record in event['Records']:
        print(' processing record' + str(record))
        job_request_paylod = create_job_reqeust(record)
        dynamo_client.put_item(Item=job_request_paylod)
       # batch_payload = record
        print('invoking simulator function' + simulator_function_name)
        # Invoke another Function
        batch_simulator_response = lambda_client.invoke(
            FunctionName=simulator_function_name,
            Payload=json.dumps(job_request_paylod)
        )
        print('response from simulator function : ' + str(batch_simulator_response))
        reponse_payload= json.loads(batch_simulator_response['Payload'].read().decode("utf-8"))
        print ('response  payload from simulator function '+ str(reponse_payload))
        response_body= reponse_payload ['body']
        job_status = response_body ['jobStatus']
        
        job_request_paylod ['jobStatus'] = job_status
        job_request_paylod ['jobPayloadLocation'] = response_body ['jobPayloadLocation']
        job_request_paylod ['jobPayloadKey'] = response_body ['jobPayloadKey']
        dynamo_client.put_item(Item=job_request_paylod)
        print (' sucessfuly updated  job status in DynamoDB '+  str(job_request_paylod))

def create_job_reqeust(record):
    job_request =  { 
        "jobRequestId" :record ["messageId"],
        "jobRequestPayload": record["body"],
        "SentTimestamp" : record["attributes"]["SentTimestamp"],
        "jobStatus":"Submitted"
    }
    return job_request