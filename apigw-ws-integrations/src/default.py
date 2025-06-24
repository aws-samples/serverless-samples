# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json

def lambda_handler(event, context):
    response={}
    response['isBase64Encoded']='false'
    response['statusCode']='200'
    response['headers']={}
    response['body']=json.dumps(event)
    return response
