# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import boto3
import copy

appsync_client = boto3.client('appsync')
mappings_base_path = "./src/mapping_templates/"

location_context = {
    "arguments":
        {
            "locationid": "1234567890",
            "name": "Location Name",
            "description": "Location Description",
            "imageUrl": "https://www.example.com/image.jpg"
        },
    "result": {
        "locationid": "1234567890",
        "imageUrl": "https://www.example.com/image.jpg",
        "name": "Location Name",
        "description": "Location Description",
        "timestamp": "2023-01-01T00:00:00.000Z"
    }
}

resource_context = {
    "arguments":
        {
            "resourceid": "1234567890",
            "locationid": "abcdefghij",
            "name": "Resource Name",
            "description": "Resource Description",
            "type": "Resource Type"
        },
    "result":
        {
            "resourceid": "1234567890",
            "locationid": "abcdefghij",
            "name": "Resource Name",
            "description": "Resource Description",
            "type": "Resource Type",
            "timestamp": "2023-01-01T00:00:00.000Z"
        }
}

booking_context = {
    "arguments":
        {
            "bookingid": "1234567890",
            "resourceid": "abcdefghij",
        },
    "identity":
        {
            "sub": "123456-abcdeefg-7890",
            "issuer": "",
            "username": "johndoe",
            "claims": {},
            "sourceIp": [
                "x.x.x.x"
            ],
            "defaultAuthStrategy": "ALLOW"
        },
    "result":
        {
            "bookingid": "1234567890",
            "resourceid": "abcdefghij",
            "starttimeepochtime": 1672578000,
            "userid": "123456-abcdeefg-7890",
            "timestamp": "2023-01-01T00:00:00.000Z"
        }
}


def test_create_location_resolver_with_location_id():
    context = copy.deepcopy(location_context)
    # Test request mapping template
    with open(mappings_base_path+'create_location_request.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    assert evaluation_result["operation"] == "PutItem"
    assert evaluation_result["key"]["locationid"]["S"] == context["arguments"]["locationid"]
    assert evaluation_result["attributeValues"]["name"]["S"] == context["arguments"]["name"]
    assert evaluation_result["attributeValues"]["description"]["S"] == context["arguments"]["description"]
    assert evaluation_result["attributeValues"]["timestamp"]["S"] is not None

    # Test response mapping template
    with open(mappings_base_path+'create_location_response.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    # Check that all result fields are present in the response after transformation
    for key in evaluation_result:
        assert evaluation_result[key] == context["result"][key]


def test_create_location_resolver_without_location_id():
    context = copy.deepcopy(location_context)
    del context["arguments"]["locationid"]

    # Test request mapping template
    with open(mappings_base_path+'create_location_request.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    assert evaluation_result["operation"] == "PutItem"
    assert evaluation_result["key"]["locationid"]["S"] is not None
    assert evaluation_result["attributeValues"]["name"]["S"] == context["arguments"]["name"]
    assert evaluation_result["attributeValues"]["description"]["S"] == context["arguments"]["description"]
    assert evaluation_result["attributeValues"]["timestamp"]["S"] is not None

    # Test response mapping template
    with open(mappings_base_path+'create_location_response.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    # Check that all result fields are present in the response after transformation
    for key in evaluation_result:
        assert evaluation_result[key] == context["result"][key]


def test_delete_location_resolver():
    context = copy.deepcopy(location_context)

    # Test request mapping template
    with open(mappings_base_path+'delete_location_request.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    assert evaluation_result["operation"] == "DeleteItem"
    assert evaluation_result["key"]["locationid"]["S"] == context["arguments"]["locationid"]

    # Test response mapping template
    with open(mappings_base_path+'delete_location_response.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    assert evaluation_result == context["result"]["locationid"]


def test_get_single_location_resolver():
    context = copy.deepcopy(location_context)

    # Test request mapping template
    with open(mappings_base_path+'get_location_request.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    assert evaluation_result["operation"] == "GetItem"
    assert evaluation_result["key"]["locationid"]["S"] == context["arguments"]["locationid"]

    # Test response mapping template
    with open(mappings_base_path+'get_location_response.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    # Check that all result fields are present in the response after transformation
    for key in evaluation_result:
        assert evaluation_result[key] == context["result"][key]


def test_get_all_location_resolver():
    context = {
        "arguments":
            {
            },
        "result": {
                "items": [
                    {
                        "locationid": "0",
                        "imageUrl": "url",
                        "name": "name",
                        "description": "description",
                        "timestamp": "2023-01-01T00:00:00.000Z"
                    },
                    {
                        "locationid": "2",
                        "imageUrl": "url2",
                        "name": "name2",
                        "description": "description2",
                        "timestamp": "2023-01-01T00:00:00.000Z"
                    },
                    {
                        "locationid": "1",
                        "imageUrl": "url1",
                        "name": "name1",
                        "description": "description1",
                        "timestamp": "2023-01-01T00:00:00.000Z"
                    }
                ],
                "scannedCount": 3
        }
    }

    # Test request mapping template
    with open(mappings_base_path+'get_locations_request.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    assert evaluation_result["operation"] == "Scan"

    # Test response mapping template
    with open(mappings_base_path+'get_locations_response.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    assert evaluation_result is not None
    assert len(evaluation_result) == len(context["result"]["items"])
    # Check that all items in the results list are present in the response after transformation
    for i in range(len(evaluation_result)):
        # Check that all result fields are present in the response after transformation
        for key in evaluation_result[i]:
            assert evaluation_result[i][key] == context["result"]["items"][i][key]


def test_create_resource_resolver_with_resource_id():
    context = copy.deepcopy(resource_context)

    # Test request mapping template
    with open(mappings_base_path+'create_resource_request.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    assert evaluation_result["operation"] == "PutItem"
    assert evaluation_result["key"]["resourceid"]["S"] == context["arguments"]["resourceid"]
    assert evaluation_result["attributeValues"]["locationid"]["S"] == context["arguments"]["locationid"]
    assert evaluation_result["attributeValues"]["name"]["S"] == context["arguments"]["name"]
    assert evaluation_result["attributeValues"]["description"]["S"] == context["arguments"]["description"]
    assert evaluation_result["attributeValues"]["type"]["S"] == context["arguments"]["type"]
    assert evaluation_result["attributeValues"]["timestamp"]["S"] is not None

    # Test response mapping template
    with open(mappings_base_path+'create_resource_response.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    # Check that all result fields are present in the response after transformation
    for key in evaluation_result:
        assert evaluation_result[key] == context["result"][key]


def test_create_resource_resolver_without_resource_id():
    context = copy.deepcopy(resource_context)
    del context["arguments"]["resourceid"]

    # Test request mapping template
    with open(mappings_base_path+'create_resource_request.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    assert evaluation_result["operation"] == "PutItem"
    assert evaluation_result["key"]["resourceid"]["S"] is not None
    assert evaluation_result["attributeValues"]["locationid"]["S"] == context["arguments"]["locationid"]
    assert evaluation_result["attributeValues"]["name"]["S"] == context["arguments"]["name"]
    assert evaluation_result["attributeValues"]["description"]["S"] == context["arguments"]["description"]
    assert evaluation_result["attributeValues"]["type"]["S"] == context["arguments"]["type"]
    assert evaluation_result["attributeValues"]["timestamp"]["S"] is not None

    # Test response mapping template
    with open(mappings_base_path+'create_resource_response.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    # Check that all result fields are present in the response after transformation
    for key in evaluation_result:
        assert evaluation_result[key] == context["result"][key]


def test_delete_resource_resolver():
    context = copy.deepcopy(resource_context)

    # Test request mapping template
    with open(mappings_base_path+'delete_resource_request.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    assert evaluation_result["operation"] == "DeleteItem"
    assert evaluation_result["key"]["resourceid"]["S"] == context["arguments"]["resourceid"]

    # Test response mapping template
    with open(mappings_base_path+'delete_resource_response.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    assert evaluation_result == context["result"]["resourceid"]


def test_get_single_resource_resolver():
    context = copy.deepcopy(resource_context)

    # Test request mapping template
    with open(mappings_base_path+'get_resource_request.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    assert evaluation_result["operation"] == "GetItem"
    assert evaluation_result["key"]["resourceid"]["S"] == context["arguments"]["resourceid"]

    # Test response mapping template
    with open(mappings_base_path+'get_resource_response.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    # Check that all result fields are present in the response after transformation
    for key in evaluation_result:
        assert evaluation_result[key] == context["result"][key]


def test_get_resources_for_location_resolver():
    context = {
        "arguments":
            {
                "locationid": "abcdefghij",
            },
        "result": {
                "items": [
                    {
                        "resourceid": "0",
                        "locationid": "abcdefghij",
                        "name": "Resource Name 0",
                        "description": "Resource Description 0",
                        "type": "Resource Type 0",
                        "timestamp": "2023-01-01T00:00:00.000Z"
                    },
                    {
                        "resourceid": "1",
                        "locationid": "abcdefghij",
                        "name": "Resource Name 1",
                        "description": "Resource Description 1",
                        "type": "Resource Type 1",
                        "timestamp": "2023-01-01T00:00:00.000Z"
                    }
                ],
                "scannedCount": 2
        },
    }

    # Test request mapping template
    with open(mappings_base_path+'get_resources_for_location_request.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    assert evaluation_result["operation"] == "Query"
    assert evaluation_result["query"]["expression"] == "locationid = :locationid"
    assert evaluation_result["query"]["expressionValues"][":locationid"]["S"] == context["arguments"]["locationid"]
    assert evaluation_result["index"] == "locationidGSI"

    # Test response mapping template
    with open(mappings_base_path+'get_resources_for_location_response.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    assert evaluation_result is not None
    assert len(evaluation_result) == len(context["result"]["items"])
    # Check that all items in the results list are present in the response after transformation
    for i in range(len(evaluation_result)):
        # Check that all result fields are present in the response after transformation
        for key in evaluation_result[i]:
            assert evaluation_result[i][key] == context["result"]["items"][i][key]


def test_create_booking_resolver_with_booking_id():
    context = copy.deepcopy(booking_context)

    # Test request mapping template
    with open(mappings_base_path+'create_booking_request.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    assert evaluation_result["operation"] == "PutItem"
    assert evaluation_result["key"]["bookingid"]["S"] == context["arguments"]["bookingid"]
    assert evaluation_result["attributeValues"]["resourceid"]["S"] == context["arguments"]["resourceid"]
    assert evaluation_result["attributeValues"]["userid"]["S"] == context["identity"]["sub"]
    assert evaluation_result["attributeValues"]["timestamp"]["S"] is not None

    # Test response mapping template
    with open(mappings_base_path+'create_booking_response.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    # Check that all result fields are present in the response after transformation
    for key in evaluation_result:
        assert evaluation_result[key] == context["result"][key]


def test_create_booking_resolver_without_booking_id():
    context = copy.deepcopy(booking_context)
    del context["arguments"]["bookingid"]

    # Test request mapping template
    with open(mappings_base_path+'create_booking_request.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    assert evaluation_result["operation"] == "PutItem"
    assert evaluation_result["key"]["bookingid"]["S"] is not None
    assert evaluation_result["attributeValues"]["resourceid"]["S"] == context["arguments"]["resourceid"]
    assert evaluation_result["attributeValues"]["userid"]["S"] == context["identity"]["sub"]
    assert evaluation_result["attributeValues"]["timestamp"]["S"] is not None

    # Test response mapping template
    with open(mappings_base_path+'create_booking_response.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    # Check that all result fields are present in the response after transformation
    for key in evaluation_result:
        assert evaluation_result[key] == context["result"][key]


def test_get_single_booking_resolver():
    context = copy.deepcopy(booking_context)

    # Test request mapping template
    with open(mappings_base_path+'get_booking_request.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    assert evaluation_result["operation"] == "GetItem"
    assert evaluation_result["key"]["bookingid"]["S"] == context["arguments"]["bookingid"]

    # Test response mapping template
    with open(mappings_base_path+'get_booking_response.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    # Check that all result fields are present in the response after transformation
    for key in evaluation_result:
        assert evaluation_result[key] == context["result"][key]


def test_get_bookings_for_resource_resolver():
    context = {
        "arguments":
            {
                "resourceid": "1234567890",
            },
        "result": {
                "items": [
                    {
                        "bookingid": "0",
                        "resourceid": "1234567890",
                        "starttimeepochtime": 1672578000,
                        "userid": "123456-abcdeefg-7890",
                        "timestamp": "2023-01-01T00:00:00.000Z"
                    },
                    {
                        "bookingid": "1",
                        "resourceid": "1234567890",
                        "starttimeepochtime": 1672578000,
                        "userid": "abcd-123456-efgh",
                        "timestamp": "2023-01-01T00:00:00.000Z"
                    }
                ],
                "scannedCount": 2
        }
    }

    # Test request mapping template
    with open(mappings_base_path+'get_bookings_for_resource_request.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    assert evaluation_result["operation"] == "Query"
    assert evaluation_result["query"]["expression"] == "resourceid = :resourceid"
    assert evaluation_result["query"]["expressionValues"][":resourceid"]["S"] == context["arguments"]["resourceid"]
    assert evaluation_result["index"] == "bookingsByResourceByTimeGSI"

    # Test response mapping template
    with open(mappings_base_path+'get_bookings_for_resource_response.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    # Check that all items in the results list are present in the response after transformation
    for i in range(len(evaluation_result)):
        # Check that all result fields are present in the response after transformation
        for key in evaluation_result[i]:
            assert evaluation_result[i][key] == context["result"]["items"][i][key]


def test_get_bookings_for_user_resolver():
    context = {
        "arguments":
            {
            },
        "identity":
            {
                "sub": "123456-abcdeefg-7890",
                "issuer": "",
                "username": "johndoe",
                "claims": {},
                "sourceIp": [
                    "x.x.x.x"
                ],
                "defaultAuthStrategy": "ALLOW"
            },
        "result": {
                "items": [
                    {
                        "bookingid": "0",
                        "resourceid": "1234567890",
                        "starttimeepochtime": 1672578000,
                        "userid": "123456-abcdeefg-7890",
                        "timestamp": "2023-01-01T00:00:00.000Z"
                    },
                    {
                        "bookingid": "1",
                        "resourceid": "0987654321",
                        "starttimeepochtime": 1672578000,
                        "userid": "123456-abcdeefg-7890",
                        "timestamp": "2023-01-01T00:00:00.000Z"
                    }
                ],
                "scannedCount": 2
        },
    }

    # Test request mapping template
    with open(mappings_base_path+'get_bookings_for_user_request.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    assert evaluation_result["operation"] == "Query"
    assert evaluation_result["query"]["expression"] == "userid = :userid"
    assert evaluation_result["query"]["expressionValues"][":userid"]["S"] == context["identity"]["sub"]
    assert evaluation_result["index"] == "useridGSI"

    # Test response mapping template
    with open(mappings_base_path+'get_bookings_for_user_response.vtl', 'r') as f:
        template = f.read()
    response = appsync_client.evaluate_mapping_template(
        template=template,
        context=json.dumps(context)
    )
    evaluation_result = json.loads(response['evaluationResult'])
    # Check that all items in the results list are present in the response after transformation
    for i in range(len(evaluation_result)):
        # Check that all result fields are present in the response after transformation
        for key in evaluation_result[i]:
            assert evaluation_result[i][key] == context["result"]["items"][i][key]
