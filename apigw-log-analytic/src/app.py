# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
# Lambda enrichement code is based https://computeblog-us-east-1.s3.amazonaws.com/apigateway-visualize-usageplans/api-gateway-access-logs-visualization-enrichment-function.zip

import boto3
import base64
import json
import ast
from datetime import datetime

apigw = boto3.client('apigateway')
# apiKey:apiStage:apiKeyId -> Usage Plan Name
usage_plan_mapping = {}
# apiKeyId -> customer name
customer_mapping = {}

# Get all the APIGW Usage Plans for this account
# TODO: Paginate results for >25 plans
account_usage_plans = apigw.get_usage_plans()

#print(account_usage_plans)

# For each APIGW Usage Plan, get the APIs and API Stages it's applied to 
# and the keys of the customers in that plan
for plan in account_usage_plans['items']:
    plan_id = plan['id']
    plan_name = plan['name']
    plan_api_stages = plan['apiStages']
    # Get all the API Keys (customers) assigned to this plan
    plan_keys = apigw.get_usage_plan_keys(usagePlanId=plan_id)
    
    # For each API Key, store the mapping to the customer name.
    # Also store the mapping from api-apiStage-apiKey to usage plan name
    # TODO: Paginate results for > 25 customers in a plan
    for plan_key in plan_keys['items']:
        key_id = plan_key['id']
        key_name = plan_key['name']
        customer_mapping[key_id] = key_name
        
        for api_stage in plan_api_stages:
            usage_plan_lookup = api_stage['apiId'] + ':' + api_stage['stage'] + ":" + key_id
            usage_plan_mapping[usage_plan_lookup] = plan_name
                

def lambda_handler(event, context):
    
    print(event)
    output = []

    for record in event['records']:
        print(record['recordId'])
        # Decode from base64 to binary
        binary_payload = base64.b64decode(record['data'])
        # print("Base64 decoded payload is " + str(payload))
        
        # Decode binary to string and convert to dictionary
        payload_dict = ast.literal_eval(binary_payload.decode("UTF-8"))
        # Add customer name to payload via API Key Id lookup
        
        print(payload_dict)
        
        # Add customer name to payload via API Key Id lookup if key exists
        if 'identityApiKeyId' in payload_dict:
            payload_dict['identity.apiKeyName'] = customer_mapping.get(payload_dict['identityApiKeyId'], '-') 
            usage_plan_lookup = payload_dict['apiId'] + ':' + payload_dict['stage'] + ":" + payload_dict['identityApiKeyId']
            payload_dict['identity.usagePlanName'] = usage_plan_mapping.get(usage_plan_lookup, '-')
        else:
            payload_dict['identity.apiKeyName'] = '-'
        
        
        
    
        # Input timestamp string
        requestTime = payload_dict['requestTime']
        datetime_obj = datetime.strptime(requestTime, "%d/%b/%Y:%H:%M:%S %z")
        
        # Convert it to the desired format
        formatted_date = datetime_obj.strftime("%Y-%m-%dT%H:%M:%S")
        payload_dict['requestTime'] = formatted_date
        
    
        
        # Encode back to binary, adding a newline to the end of the string
        print("Updated dict payload is " + str(payload_dict))
        new_payload_string = json.dumps(payload_dict) + '\n'
        new_payload_binary = new_payload_string.encode('utf-8') 
        
        #print(new_payload_binary)
        output_record = {
            'recordId': record['recordId'],
            'result': 'Ok',
            'data': base64.b64encode(new_payload_binary)
        }
        output.append(output_record)

    print('Successfully processed {} records.'.format(len(event['records'])))

    return {'records': output}


    
    
