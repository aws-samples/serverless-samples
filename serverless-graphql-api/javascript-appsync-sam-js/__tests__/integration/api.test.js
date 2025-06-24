// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

// The test suite expects test_init.sh to run in advance to clean up databse, 
// export user identity information, etc. It is performed automatically by testpec.yml in CI/CD pipeline

var supertest = require('supertest');
const uuid = require("uuid")
var WebSocketClient = require('websocket').client;

const apiEndpoint = process.env.API_ENDPOINT;
const regularUserAccessToken = process.env.REGULAR_USER_ACCESS_TOKEN;
const regularUserSub = process.env.REGULAR_USER_SUB;
const adminUserIdToken = process.env.ADMIN_USER_ID_TOKEN;
const adminUserAccessToken = process.env.ADMIN_USER_ACCESS_TOKEN;

class AppSyncSubscription{
    messages = [];
    errors = [];
    #query = '';
    #subscriptionId = '';
    #appSyncHost = '';
    #authToken = '';
    #client = null;
    #connection = null;

    constructor(query) {
        this.#query = query;
        this.#subscriptionId = uuid.v4();
        this.#appSyncHost = apiEndpoint.replace('https://', '').replace('/graphql', '');
        var wssUrl = apiEndpoint.replace('https', 'wss').replace('appsync-api', 'appsync-realtime-api');
        this.#authToken = adminUserAccessToken;
        var client =  new WebSocketClient();
        this.#client=client;
        client.on('connectFailed',(error) => {this.#onError(error)});
        client.on('connect', (connection) => {this.#onConnectionConnected(connection)});
        var headerBase64Encoded = (Buffer.from(JSON.stringify({ 'host': this.#appSyncHost, 'Authorization': this.#authToken }))).toString('base64');
        var connectionUrl = wssUrl + '?header=' + headerBase64Encoded + '&payload=e30='
        client.connect(connectionUrl, 'graphql-ws');
    }

    #onError(error) {
        // console.log("WebSocket client error: " + error);
        this.errors.push(error)
    }
    #onConnectionClosed() {
        // console.log('WebSocket connection closed');
    }

    #onConnectionMessage(message){
        // console.log("Received message: '" + message.utf8Data + "'");
        var messageObject = JSON.parse(message.utf8Data);
        var messageType = messageObject.type;
        if (messageType == 'connection_ack') {
            var requestData = JSON.stringify({ 'query': this.#query, 'variables': {} });
            var registerRequest = {
                'type': 'start',
                'id': this.#subscriptionId,
                'payload': {
                    'data': requestData,
                    'extensions': {
                        'authorization': { 'host': this.#appSyncHost, 'Authorization': this.#authToken }
                    }
                }
            };
            this.#connection.sendUTF(JSON.stringify(registerRequest));
        };
        if (messageType == 'data') {
            this.messages.push(message.utf8Data)
        };
        if (messageType == 'error') {
            this.#onError(messageObject.payload)
        };

    }

    #onConnectionConnected(connection) {
            // console.log('WebSocket client connected');
            this.#connection = connection;
            connection.on('error', (error) => {this.#onError(error)});
            connection.on('close', () => {this.#onConnectionClosed ()});
            connection.on('message', (message) => {this.#onConnectionMessage(message)});
            if (connection.connected) {
                connection.sendUTF(JSON.stringify({ 'type': 'connection_init' }));
            }
    }

    close() {
        if (this.#connection) {
            this.#connection.close();
            this.#client = null;
        };

    }
}

// This includes all tests for API 
describe('Test API endpoint', () => {
    var request;
    var newLocationId;
    var newResourceId;
    var newBookingId;
    var newSelfBookingId;
    var newLocation = { "imageUrl": "https://api.example.com/venetian.jpg", "description": "Headquorters in New Yorks", "name": "HQ" };
    var newResource = { "description": "Fishbowl, Level 2", "name": "FL-2", "type": "room" };
    var newBooking = { "starttimeepochtime": 1617278400 };
    var locationSubscription = new AppSyncSubscription('subscription TestLocationCreatedSubscription {locationCreated {locationid name description imageUrl timestamp}}');
    var resourceSubscription = new AppSyncSubscription('subscription TestResourceCreateSubscription {resourceCreated {resourceid locationid name description type timestamp}}');
    var bookingSubscription = new AppSyncSubscription('subscription TestBookingCreateSubscription {bookingCreated {bookingid resourceid starttimeepochtime timestamp userid}}');

    // One-time setup 
    beforeAll(() => {
        request = supertest(apiEndpoint);
        jest.setTimeout(10000)
    });

    // Clean up after the tests are over 
    afterAll(() => {
        locationSubscription.close();
        locationSubscription=null;
        resourceSubscription.close();
        resourceSubscription=null;
        bookingSubscription.close();
        bookingSubscription=null;
    });

    it('deny access to the api without authentication', async () => {
        schemaRequest = '{"query":"{__schema {queryType {fields {name}}}}","variables":{}}'
        return request.post("")
            .set('Content-Type', 'application/json')
            .send(schemaRequest)
            .expect(401);
    });

    it('allow access to the api with authentication', async () => {
        schemaRequest = '{"query":"{__schema {queryType {fields {name}}}}","variables":{}}'
        const response = await request.post("")
            .set('Content-Type', 'application/json')
            .set('Authorization', adminUserAccessToken)
            .send(schemaRequest)
            .expect(200);
    });

    it('return empty list of locations', async () => {
        dataRequest = '{"query":"query allLocations {getAllLocations {description name imageUrl resources {description name type bookings {starttimeepochtime userid}}}}","variables":{}}'
        const response = await request.post("")
            .set('Content-Type', 'application/json')
            .set('Authorization', regularUserAccessToken)
            .send(dataRequest)
            .expect(200);
        expect(response.body.data.getAllLocations).toEqual([]);
    });

    it('deny adding location by regular user', async () => {
        dataRequest = `{"query":"mutation addLocation {createLocation(name: \\"${newLocation.name} \\", description: \\"${newLocation.description}\\", imageUrl: \\"${newLocation.imageUrl}\\") {name locationid imageUrl description}}","variables":{}}`
        const response = await request.post("")
            .set('Content-Type', 'application/json')
            .set('Authorization', regularUserAccessToken)
            .send(dataRequest)
            .expect(200);
        expect(response.body.data.createLocation).toEqual(null);
        expect(response.body.errors).toEqual(
            expect.arrayContaining([
                expect.objectContaining({ errorType: 'Unauthorized' })
            ])
        );
    });

    it('allow adding location by administrative user', async () => {
        dataRequest = `{"query":"mutation addLocation {createLocation(name: \\"${newLocation.name}\\", description: \\"${newLocation.description}\\", imageUrl: \\"${newLocation.imageUrl}\\") {name locationid imageUrl description}}","variables":{}}`
        const response = await request.post("")
            .set('Content-Type', 'application/json')
            .set('Authorization', adminUserIdToken)
            .send(dataRequest)
            .expect(200);
        expect(response.body.data.createLocation.name).toBe(newLocation.name);
        expect(response.body.data.createLocation).toHaveProperty("locationid");
        newLocationId = response.body.data.createLocation.locationid;
    });

    it('deny adding invalid location', async () => {
        dataRequest = `{"query":"mutation addLocation {createLocation(name: \\"${newLocation.name}\\", description: \\"${newLocation.description}\\", imageURL: \\"${newLocation.imageUrl}\\") {name locationid imageUrl description}}","variables":{}}`
        const response = await request.post("")
            .set('Content-Type', 'application/json')
            .set('Authorization', adminUserIdToken)
            .send(dataRequest)
            .expect(200);
        expect(response.body.errors).toEqual(
            expect.arrayContaining([
                expect.objectContaining({ message: "Validation error of type UnknownArgument: Unknown field argument imageURL @ 'createLocation'" })
            ])
        );
    });


    it('allow getting location details by regular user', async () => {
        dataRequest = `{"query":"query getLocation {getLocation(locationid: \\"${newLocationId}\\") {description imageUrl locationid name timestamp }}","variables":{}}`
        const response = await request.post("")
            .set('Content-Type', 'application/json')
            .set('Authorization', regularUserAccessToken)
            .send(dataRequest)
            .expect(200);
        expect(response.body.data.getLocation.locationid).toBe(newLocationId);
        expect(response.body.data.getLocation.name).toBe(newLocation.name);
        expect(response.body.data.getLocation.imageUrl).toBe(newLocation.imageUrl);
        expect(response.body.data.getLocation.description).toBe(newLocation.description);
    });

    it('return empty list of resouces for a new location', async () => {
        dataRequest = '{"query":"query allLocations {getAllLocations {description name imageUrl resources {description name type bookings {starttimeepochtime userid}}}}","variables":{}}'
        const response = await request.post("")
            .set('Content-Type', 'application/json')
            .set('Authorization', regularUserAccessToken)
            .send(dataRequest)
            .expect(200);
        expect(response.body.data.getAllLocations[0].resources).toEqual([]);
    });

    it('deny adding resource by regular user', async () => {
        dataRequest = `{"query":"mutation addResource {createResource(locationid: \\"${newLocationId}\\", name: \\"${newResource.name}\\", description: \\"${newResource.description}\\", type: \\"${newResource.type}\\") {resourceid locationid name description type}}","variables":{}}`
        const response = await request.post("")
            .set('Content-Type', 'application/json')
            .set('Authorization', regularUserAccessToken)
            .send(dataRequest)
            .expect(200);
        expect(response.body.data.createResource).toEqual(null);
        expect(response.body.errors).toEqual(
            expect.arrayContaining([
                expect.objectContaining({ errorType: 'Unauthorized' })
            ])
        );
    });

    it('allow adding resource by administrative user', async () => {
        dataRequest = `{"query":"mutation addResource {createResource(locationid: \\"${newLocationId}\\", name: \\"${newResource.name}\\", description: \\"${newResource.description}\\", type: \\"${newResource.type}\\") {resourceid locationid name description type}}","variables":{}}`
        const response = await request.post("")
            .set('Content-Type', 'application/json')
            .set('Authorization', adminUserIdToken)
            .send(dataRequest)
            .expect(200);
        expect(response.body.data.createResource.name).toBe(newResource.name);
        expect(response.body.data.createResource).toHaveProperty("resourceid");
        expect(response.body.data.createResource).toHaveProperty("locationid");
        expect(response.body.data.createResource.locationid).toBe(newLocationId);
        newResourceId = response.body.data.createResource.resourceid;
        newBooking.resourceid = newResourceId;
    });

    it('allow getting resource details by regular user', async () => {
        dataRequest = `{"query":"query getResource {getResource(resourceid: \\"${newResourceId}\\") {locationid resourceid name description type }}","variables":{}}`
        const response = await request.post("")
            .set('Content-Type', 'application/json')
            .set('Authorization', regularUserAccessToken)
            .send(dataRequest)
            .expect(200);
        expect(response.body.data.getResource.resourceid).toBe(newResourceId);
        expect(response.body.data.getResource.locationid).toBe(newLocationId);
        expect(response.body.data.getResource.name).toBe(newResource.name);
        expect(response.body.data.getResource.type).toBe(newResource.type);
        expect(response.body.data.getResource.description).toBe(newResource.description);
    });

    it('return empty list of bookings for a new resource', async () => {
        dataRequest = '{"query":"query allLocations {getAllLocations {description name imageUrl resources {description name type bookings {starttimeepochtime userid}}}}","variables":{}}'
        const response = await request.post("")
            .set('Content-Type', 'application/json')
            .set('Authorization', regularUserAccessToken)
            .send(dataRequest)
            .expect(200);
        expect(response.body.data.getAllLocations[0].resources[0].bookings).toEqual([]);
    });

    it('deny listing of bookings for yourself without authentication', async () => {
        dataRequest = '{"query":"query myBookings {getMyBookings {bookingid resourceid starttimeepochtime}}","variables":{}}'
        const response = await request.post("")
            .set('Content-Type', 'application/json')
            .send(dataRequest)
            .expect(401);
    });

    it('return empty list of bookings for a new user (yourself)', async () => {
        dataRequest = '{"query":"query myBookings {getMyBookings {bookingid resourceid starttimeepochtime}}","variables":{}}'
        const response = await request.post("")
            .set('Content-Type', 'application/json')
            .set('Authorization', regularUserAccessToken)
            .send(dataRequest)
            .expect(200);
        expect(response.body.data.getMyBookings).toEqual([]);
    });

    it('allow adding booking for yourself', async () => {
        dataRequest = `{"query":"mutation addBooking {createBooking(resourceid: \\"${newResourceId}\\", starttimeepochtime: ${newBooking.starttimeepochtime}) {bookingid resourceid starttimeepochtime userid}}","variables":{}}`
        const response = await request.post("")
            .set('Content-Type', 'application/json')
            .set('Authorization', regularUserAccessToken)
            .send(dataRequest)
            .expect(200);
        expect(response.body.data.createBooking).toHaveProperty("bookingid");
        expect(response.body.data.createBooking).toHaveProperty("userid");
        expect(response.body.data.createBooking.userid).toBe(regularUserSub);
        expect(response.body.data.createBooking.resourceid).toBe(newResourceId);
        newBookingId = response.body.data.createBooking.bookingid;
        newSelfBookingId = newBookingId;
    });

    it('return list with a single newly added booking for a resource', async () => {
        dataRequest = `{"query":"query getResource {getResource(resourceid: \\"${newResourceId}\\") {bookings {bookingid resourceid userid starttimeepochtime}}}","variables":{}}`
        const response = await request.post("")
            .set('Content-Type', 'application/json')
            .set('Authorization', regularUserAccessToken)
            .send(dataRequest)
            .expect(200)
        expect(response.body.data.getResource.bookings[0].bookingid).toBe(newBookingId);
        expect(response.body.data.getResource.bookings[0].resourceid).toBe(newBooking.resourceid);
        expect(response.body.data.getResource.bookings[0].userid).toBe(regularUserSub);
        expect(response.body.data.getResource.bookings[0].starttimeepochtime).toBe(newBooking.starttimeepochtime);
    });

    it('return list with a single newly added booking for a user', async () => {
        dataRequest = '{"query":"query myBookings {getMyBookings {bookingid resourceid userid starttimeepochtime}}","variables":{}}'
        const response = await request.post("")
            .set('Content-Type', 'application/json')
            .set('Authorization', regularUserAccessToken)
            .send(dataRequest)
            .expect(200)
        expect(response.body.data.getMyBookings[0].bookingid).toBe(newBookingId);
        expect(response.body.data.getMyBookings[0].resourceid).toBe(newBooking.resourceid);
        expect(response.body.data.getMyBookings[0].userid).toBe(regularUserSub);
        expect(response.body.data.getMyBookings[0].starttimeepochtime).toBe(newBooking.starttimeepochtime);
    });

    it('allow deleting of your own booking', async () => {
        dataRequest = `{"query":"mutation deleteBooking {deleteBooking(bookingid: \\"${newBookingId}\\") }","variables":{}}`
        const response = await request.post("")
            .set('Content-Type', 'application/json')
            .set('Authorization', regularUserAccessToken)
            .send(dataRequest)
            .expect(200);
        expect(response.body.data.deleteBooking).toBe(newBookingId);
    });

    it('deny deleting of somebody else\'s booking if you are not an administrator', async () => {
        // Create booking as admin user
        dataRequest1 = `{"query":"mutation addBooking {createBooking(resourceid: \\"${newResourceId}\\", starttimeepochtime: ${newBooking.starttimeepochtime}) {bookingid resourceid starttimeepochtime userid}}","variables":{}}`
        const response1 = await request.post("")
            .set('Content-Type', 'application/json')
            .set('Authorization', adminUserIdToken)
            .send(dataRequest1)
            .expect(200);
        newBookingId = response1.body.data.createBooking.bookingid;
        // Try to delete booking as a different user (non-administrator)        
        dataRequest2 = `{"query":"mutation deleteBooking {deleteBooking(bookingid: \\"${newBookingId}\\") }","variables":{}}`
        const response2 = await request.post("")
            .set('Content-Type', 'application/json')
            .set('Authorization', regularUserAccessToken)
            .send(dataRequest2)
            .expect(200);
            expect(response2.body.data.deleteBooking==null || response2.body.data.deleteBooking=="").toBeTruthy();
            expect(response2.body.errors).toEqual(
            expect.arrayContaining([
                expect.objectContaining({ errorType: 'Unauthorized' })
            ])
        );
        // Try to delete record as an owner
        dataRequest3 = `{"query":"mutation deleteBooking {deleteBooking(bookingid: \\"${newBookingId}\\") }","variables":{}}`
        const response3 = await request.post("")
            .set('Content-Type', 'application/json')
            .set('Authorization', adminUserIdToken)
            .send(dataRequest3)
            .expect(200);
        expect(response3.body.data.deleteBooking).toBe(newBookingId);
    });


    it('deny deleting resource by regular user', async () => {
        dataRequest = `{"query":"mutation deleteResource {deleteResource(resourceid: \\"${newResourceId}\\") }","variables":{}}`
        const response = await request.post("")
            .set('Content-Type', 'application/json')
            .set('Authorization', regularUserAccessToken)
            .send(dataRequest)
            .expect(200);
        expect(response.body.data.deleteResource).toEqual(null);
        expect(response.body.errors).toEqual(
            expect.arrayContaining([
                expect.objectContaining({ errorType: 'Unauthorized' })
            ])
        );
    });

    it('allow deleting resource by administrative user', async () => {
        dataRequest = `{"query":"mutation deleteResource {deleteResource(resourceid: \\"${newResourceId}\\") }","variables":{}}`
        const response = await request.post("")
            .set('Content-Type', 'application/json')
            .set('Authorization', adminUserIdToken)
            .send(dataRequest)
            .expect(200);
        expect(response.body.data.deleteResource).toBe(newResourceId);
    });

    it('deny deleting location by regular user', async () => {
        dataRequest = `{"query":"mutation deleteLocation {deleteLocation(locationid: \\"${newLocationId}\\") }","variables":{}}`
        const response = await request.post("")
            .set('Content-Type', 'application/json')
            .set('Authorization', regularUserAccessToken)
            .send(dataRequest)
            .expect(200);
        expect(response.body.data.deleteLocation).toEqual(null);
        expect(response.body.errors).toEqual(
            expect.arrayContaining([
                expect.objectContaining({ errorType: 'Unauthorized' })
            ])
        );
    });

    it('allow deleting location by administrative user', async () => {
        dataRequest = `{"query":"mutation deleteLocation {deleteLocation(locationid: \\"${newLocationId}\\") }","variables":{}}`
        const response = await request.post("")
            .set('Content-Type', 'application/json')
            .set('Authorization', adminUserIdToken)
            .send(dataRequest)
            .expect(200);
        expect(response.body.data.deleteLocation).toBe(newLocationId);
    });

    it('capture new location addition via subscription', async () => {
        expect(locationSubscription.messages.length).toBe(1);
        data = JSON.parse(locationSubscription.messages[0]);
        expect(data.payload.data.locationCreated.locationid).toBe(newLocationId);
        expect(data.payload.data.locationCreated.name).toBe(newLocation.name);
        expect(data.payload.data.locationCreated.description).toBe(newLocation.description);
        expect(data.payload.data.locationCreated.imageUrl).toBe(newLocation.imageUrl);
        locationSubscription.close();
    });

    it('capture new resource addition via subscription', async () => {
        expect(resourceSubscription.messages.length).toBe(1);
        data = JSON.parse(resourceSubscription.messages[0]);
        expect(data.payload.data.resourceCreated.resourceid).toBe(newResourceId);
        expect(data.payload.data.resourceCreated.locationId).toBe[newLocationId];
        expect(data.payload.data.resourceCreated.name).toBe(newResource.name);
        expect(data.payload.data.resourceCreated.description).toBe(newResource.description);
        expect(data.payload.data.resourceCreated.type).toBe(newResource.type);
        resourceSubscription.close();
    });

    it('capture new booking addition via subscription', async () => {
        expect(bookingSubscription.messages.length).toBe(2);
        data = JSON.parse(bookingSubscription.messages[0]);
        expect(data.payload.data.bookingCreated.bookingid).toBe(newSelfBookingId);
        expect(data.payload.data.bookingCreated.resourceid).toBe(newResourceId);
        expect(data.payload.data.bookingCreated.userid).toBe(regularUserSub);
        bookingSubscription.close();
    });


});
