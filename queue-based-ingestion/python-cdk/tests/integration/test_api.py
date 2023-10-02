# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import requests


new_job_request = {"testmessage": "sample job request int testing"}



def test_access_to_the_api_without_authentication(global_config):
    response = requests.get(global_config["APIEndpointURL"] + 'submit-job-request')
    assert response.status_code == 403

def test_allow_submit_job_api(global_config):
    api_url = global_config["APIEndpointURL"] + f'submit-job-request'
    response = requests.post(
        api_url,
        data=json.dumps(new_job_request),
        headers={'Authorization': global_config["regularUserIdToken"], 'Content-Type': 'application/json'}
    )
    assert response.status_code == 200
    data = json.loads(response.text)
    
    assert not ((data.get("SendMessageResponse").get("SendMessageResult").get("MessageId")) == "")
    global submitted_job_request_id
    submitted_job_request_id = (data.get("SendMessageResponse").get("SendMessageResult").get("MessageId"))

def test_allow_get_job_status(global_config):
    api_url = global_config["APIEndpointURL"] + "job-status/"+submitted_job_request_id
    response = requests.get(
        api_url,
        headers={'Authorization': global_config["regularUserIdToken"]}
    )

    assert response.status_code == 200
    response_data = response.text.replace("\'", "\"")
    data = json.loads(response_data)
    assert (data.get("jobRequestId") == submitted_job_request_id)
    assert (data.get("jobStatus") == "Submitted" or data.get("jobStatus") == "complete")