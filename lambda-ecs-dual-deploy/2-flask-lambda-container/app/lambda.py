# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json, requests

def handler(event, context):
    response = {}
    r = requests.get('http://127.0.0.1:8000')
    response['statusCode']=200
    response['body']="Response via Lambda: ["+r.text+"]"
    print(response)
    return response


