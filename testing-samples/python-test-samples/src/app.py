from asyncio.log import logger
import boto3
        
def lambda_handler(event, context):

    s3_client = boto3.client('s3')
    s3_response = s3_client.list_buckets()
    s3_response = s3_response["Buckets"]
    bucket_list = ""

    for bucket in s3_response:
        bucket_list += bucket["Name"] + " | "

    print("Hello logfile!")

    return {
        "statusCode": 200,
        "body": bucket_list 
    }
