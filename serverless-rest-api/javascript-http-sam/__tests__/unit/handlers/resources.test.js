// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

const lambda = require('../../../src/api/resources.js');
const { DynamoDBDocument } = require('@aws-sdk/lib-dynamodb');
const mockdate = require('mockdate');

// Mock uuid
const uuidvalue = 'f8216640-91a2-11eb-8ab9-57aa454facef'
jest.mock('uuid', () => ({ v1: () => uuidvalue }));

// This includes all tests for locations handler 
describe('Test resources handler', () => {
    let scanSpy, getSpy, deleteSpy, querySpy, putSpy;

    // Test one-time setup and teardown, see more in https://jestjs.io/docs/en/setup-teardown 
    beforeAll(() => {
        // Mock dynamodb methods
        // https://jestjs.io/docs/en/jest-object.html#jestspyonobject-methodname 
        scanSpy = jest.spyOn(DynamoDBDocument.prototype, 'scan');
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
        querySpy.mockRestore()
        mockdate.reset();
    });

    it('should return list of resources for the location', async () => {
        const items = {
            "Items": [
                {
                    "locationid": "f8216640-91a2-11eb-8ab9-57aa454facef",
                    "description": "Venetian Level 2",
                    "name": "Titian 2205",
                    "resourceid": "759f8770-9309-11eb-87e3-8f538c287bfc",
                    "type": "room",
                    "timestamp": "2021-04-01T16:44:00.231Z"
                },
                {
                    "locationid": "f8216640-91a2-11eb-8ab9-57aa454facef",
                    "description": "Venetian Level 3",
                    "name": "Toscana 3606, Room 6",
                    "resourceid": "246396e0-9308-11eb-87e3-8f538c287bfc",
                    "type": "room",
                    "timestamp": "2021-04-01T16:34:34.446Z"
                }
            ],
            "Count": 2,
            "ScannedCount": 2
        };

        // Return the specified value whenever the spied function is called 
        querySpy.mockReturnValue(items);

        const event = {
            "routeKey": "GET /locations/{locationid}/resources",
            "rawPath": "/locations/f8216640-91a2-11eb-8ab9-57aa454facef/resources",
            "requestContext": {
                "requestId":"e0GDshQXoAMEJug="
            },
            "pathParameters": {
                "locationid": "f8216640-91a2-11eb-8ab9-57aa454facef",
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

    it('should return single resource for valid ID', async () => {
        const item = {
            "Item": {
                "locationid": "f8216640-91a2-11eb-8ab9-57aa454facef",
                "description": "Venetian Level 3",
                "name": "Toscana 3606, Room 6",
                "resourceid": "246396e0-9308-11eb-87e3-8f538c287bfc",
                "type": "room",
                "timestamp": "2021-04-01T16:34:34.446Z"
            }
        };

        // Return the specified value whenever the spied function is called 
        getSpy.mockReturnValue(item);

        const event = {
            "routeKey": "GET /locations/{locationid}/resources/{resourceid}",
            "rawPath": "/locations/f8216640-91a2-11eb-8ab9-57aa454facef/resources/246396e0-9308-11eb-87e3-8f538c287bfc",
            "requestContext": {
                "requestId":"e0GDshQXoAMEJug="
            },
            "pathParameters": {
                "locationid": "f8216640-91a2-11eb-8ab9-57aa454facef",
                "resourceid": "246396e0-9308-11eb-87e3-8f538c287bfc"
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

    it('should return empty result for invalid resource ID', async () => {
        const item = {};

        // Return the specified value whenever the spied function is called 
        getSpy.mockReturnValue(item);

        const event = {
            "routeKey": "GET /locations/{locationid}/resources/{resourceid}",
            "rawPath": "/locations/f8216640-91a2-11eb-8ab9-57aa454facef/resources/246396e0-9308-11eb-87e3-8f538c287000",
            "requestContext": {
                "requestId":"e0GDshQXoAMEJug="
            },
            "pathParameters": {
                "locationid": "f8216640-91a2-11eb-8ab9-57aa454facef",
                "resourceid": "246396e0-9308-11eb-87e3-8f538c287000"
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

    it('should add new resource to the location', async () => {
        const item = {};

        // Return the specified value whenever the spied function is called 
        putSpy.mockReturnValue(item);

        const event = {
            "routeKey": "PUT /locations/{locationid}/resources",
            "rawPath": "/locations/f8216640-91a2-11eb-8ab9-57aa454facef/resources",
            "body": "{\"description\":\"Venetian Level 2\",\"name\":\"Titian 2205\",\"type\":\"room\"}",
            "requestContext": {
                "requestId":"e0GDshQXoAMEJug="
            },
            "pathParameters": {
                "locationid": "f8216640-91a2-11eb-8ab9-57aa454facef"
            }
        }

        requestJSON = JSON.parse(event.body);
        const newItem = {
            resourceid: uuidvalue,
            locationid: event.pathParameters.locationid,
            timestamp: new Date().toISOString(),
            description: requestJSON.description,
            name: requestJSON.name,
            type: requestJSON.type
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

    it('should delete resource by ID', async () => {
        const deleteItem = {};

        // Return the specified value whenever the spied function is called 
        deleteSpy.mockReturnValue(deleteItem);

        const event = {
            "routeKey": "DELETE /locations/{locationid}/resources/{resourceid}",
            "rawPath": "/locations/1ec9b8a0-9244-11eb-ab60-99d5acd6d148/resources/246396e0-9308-11eb-87e3-8f538c287000",
            "requestContext": {
                "requestId":"e0GDshQXoAMEJug="
            },
            "pathParameters": {
                "locationid": "1ec9b8a0-9244-11eb-ab60-99d5acd6d148",
                "resourceid": "246396e0-9308-11eb-87e3-8f538c287000"
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
