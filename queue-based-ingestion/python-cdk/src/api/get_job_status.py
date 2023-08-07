# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import os
from botocore.exceptions import ClientError
def lambda_handler(event, context):
    
    dynamo_table_name = os.environ['SQS_MESSAGE_STORE_TABLE_NAME']
    s3_client = boto3.client('s3')

    expiration = 3600

    print(str(event))

    url_path_parameters = event['pathParameters']
    job_id_parameter = url_path_parameters['job-id']
    print(str(job_id_parameter))

    dynamo_client = boto3.resource('dynamodb').Table(dynamo_table_name)
    dynamo_response = dynamo_client.get_item(Key={'jobRequestId': job_id_parameter})
    print('dynamodb query response ' + str(dynamo_response))
    
    if 'Item' in dynamo_response :
        dynamo_record = dynamo_response ['Item']
        print('dynamodb dynamo_record ' + str(dynamo_record))
        job_status = dynamo_record ['jobStatus']
        job_request_id = dynamo_record['jobRequestId']
        
        if job_status == 'complete':
            job_payload_location = dynamo_record['jobPayloadLocation']
            print('job_payload_location '+job_payload_location)
            job_payload_key = dynamo_record['jobPayloadKey']

            # Generate S3 Pre-signed URL only if Job status is complete  
            try:
                S3_presigned_url = s3_client.generate_presigned_url('get_object',
                                                            Params={'Bucket': job_payload_location,
                                                                    'Key': job_payload_key},
                                                            ExpiresIn=expiration)
                print(str(S3_presigned_url))                                            
            except ClientError as e:
                print.error(e)
                return {
                    "Error Message" : "Error While generating S3 Pre-signed URL for  Job Id : " + job_id_parameter
                } 
            response_str={
                "jobStatus": job_status ,
                "jobId": job_id_parameter,
                "jobProcessedPayloadLink" :S3_presigned_url,
                "jobRequestId" :job_request_id
                }
            print ("sending response.... "+str(response_str))
            return {
                "statusCode":"200",
                "isBase64Encoded": False,
                "body":str(response_str)
            }
        else :
            # Since Job status is not complete dont add  S3 Pre-signed URL to response   
            response_str_pending ={
                "jobStatus": job_status ,
                "jobId": job_id_parameter,
                "jobRequestId" :job_request_id
            }
            return {
                "statusCode":"200",
                "isBase64Encoded": False,
                "body":str(response_str_pending)
            }
    else : 
        return {
            "Error Message" : "No Job data found for Job Id : " + job_id_parameter
        }    

