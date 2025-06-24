# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Subscription testing uses WebSocket based approach documented at https://aws.amazon.com/blogs/mobile/appsync-websockets-python/

import json
import requests
import websocket
import threading
import time
from base64 import b64encode, decode
from uuid import uuid4

new_location_id = ""
new_resource_id = ""
new_booking_id = ""
new_location = {"imageUrl": "https://api.example.com/venetian.jpg",
                "description": "Headquarters in New York",
                "name": "HQ"}
new_resource = {"description": "Fishbowl, Level 2",
                "name": "FL-2",
                "type": "room"}
new_booking = {"starttimeepochtime": 1617278400}
location_created_subscriber = None
resource_created_subscriber = None
booking_created_subscriber = None


class AppSyncTestSubscriber:
    # Based on https://aws.amazon.com/blogs/mobile/appsync-websockets-python/

    def on_open(self, web_socket):
        web_socket.send(json.dumps({'type': 'connection_init'}))

    def on_close(self, web_socket):
        return

    def on_error(self, web_socket, error):
        self.subscription_errors.append(error)

    def on_message(self, web_socket, message):
        message_object = json.loads(message)
        message_type = message_object['type']
        if message_type == 'connection_ack':
            self.subscription_messages.append(message)
            subscription_request_data = json.dumps({
                'query': self.subscription_query,
                'variables': {}
            })
            register_request = {
                'id': self.appsync_subscription_id,
                'payload': {
                    'data': subscription_request_data,
                    'extensions': {
                        'authorization': {
                            'host': self.appsync_host,
                            'Authorization': self.authentication_token
                        }
                    }
                },
                'type': 'start'
            }
            web_socket.send(json.dumps(register_request))
        if message_type == 'data':
            self.subscription_messages.append(message)
        if message_type == 'error':
            self.subscription_errors.append(message_object['payload'])

    def __init__(self, global_config, query):
        self.websocket_application = None
        self.websocket_application_thread = None
        self.subscription_messages = []
        self.subscription_errors = []
        subscription_query = ''
        self.appsync_subscription_id = str(uuid4())
        self.subscription_query = query
        self.appsync_host = global_config["APIEndpoint"].replace('https://', '').replace('/graphql', '')
        self.authentication_token = global_config["adminUserAccessToken"]
        subscription_request_header = {
            'host': self.appsync_host,
            'Authorization': self.authentication_token
        }
        connection_url = global_config["APIEndpoint"].replace('https', 'wss').replace('appsync-api',
                                                                                      'appsync-realtime-api') \
                         + '?header=' + b64encode(json.dumps(subscription_request_header).encode('utf-8')).decode('utf-8') \
                         + '&payload=e30='
        self.websocket_application = websocket.WebSocketApp(connection_url,
                                                                             subprotocols=['graphql-ws'],
                                                                             on_message=lambda ws, msg: self.on_message(ws, msg),
                                                                             on_error=lambda ws, msg: self.on_error(ws, msg),
                                                                             on_close=lambda ws: self.on_close(ws),
                                                                             on_open=lambda ws: self.on_open(ws))
        self.websocket_application_thread = threading.Thread(target=self.websocket_application.run_forever)
        self.websocket_application_thread.daemon = True
        self.websocket_application_thread.start()

    def close(self):
        deregister_request = {
            'type': 'stop',
            'id': self.appsync_subscription_id
        }
        self.websocket_application.send(json.dumps(deregister_request))
        self.websocket_application.close()


def test_init_subscriptions(global_config):
    global location_created_subscriber, resource_created_subscriber, booking_created_subscriber
    query = '''subscription TestLocationCreatedSubscription {
      locationCreated {
        locationid
        name
        description
        imageUrl
        timestamp
      }
      }'''
    location_created_subscriber = AppSyncTestSubscriber(global_config, query)
    query = '''subscription TestResourceCreateSubscription {
      resourceCreated {
        resourceid
        locationid
        name
        description
        type
        timestamp
      }
      }'''
    resource_created_subscriber = AppSyncTestSubscriber(global_config, query)
    query = '''subscription TestBookingCreateSubscription {
      bookingCreated {
        bookingid
        resourceid
        starttimeepochtime
        timestamp
        userid
      }
      }'''
    booking_created_subscriber = AppSyncTestSubscriber(global_config, query)
    time.sleep(5)
    assert len(location_created_subscriber.subscription_messages) == 1
    data = json.loads(location_created_subscriber.subscription_messages[0])
    assert data["type"] == "connection_ack"
    assert len(resource_created_subscriber.subscription_messages) == 1
    data = json.loads(resource_created_subscriber.subscription_messages[0])
    assert data["type"] == "connection_ack"
    assert len(booking_created_subscriber.subscription_messages) == 1
    data = json.loads(booking_created_subscriber.subscription_messages[0])
    assert data["type"] == "connection_ack"
    return


def test_access_to_the_api_without_authentication(global_config):
    schema_request = '{"query":"{__schema {queryType {fields {name}}}}","variables":{}}'
    headers = {'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=schema_request)
    assert response.status_code == 401


def test_access_to_the_api_with_authentication(global_config):
    schema_request = '{"query":"{__schema {queryType {fields {name}}}}","variables":{}}'
    headers = {'Authorization': global_config["adminUserAccessToken"], 'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=schema_request)
    assert response.status_code == 200
    data = json.loads(response.text)['data']
    assert data['__schema']['queryType']["fields"] is not None


def test_get_list_of_locations_by_regular_user(global_config):
    data_request = '{"query":"query allLocations {getAllLocations {description name imageUrl resources {description name type bookings {starttimeepochtime userid}}}}","variables":{}}'
    headers = {'Authorization': global_config["regularUserAccessToken"], 'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=data_request)
    assert response.status_code == 200
    data = json.loads(response.text)['data']
    assert data['getAllLocations'] == []


def test_deny_put_location_by_regular_user(global_config):
    data_request = '{"query":"mutation addLocation {createLocation(' \
                   + f'name: \\"{new_location["name"]} \\", ' \
                   + f'description: \\"{new_location["description"]}\\", ' \
                   + f'imageUrl: \\"{new_location["imageUrl"]}\\"' \
                   + ') {name locationid imageUrl description timestamp}}","variables":{}}'
    headers = {'Authorization': global_config["regularUserAccessToken"], 'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=data_request)
    assert response.status_code == 200
    data = json.loads(response.text)['data']
    assert data['createLocation'] is None
    errors = json.loads(response.text)['errors']
    assert errors[0]['errorType'] == 'Unauthorized'


def test_allow_put_location_by_administrative_user(global_config):
    data_request = '{"query":"mutation addLocation {createLocation(' \
                   + f'name: \\"{new_location["name"]}\\", ' \
                   + f'description: \\"{new_location["description"]}\\", ' \
                   + f'imageUrl: \\"{new_location["imageUrl"]}\\"' \
                   + ') {name locationid imageUrl description timestamp}}","variables":{}}'
    headers = {'Authorization': global_config["adminUserAccessToken"], 'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=data_request)
    assert response.status_code == 200
    data = json.loads(response.text)['data']
    assert data['createLocation']['name'] == new_location['name']
    assert data['createLocation']['imageUrl'] == new_location['imageUrl']
    assert data['createLocation']['description'] == new_location['description']
    global new_location_id
    new_location_id = data['createLocation']['locationid']


def test_deny_put_invalid_location(global_config):
    data_request = '{"query":"mutation addLocation {createLocation(' \
                   + f'name: \\"{new_location["name"]}\\", ' \
                   + f'description: \\"{new_location["description"]}\\", ' \
                   + f'imageURL: \\"{new_location["imageUrl"]}\\"' \
                   + ') {name locationid imageUrl description timestamp}}","variables":{}}'
    headers = {'Authorization': global_config["adminUserAccessToken"], 'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=data_request)
    assert response.status_code == 200
    data = json.loads(response.text)['data']
    assert data is None
    errors = json.loads(response.text)['errors']
    assert errors[0]['message'].startswith('Validation error of type UnknownArgument')


def test_get_location_by_regular_user(global_config):
    data_request = '{"query":"query getLocation {getLocation(' \
                   + f'locationid: \\"{new_location_id}\\"' \
                   + ') {description imageUrl locationid name timestamp }}","variables":{}}'
    headers = {'Authorization': global_config["regularUserAccessToken"], 'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=data_request)
    assert response.status_code == 200
    data = json.loads(response.text)['data']
    assert data['getLocation']['locationid'] == new_location_id
    assert data['getLocation']['name'] == new_location['name']
    assert data['getLocation']['imageUrl'] == new_location['imageUrl']
    assert data['getLocation']['description'] == new_location['description']


def test_get_list_of_resources_by_regular_user(global_config):
    data_request = '{"query":"query allLocations {getAllLocations {description name imageUrl resources {description name type bookings {starttimeepochtime userid}}}}","variables":{}}'
    headers = {'Authorization': global_config["regularUserAccessToken"], 'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=data_request)
    assert response.status_code == 200
    data = json.loads(response.text)['data']
    assert data['getAllLocations'][0]['resources'] == []


def test_deny_put_resource_by_regular_user(global_config):
    data_request = '{"query":"mutation addResource {createResource(' \
                   + f'locationid: \\"{new_location_id}\\", ' \
                   + f'name: \\"{new_resource["name"]}\\", ' \
                   + f'description: \\"{new_resource["description"]}\\", ' \
                   + f'type: \\"{new_resource["type"]}\\"' \
                   + ') {resourceid locationid name description type timestamp}}","variables":{}}'
    headers = {'Authorization': global_config["regularUserAccessToken"], 'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=data_request)
    assert response.status_code == 200
    data = json.loads(response.text)['data']
    assert data['createResource'] is None
    errors = json.loads(response.text)['errors']
    assert errors[0]['errorType'] == 'Unauthorized'


def test_allow_put_resource_by_administrative_user(global_config):
    data_request = '{"query":"mutation addResource {createResource(' \
                   + f'locationid: \\"{new_location_id}\\", ' \
                   + f'name: \\"{new_resource["name"]}\\", ' \
                   + f'description: \\"{new_resource["description"]}\\", ' \
                   + f'type: \\"{new_resource["type"]}\\"' \
                   + ') {resourceid locationid name description type timestamp}}","variables":{}}'
    headers = {'Authorization': global_config["adminUserAccessToken"], 'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=data_request)
    assert response.status_code == 200
    data = json.loads(response.text)['data']
    assert data['createResource']['name'] == new_resource['name']
    assert data['createResource']['locationid'] == new_location_id
    global new_resource_id, new_booking
    new_resource_id = data['createResource']['resourceid']
    new_booking['resourceid'] = data['createResource']['resourceid']


def test_access_to_the_resource_without_authentication(global_config):
    data_request = '{"query":"query getResource {getResource(' \
                   + f'resourceid: \\"{new_resource_id}\\"' \
                   + ') {locationid resourceid name description type }}","variables":{}}'
    headers = {'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=data_request)
    assert response.status_code == 401


def test_get_resource_by_regular_user(global_config):
    data_request = '{"query":"query getResource {getResource(' \
                   + f'resourceid: \\"{new_resource_id}\\"' \
                   + ') {locationid resourceid name description type }}","variables":{}}'
    headers = {'Authorization': global_config["regularUserAccessToken"], 'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=data_request)
    assert response.status_code == 200
    data = json.loads(response.text)['data']
    assert data['getResource']['locationid'] == new_location_id
    assert data['getResource']['resourceid'] == new_resource_id
    assert data['getResource']['name'] == new_resource['name']
    assert data['getResource']['type'] == new_resource['type']
    assert data['getResource']['description'] == new_resource['description']


def test_get_list_of_bookings_for_resource_by_regular_user(global_config):
    data_request = '{"query":"query allLocations {getAllLocations {description name imageUrl resources {description name type bookings {starttimeepochtime userid}}}}","variables":{}}'
    headers = {'Authorization': global_config["regularUserAccessToken"], 'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=data_request)
    assert response.status_code == 200
    data = json.loads(response.text)['data']
    assert data['getAllLocations'][0]['resources'][0]['bookings'] == []


def test_get_list_of_bookings_for_yourself(global_config):
    data_request = '{"query":"query myBookings {getMyBookings {bookingid resourceid starttimeepochtime}}","variables":{}}'
    headers = {'Authorization': global_config["regularUserAccessToken"], 'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=data_request)
    assert response.status_code == 200
    data = json.loads(response.text)['data']
    assert data['getMyBookings'] == []


def test_get_list_of_bookings_for_yourself_without_authentication(global_config):
    data_request = '{"query":"query myBookings {getMyBookings {bookingid resourceid starttimeepochtime}}","variables":{}}'
    headers = {'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=data_request)
    assert response.status_code == 401


def test_allow_put_booking_for_yourself(global_config):
    data_request = '{"query":"mutation addBooking {createBooking(' \
                   + f'resourceid: \\"{new_resource_id}\\", ' \
                   + f'starttimeepochtime: {new_booking["starttimeepochtime"]}, ' \
                   + ') {bookingid resourceid starttimeepochtime userid timestamp}}","variables":{}}'
    headers = {'Authorization': global_config["regularUserAccessToken"], 'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=data_request)
    assert response.status_code == 200
    data = json.loads(response.text)['data']
    assert 'bookingid' in data['createBooking']
    assert data['createBooking']['resourceid'] == new_resource_id
    assert data['createBooking']['userid'] == global_config["regularUserSub"]
    global new_booking_id
    new_booking_id = data['createBooking']['bookingid']


def test_get_list_of_bookings_for_resource_after_adding_booking_for_user(global_config):
    data_request = '{"query":"query getResource {getResource(' \
                   + f'resourceid: \\"{new_resource_id}\\"' \
                   + ') {bookings {bookingid resourceid userid starttimeepochtime timestamp}}}","variables":{}}'
    headers = {'Authorization': global_config["regularUserAccessToken"], 'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=data_request)
    assert response.status_code == 200
    data = json.loads(response.text)['data']
    assert data['getResource']['bookings'][0]['bookingid'] == new_booking_id
    assert data['getResource']['bookings'][0]['resourceid'] == new_booking['resourceid']
    assert data['getResource']['bookings'][0]['userid'] == global_config["regularUserSub"]
    assert data['getResource']['bookings'][0]['starttimeepochtime'] == new_booking['starttimeepochtime']


def test_get_list_of_bookings_for_yourself_after_adding_booking_for_user(global_config):
    data_request = '{"query":"query myBookings {getMyBookings {bookingid resourceid userid starttimeepochtime}}","variables":{}}'
    headers = {'Authorization': global_config["regularUserAccessToken"], 'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=data_request)
    assert response.status_code == 200
    data = json.loads(response.text)['data']
    assert data['getMyBookings'][0]['bookingid'] == new_booking_id
    assert data['getMyBookings'][0]['userid'] == global_config["regularUserSub"]
    assert data['getMyBookings'][0]['resourceid'] == new_booking['resourceid']
    assert data['getMyBookings'][0]['starttimeepochtime'] == new_booking['starttimeepochtime']


def test_deleting_of_your_own_booking(global_config):
    data_request = '{"query":"mutation deleteBooking {deleteBooking(' \
                   + f'bookingid: \\"{new_booking_id}\\"' \
                   + ') }","variables":{}}'
    headers = {'Authorization': global_config["regularUserAccessToken"], 'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=data_request)
    assert response.status_code == 200
    data = json.loads(response.text)['data']
    assert data['deleteBooking'] == new_booking_id


def test_deny_deleting_not_your_own_booking_by_non_admin(global_config):
    # create booking as admin user
    data_request = '{"query":"mutation addBooking {createBooking(' \
                   + f'resourceid: \\"{new_resource_id}\\", ' \
                   + f'starttimeepochtime: {new_booking["starttimeepochtime"]}, ' \
                   + ') {bookingid resourceid starttimeepochtime userid}}","variables":{}}'
    headers = {'Authorization': global_config["adminUserAccessToken"], 'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=data_request)
    data = json.loads(response.text)['data']
    temp_new_booking_id = data['createBooking']['bookingid']
    # Try to delete booking as a different user (non-administrator)
    data_request = '{"query":"mutation deleteBooking {deleteBooking(' \
                   + f'bookingid: \\"{temp_new_booking_id}\\"' \
                   + ') }","variables":{}}'
    headers = {'Authorization': global_config["regularUserAccessToken"], 'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=data_request)
    assert response.status_code == 200
    data = json.loads(response.text)['data']
    assert data['deleteBooking'] is None
    errors = json.loads(response.text)['errors']
    assert errors[0]['errorType'] == 'Unauthorized'
    # Try to delete record as an owner
    data_request = '{"query":"mutation deleteBooking {deleteBooking(' \
                   + f'bookingid: \\"{temp_new_booking_id}\\"' \
                   + ') }","variables":{}}'
    headers = {'Authorization': global_config["adminUserAccessToken"], 'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=data_request)
    assert response.status_code == 200
    data = json.loads(response.text)['data']
    assert data['deleteBooking'] == temp_new_booking_id


def test_allow_deleting_not_your_own_booking_by_admin(global_config):
    # create booking as a regular user
    data_request = '{"query":"mutation addBooking {createBooking(' \
                   + f'resourceid: \\"{new_resource_id}\\", ' \
                   + f'starttimeepochtime: {new_booking["starttimeepochtime"]}, ' \
                   + ') {bookingid resourceid starttimeepochtime userid}}","variables":{}}'
    headers = {'Authorization': global_config["regularUserAccessToken"], 'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=data_request)
    data = json.loads(response.text)['data']
    temp_new_booking_id = data['createBooking']['bookingid']
    # Try to delete booking as an administrator
    data_request = '{"query":"mutation deleteBooking {deleteBooking(' \
                   + f'bookingid: \\"{temp_new_booking_id}\\"' \
                   + ') }","variables":{}}'
    headers = {'Authorization': global_config["adminUserAccessToken"], 'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=data_request)
    assert response.status_code == 200
    data = json.loads(response.text)['data']
    assert data['deleteBooking'] == temp_new_booking_id


def test_deny_deleting_resource_by_regular_user(global_config):
    data_request = '{"query":"mutation deleteResource {deleteResource(' \
                   + f'resourceid: \\"{new_resource_id}\\"' \
                   + ') }","variables":{}}'
    headers = {'Authorization': global_config["regularUserAccessToken"], 'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=data_request)
    assert response.status_code == 200
    data = json.loads(response.text)['data']
    assert data['deleteResource'] is None
    errors = json.loads(response.text)['errors']
    assert errors[0]['errorType'] == 'Unauthorized'


def test_deleting_resource_by_administrative_user(global_config):
    data_request = '{"query":"mutation deleteResource {deleteResource(' \
                   + f'resourceid: \\"{new_resource_id}\\"' \
                   + ') }","variables":{}}'
    headers = {'Authorization': global_config["adminUserAccessToken"], 'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=data_request)
    assert response.status_code == 200
    data = json.loads(response.text)['data']
    assert data['deleteResource'] == new_resource_id


def test_deny_deleting_location_by_regular_user(global_config):
    data_request = '{"query":"mutation deleteLocation {deleteLocation(' \
                   + f'locationid: \\"{new_location_id}\\"' \
                   + ') }","variables":{}}'
    headers = {'Authorization': global_config["regularUserAccessToken"], 'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=data_request)
    assert response.status_code == 200
    data = json.loads(response.text)['data']
    assert data['deleteLocation'] is None
    errors = json.loads(response.text)['errors']
    assert errors[0]['errorType'] == 'Unauthorized'


def test_deleting_location_by_administrative_user(global_config):
    data_request = '{"query":"mutation deleteLocation {deleteLocation(' \
                   + f'locationid: \\"{new_location_id}\\"' \
                   + ') }","variables":{}}'
    headers = {'Authorization': global_config["adminUserAccessToken"], 'Content-Type': 'application/json'}
    response = requests.request("POST", global_config["APIEndpoint"], headers=headers, data=data_request)
    assert response.status_code == 200
    data = json.loads(response.text)['data']
    assert data['deleteLocation'] == new_location_id


def test_location_created_subscription_results(global_config):
    global location_created_subscriber, new_location_id, new_location
    location_created_subscriber.close()
    assert len(location_created_subscriber.subscription_messages) > 1
    data = json.loads(location_created_subscriber.subscription_messages[1])
    assert data["payload"]["data"]["locationCreated"]["locationid"] == new_location_id
    assert data["payload"]["data"]["locationCreated"]["name"] == new_location["name"]
    assert data["payload"]["data"]["locationCreated"]["description"] == new_location["description"]
    assert data["payload"]["data"]["locationCreated"]["imageUrl"] == new_location["imageUrl"]
    return


def test_resource_created_subscription_results(global_config):
    global resource_created_subscriber, new_resource_id, new_resource
    resource_created_subscriber.close()
    assert len(resource_created_subscriber.subscription_messages) > 1
    data = json.loads(resource_created_subscriber.subscription_messages[1])
    assert data["payload"]["data"]["resourceCreated"]["resourceid"] == new_resource_id
    assert data["payload"]["data"]["resourceCreated"]["locationid"] == new_location_id
    assert data["payload"]["data"]["resourceCreated"]["name"] == new_resource["name"]
    assert data["payload"]["data"]["resourceCreated"]["description"] == new_resource["description"]
    assert data["payload"]["data"]["resourceCreated"]["type"] == new_resource["type"]
    return


def test_booking_created_subscription_results(global_config):
    global booking_created_subscriber, new_booking_id, new_resource_id
    booking_created_subscriber.close()
    assert len(booking_created_subscriber.subscription_messages) > 1
    data = json.loads(booking_created_subscriber.subscription_messages[1])
    assert data["payload"]["data"]["bookingCreated"]["bookingid"] == new_booking_id
    assert data["payload"]["data"]["bookingCreated"]["resourceid"] == new_resource_id
    assert data["payload"]["data"]["bookingCreated"]["userid"] == global_config["regularUserSub"]
    return
