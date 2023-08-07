# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import json
import os
import random

DEFAULT_WEATHER_DATA_STORE = 'weather_sample_data.dat'
def lambda_handler(event, context):
    bucket_name = os.environ['BATCH_SIMULATOR_BUCKET_NAME']
    #'aws-sqs-ingestion-job-payload-bucket'
    print('Input reqeust event:'+ str(event))
    s3_client = boto3.client('s3')
    messageID = event['jobRequestId']
    print(messageID)

    json_payload = generateBatchPayload(event)

    s3_client.put_object( 
     Body=json.dumps(json_payload),
     Bucket=bucket_name,
     Key=messageID
    )
    response =  {
        "jobStatus": "complete",
        "jobPayloadLocation": bucket_name,
        "jobPayloadKey" :messageID,
        "jobRequestId" : messageID
        }

    return {
        "statusCode": 200,
        "body": response
    }

def generateBatchPayload(event) :
    
    MAX_RECORDS= 100
    weather_data_store_location= os.environ.get("WEATHER_DATA_STORE",DEFAULT_WEATHER_DATA_STORE)
    lines = open(weather_data_store_location).read().splitlines()
    output_json  = json.loads ('{"weatherData":[]}')
    print(output_json)
    for ctr in range (1,MAX_RECORDS):
        file_record = random.choice(lines)
        file_record_split = file_record.split("|")
        json_record =  {
            "station" : file_record_split[0],
            "geoLocation" : file_record_split[1],
            "localTime": file_record_split[2],
            "conditions" : file_record_split[3],
            "temperature": file_record_split[4],
            "pressure" : file_record_split[5],
            "humidity" : file_record_split[6]
        }
        output_json["weatherData"].append(json_record)
        #print (json_record) 
    print('Genearted Payload -' + str(output_json)) 
    return output_json 
    