// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

const lambda = require('../../../src/api/bookings.js');
const { DynamoDBDocument } = require('@aws-sdk/lib-dynamodb');
const mockdate = require('mockdate');

// Mock uuid
const uuidvalue = 'f8216640-91a2-11eb-8ab9-57aa454facef'
jest.mock('uuid', () => ({ v1: () =>  uuidvalue}));

// This includes all tests for locations handler 
describe('Test bookings handler', () => {
    let scanSpy, getSpy, deleteSpy, querySpy, putSpy;

    // Test one-time setup and teardown, see more in https://jestjs.io/docs/en/setup-teardown 
    beforeAll(() => {
        // Mock dynamodb methods
        // https://jestjs.io/docs/en/jest-object.html#jestspyonobject-methodname 
        scanSpy = jest.spyOn( DynamoDBDocument.prototype, 'scan');
        querySpy = jest.spyOn(DynamoDBDocument.prototype, 'query');
        getSpy = jest.spyOn(DynamoDBDocument.prototype, 'get');
        putSpy = jest.spyOn(DynamoDBDocument.prototype, 'put');
        deleteSpy = jest.spyOn(DynamoDBDocument.prototype, 'delete');

        // Mock other functions
        mockdate.set(1600000000000)
       
    });

    // Clean up mocks 
    afterAll(() => {
        scanSpy.mockRestore();
        getSpy.mockRestore();
        putSpy.mockRestore();
        deleteSpy.mockRestore();
        querySpy.mockRestore();
        mockdate.reset();
    });

    it('should return list of bookings for the user', async () => {
        const items = {
            "Items": [
                {
                    "bookingid": "15f5c040-933c-11eb-ae5f-13d2a94dc9c8",
                    "resourceid": "f8216640-91a2-11eb-8ab9-57aa454facef",
                    "userid": "123456",
                    "timestamp": "2021-04-01T22:46:24.068Z"
                }
            ],
            "Count": 1,
            "ScannedCount": 1
        };

        // Return the specified value whenever the spied function is called 
        querySpy.mockReturnValue(items);

        const event = {
            "routeKey": "GET /users/{userid}/bookings",
            "rawPath": "/users/123456/bookings",
            "requestContext": {
                "requestId":"e0GDshQXoAMEJug="
            },
            "pathParameters": {
                "userid": "f8216640-91a2-11eb-8ab9-57aa454facef"
            }
        }

        // Invoke Lambda handler 
        const result = await lambda.handler(event);

        const expectedResult = {
            statusCode: 200,
            body: JSON.stringify(items),
            headers: {
                "Content-Type": "application/json"
            }
        };

        // Compare the result with the expected result 
        expect(result).toEqual(expectedResult);
    });

    it('should return list of bookings for the resource', async () => {
        const items = {
            "Items": [
                {
                    "bookingid": "b4c755b0-933e-11eb-bbca-998fedd8816f",
                    "starttimeepochtime": 1617278400,
                    "resourceid": "f8216640-91a2-11eb-8ab9-57aa454facef",
                    "userid": "123456",
                    "timestamp": "2021-04-01T23:05:09.515Z"
                }
            ],
            "Count": 1,
            "ScannedCount": 1
        };

        // Return the specified value whenever the spied function is called 
        querySpy.mockReturnValue(items);

        const event = {
            "routeKey": "GET /locations/{locationid}/resources/{resourceid}/bookings",
            "rawPath": "/locations/31a9f940-917b-11eb-9054-67837e2c40b0/resources/f8216640-91a2-11eb-8ab9-57aa454facef/bookings",
            "requestContext": {
                "requestId":"e0GDshQXoAMEJug="
            },
            "pathParameters": {
                "locationid": "31a9f940-917b-11eb-9054-67837e2c40b0",
                "resourceid":"f8216640-91a2-11eb-8ab9-57aa454facef"
            }
        }

        // Invoke Lambda handler 
        const result = await lambda.handler(event);

        const expectedResult = {
            statusCode: 200,
            body: JSON.stringify(items),
            headers: {
                "Content-Type": "application/json"
            }
        };

        // Compare the result with the expected result 
        expect(result).toEqual(expectedResult);
    });

    it('should return single booking for valid ID', async () => {
        const item = {
            "Item": {
                "bookingid": "15f5c040-933c-11eb-ae5f-13d2a94dc9c8",
                "resourceid": "f8216640-91a2-11eb-8ab9-57aa454facef",
                "userid": "123456",
                "timestamp": "2021-04-01T22:46:24.068Z"
            }
        };

        // Return the specified value whenever the spied function is called 
        getSpy.mockReturnValue(item);

        const event = {
            "routeKey": "GET /users/{userid}/bookings/{bookingid}",
            "rawPath": "/users/123456/bookings/15f5c040-933c-11eb-ae5f-13d2a94dc9c8",
            "requestContext": {
                "requestId":"e0GDshQXoAMEJug="
            },
            "pathParameters": {
                "userid": "123456",
                "bookingid": "15f5c040-933c-11eb-ae5f-13d2a94dc9c8"
            }
        }

        // Invoke Lambda handler 
        const result = await lambda.handler(event);

        const expectedResult = {
            statusCode: 200,
            body: JSON.stringify(item),
            headers: {
                "Content-Type": "application/json"
            }
        };

        // Compare the result with the expected result 
        expect(result).toEqual(expectedResult);
    });

    it('should return empty result for invalid booking ID', async () => {
        const item = {};

        // Return the specified value whenever the spied function is called 
        getSpy.mockReturnValue(item);

        const event = {
            "routeKey": "GET /users/{userid}/bookings/{bookingid}",
            "rawPath": "/users/123456/bookings/246396e0-9308-11eb-87e3-8f538c287000",
            "requestContext": {
                "requestId":"e0GDshQXoAMEJug="
            },
            "pathParameters": {
                "userid": "123456",
                "bookingid": "246396e0-9308-11eb-87e3-8f538c287000"
            }
        }

        // Invoke Lambda handler 
        const result = await lambda.handler(event);

        const expectedResult = {
            statusCode: 200,
            body: JSON.stringify(item),
            headers: {
                "Content-Type": "application/json"
            }
        };

        // Compare the result with the expected result 
        expect(result).toEqual(expectedResult);
    });

    it('should add new booking for the user', async () => {
        const item = {};

        // Return the specified value whenever the spied function is called 
        putSpy.mockReturnValue(item);

        const event = {
            "routeKey": "PUT /users/{userid}/bookings",
            "rawPath": "/users/123456/bookings",
            "body": "{\"resourceid\":\"f8216640-91a2-11eb-8ab9-57aa454facef\",\"starttimeepochtime\":1617278400}",
            "requestContext": {
                "requestId":"e0GDshQXoAMEJug="
            },
            "pathParameters": {
                "userid": "123456"
            }
        }

        requestJSON = JSON.parse(event.body);
        const newItem = {
            bookingid: uuidvalue,
            userid: event.pathParameters.userid,
            resourceid: requestJSON.resourceid,
            starttimeepochtime: requestJSON.starttimeepochtime,
            timestamp: new Date().toISOString()
        }

        // Invoke Lambda handler 
        const result = await lambda.handler(event);
        const expectedNewItemResult = {
            statusCode: 200,
            body: JSON.stringify(newItem),
            headers: {
                "Content-Type": "application/json"
            }
        };

        // Compare the result with the expected result 
        expect(result).toEqual(expectedNewItemResult);
    });

    it('should delete booking by ID', async () => {
        const deleteItem = {};

        // Return the specified value whenever the spied function is called 
        deleteSpy.mockReturnValue(deleteItem);

        const event = {
            "routeKey": "DELETE /users/{userid}/bookings/{bookingid}",
            "rawPath": "/users/123456/resources/246396e0-9308-11eb-87e3-8f538c287000",
            "requestContext": {
                "requestId":"e0GDshQXoAMEJug="
            },
            "pathParameters": {
                "userid": "123456",
                "bookingid": "246396e0-9308-11eb-87e3-8f538c287000"
            }
        }

        // Invoke Lambda handler 
        const result = await lambda.handler(event);

        const expectedDeletionResult = {
            statusCode: 200,
            body: JSON.stringify(deleteItem),
            headers: {
                "Content-Type": "application/json"
            }
        };

        // Compare the result with the expected result 
        expect(result).toEqual(expectedDeletionResult);
    });

});
