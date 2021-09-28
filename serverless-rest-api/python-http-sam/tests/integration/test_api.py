# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import requests

new_location_id = ""

new_resource_id = ""

new_booking_id = ""

new_location = {"imageUrl": "https://api.example.com/venetian.jpg",
                "description": "Headquarters in New Yorks",
                "name": "HQ"}

new_resource = {"description": "Fishbowl, Level 2",
                "name": "FL-2",
                "type": "room"}

new_booking = {"starttimeepochtime": 1617278400}


def test_access_to_the_locations_without_authentication(global_config):
    response = requests.get(global_config["APIEndpoint"] + 'locations')
    assert response.status_code == 401


def test_get_list_of_locations_by_regular_user(global_config):
    response = requests.get(
        global_config["APIEndpoint"] + 'locations',
        headers={'Authorization': global_config["regularUserIdToken"]}
    )
    assert response.status_code == 200
    data = json.loads(response.text)
    assert data == []


def test_deny_put_location_by_regular_user(global_config):
    response = requests.put(
        global_config["APIEndpoint"] + 'locations',
        data=json.dumps(new_location),
        headers={'Authorization': global_config["regularUserIdToken"], 'Content-Type': 'application/json'}
    )
    assert response.status_code == 403


def test_allow_put_location_by_administrative_user(global_config):
    response = requests.put(
        global_config["APIEndpoint"] + 'locations',
        data=json.dumps(new_location),
        headers={'Authorization': global_config["adminUserIdToken"], 'Content-Type': 'application/json'}
    )
    assert response.status_code == 200
    data = json.loads(response.text)
    assert data['name'] == new_location['name']
    assert data['imageUrl'] == new_location['imageUrl']
    assert data['description'] == new_location['description']
    global new_location_id
    new_location_id = data['locationid']


def test_deny_put_invalid_location(global_config):
    new_invalid_location = {"imageURL": "https://api.example.com/venetian.jpg",
                            "description": "Headquarters in New Yorks",
                            "name": "HQ"}
    response = requests.put(
        global_config["APIEndpoint"] + 'locations',
        data=new_invalid_location,
        headers={'Authorization': global_config["adminUserIdToken"], 'Content-Type': 'application/json'}
    )
    assert response.status_code == 400


def test_get_location_by_regular_user(global_config):
    response = requests.get(
        global_config["APIEndpoint"] + f'locations/{new_location_id}',
        headers={'Authorization': global_config["regularUserIdToken"]}
    )
    assert response.status_code == 200
    data = json.loads(response.text)
    assert data['locationid'] == new_location_id
    assert data['name'] == new_location['name']
    assert data['imageUrl'] == new_location['imageUrl']
    assert data['description'] == new_location['description']


def test_access_to_the_resources_without_authentication(global_config):
    response = requests.get(global_config["APIEndpoint"] + f'locations/{new_location_id}/resources')
    assert response.status_code == 401


def test_get_list_of_resources_by_regular_user(global_config):
    response = requests.get(
        global_config["APIEndpoint"] + f'locations/{new_location_id}/resources',
        headers={'Authorization': global_config["regularUserIdToken"]}
    )
    assert response.status_code == 200
    data = json.loads(response.text)
    assert data == []


def test_deny_put_resource_by_regular_user(global_config):
    response = requests.put(
        global_config["APIEndpoint"] + f'locations/{new_location_id}/resources',
        data=json.dumps(new_resource),
        headers={'Authorization': global_config["regularUserIdToken"], 'Content-Type': 'application/json'}
    )
    assert response.status_code == 403


def test_allow_put_resource_by_administrative_user(global_config):
    response = requests.put(
        global_config["APIEndpoint"] + f'locations/{new_location_id}/resources',
        data=json.dumps(new_resource),
        headers={'Authorization': global_config["adminUserIdToken"], 'Content-Type': 'application/json'}
    )
    assert response.status_code == 200
    data = json.loads(response.text)
    assert data['name'] == new_resource['name']
    assert data['locationid'] == new_location_id
    global new_resource_id, new_booking
    new_resource_id = data['resourceid']
    new_booking['resourceid'] = data['resourceid']


def test_get_resource_by_regular_user(global_config):
    response = requests.get(
        global_config["APIEndpoint"] + f'locations/{new_location_id}/resources/{new_resource_id}',
        headers={'Authorization': global_config["regularUserIdToken"]}
    )
    assert response.status_code == 200
    data = json.loads(response.text)
    assert data['locationid'] == new_location_id
    assert data['resourceid'] == new_resource_id
    assert data['name'] == new_resource['name']


def test_access_to_the_bookings_without_authentication(global_config):
    response = requests.get(
        global_config["APIEndpoint"] + f'locations/{new_location_id}/resources/{new_resource_id}/bookings')
    assert response.status_code == 401


def test_get_list_of_bookings_for_resource_by_regular_user(global_config):
    response = requests.get(
        global_config["APIEndpoint"] + f'locations/{new_location_id}/resources/{new_resource_id}/bookings',
        headers={'Authorization': global_config["regularUserIdToken"]}
    )
    assert response.status_code == 200
    data = json.loads(response.text)
    assert data == []


def test_deny_put_booking_for_somebody_else(global_config):
    response = requests.put(
        global_config["APIEndpoint"] + f'users/{global_config["adminUserSub"]}/bookings',
        data=json.dumps(new_booking),
        headers={'Authorization': global_config['regularUserIdToken'], 'Content-Type': 'application/json'}
    )
    assert response.status_code == 403


def test_deny_put_booking_for_somebody_else_by_administrative_user(global_config):
    response = requests.put(
        global_config["APIEndpoint"] + f'users/{global_config["regularUserSub"]}/bookings',
        data=json.dumps(new_booking),
        headers={'Authorization': global_config["adminUserIdToken"], 'Content-Type': 'application/json'}
    )
    assert response.status_code == 403


def test_deny_getting_list_of_bookings_for_somebody_else(global_config):
    response = requests.get(
        global_config["APIEndpoint"] + f'users/{global_config["adminUserSub"]}/bookings',
        headers={'Authorization': global_config["regularUserIdToken"]}
    )
    assert response.status_code == 403


def test_deny_getting_list_of_bookings_for_somebody_else_by_administrative_user(global_config):
    response = requests.get(
        global_config["APIEndpoint"] + f'users/{global_config["regularUserSub"]}/bookings',
        headers={'Authorization': global_config["adminUserIdToken"]}
    )
    assert response.status_code == 403


def test_get_list_of_bookings_for_yourself(global_config):
    response = requests.get(
        global_config["APIEndpoint"] + f'users/{global_config["regularUserSub"]}/bookings',
        headers={'Authorization': global_config["regularUserIdToken"]}
    )
    assert response.status_code == 200
    data = json.loads(response.text)
    assert data == []


def test_allow_put_booking_for_yourself(global_config):
    response = requests.put(
        global_config["APIEndpoint"] + f'users/{global_config["regularUserSub"]}/bookings',
        data=json.dumps(new_booking),
        headers={'Authorization': global_config['regularUserIdToken'], 'Content-Type': 'application/json'}
    )
    assert response.status_code == 200
    data = json.loads(response.text)
    assert 'bookingid' in data
    assert data['resourceid'] == new_resource_id
    assert data['userid'] == global_config["regularUserSub"]
    global new_booking_id
    new_booking_id = data['bookingid']


def test_get_list_of_bookings_for_resource_after_adding_booking_for_user(global_config):
    response = requests.get(
        global_config["APIEndpoint"] + f'locations/{new_location_id}/resources/{new_resource_id}/bookings',
        headers={'Authorization': global_config["regularUserIdToken"]}
    )
    assert response.status_code == 200
    data = (json.loads(response.text))[0]
    assert data['userid'] == global_config["regularUserSub"]


def test_get_list_of_bookings_for_yourself_after_adding_booking_for_user(global_config):
    response = requests.get(
        global_config["APIEndpoint"] + f'users/{global_config["regularUserSub"]}/bookings',
        headers={'Authorization': global_config["regularUserIdToken"]}
    )
    assert response.status_code == 200
    data = (json.loads(response.text))[0]
    assert data['userid'] == global_config["regularUserSub"]


def test_get_details_of_your_booking(global_config):
    response = requests.get(
        global_config["APIEndpoint"] + f'users/{global_config["regularUserSub"]}/bookings/{new_booking_id}',
        headers={'Authorization': global_config["regularUserIdToken"]}
    )
    assert response.status_code == 200
    data = json.loads(response.text)
    assert data['userid'] == global_config["regularUserSub"]
    assert data['bookingid'] == new_booking_id
    assert data['resourceid'] == new_resource_id


def test_deny_getting_details_of_somebody_else_booking_by_administrative_user(global_config):
    response = requests.get(
        global_config["APIEndpoint"] + f'users/{global_config["regularUserSub"]}/bookings/{new_booking_id}',
        headers={'Authorization': global_config["adminUserIdToken"]}
    )
    assert response.status_code == 403


def test_deny_deleting_somebody_else_booking_by_administrative_user(global_config):
    response = requests.delete(
        global_config["APIEndpoint"] + f'users/{global_config["regularUserSub"]}/bookings/{new_booking_id}',
        headers={'Authorization': global_config["adminUserIdToken"]}
    )
    assert response.status_code == 403


def test_deleting_of_your_own_booking(global_config):
    response = requests.delete(
        global_config["APIEndpoint"] + f'users/{global_config["regularUserSub"]}/bookings/{new_booking_id}',
        headers={'Authorization': global_config["regularUserIdToken"]}
    )
    assert response.status_code == 200


def test_deny_deleting_resource_by_regular_user(global_config):
    response = requests.delete(
        global_config["APIEndpoint"] + f'locations/{new_location_id}/resources/{new_resource_id}',
        headers={'Authorization': global_config["regularUserIdToken"]}
    )
    assert response.status_code == 403


def test_deleting_resource_by_administrative_user(global_config):
    response = requests.delete(
        global_config["APIEndpoint"] + f'locations/{new_location_id}/resources/{new_resource_id}',
        headers={'Authorization': global_config["adminUserIdToken"]}
    )
    assert response.status_code == 200


def test_deny_deleting_location_by_regular_user(global_config):
    response = requests.delete(
        global_config["APIEndpoint"] + f'locations/{new_location_id}',
        headers={'Authorization': global_config["regularUserIdToken"]}
    )
    assert response.status_code == 403


def test_deleting_location_by_administrative_user(global_config):
    response = requests.delete(
        global_config["APIEndpoint"] + f'locations/{new_location_id}',
        headers={'Authorization': global_config["adminUserIdToken"]}
    )
    assert response.status_code == 200
