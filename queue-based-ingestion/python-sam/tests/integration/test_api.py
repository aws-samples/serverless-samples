# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import requests
import re
from time import sleep

JOB_REQUEST_MESSAGE_PAYLOAD={ "testmessage": "sample-message-012" }
INVALID_JOB_ID = '38573c4b-07ad-4ccf-8241-869ffe16d566'
INVALID_JOB_ID_ERROR_MSG= "No Job data found for Job Id" 

def test_submit_job_request_no_authentication(global_config):
    #print(global_config["regularUserIdToken"])
    #print(global_config["JobRequestAPIEndpoint"])

    response = requests.post(
        global_config["JobRequestAPIEndpoint"] + '/submit-job-request',
        data=json.dumps(JOB_REQUEST_MESSAGE_PAYLOAD),
        #headers={'Authorization': global_config["regularUserIdToken"], 'Content-Type': 'application/json'}
    )
    print(str(response))
    assert response.status_code == 401

def test_submit_job_request_with_authentication(global_config):
    response = requests.post(
        global_config["JobRequestAPIEndpoint"] + '/submit-job-request',
        data=json.dumps(JOB_REQUEST_MESSAGE_PAYLOAD),
        headers={'Authorization': global_config["regularUserIdToken"], 'Content-Type': 'application/json'}
    )
    print(" submit-job-request response" +str(response.text))
    assert response.status_code == 200

def test_get_job_staus_valid(global_config):
    response = requests.post(
        global_config["JobRequestAPIEndpoint"] + '/submit-job-request',
        data=json.dumps(JOB_REQUEST_MESSAGE_PAYLOAD),
        headers={'Authorization': global_config["regularUserIdToken"], 'Content-Type': 'application/json'}
    )
    response_data=response.text

    print(" submit-job-request response" +str(response.text))

    # Get message Id from response
    regex = r"<MessageId>.*</MessageId>"
    message_id_str = re.search(regex,response_data, flags=0)
    message_id =message_id_str.group()[11:47]
    print("Matched message_id "+ message_id)

    #add wait time to let simulator fucntion finsih the job
    sleep(5)

    response = requests.get(
        global_config["JobRequestAPIEndpoint"] + '/job-status/'+message_id,
        headers={'Authorization': global_config["regularUserIdToken"], 'Content-Type': 'application/json'}
    )

    response_data=json.loads(response.text)
    print ('get job status response ' + str(response_data))
    
    assert response_data['jobStatus'] == "complete"
    assert response_data['jobRequestId'] == message_id
    assert "https://" in response_data['jobProcessedPayloadLink']
    assert response.status_code == 200

def test_get_job_staus_invalid(global_config):
    print("Before test case 4")
    response = requests.post(
        global_config["JobRequestAPIEndpoint"] + '/submit-job-request',
        data=json.dumps(JOB_REQUEST_MESSAGE_PAYLOAD),
        headers={'Authorization': global_config["regularUserIdToken"], 'Content-Type': 'application/json'}
    )
    print(" submit-job-request response" +str(response.text))
    
    response_data=response.text

    # dont Get message Id from response use dummy message id 
    response = requests.get(
        global_config["JobRequestAPIEndpoint"] + '/job-status/'+INVALID_JOB_ID,
        headers={'Authorization': global_config["regularUserIdToken"], 'Content-Type': 'application/json'}
    )

    response_data=json.loads(response.text)
    print ('get job status response ' + str(response_data))

    assert INVALID_JOB_ID_ERROR_MSG in response_data['Error Message']
    