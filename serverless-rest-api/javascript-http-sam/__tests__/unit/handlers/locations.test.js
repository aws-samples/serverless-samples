// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

const lambda = require('../../../src/api/locations.js'); 
const { DynamoDBDocument } = require('@aws-sdk/lib-dynamodb');
const mockdate = require('mockdate');

// Mock uuid
const uuidvalue = 'f8216640-91a2-11eb-8ab9-57aa454facef'
jest.mock('uuid', () => ({ v1: () =>  uuidvalue}));

// This includes all tests for locations handler 
describe('Test locations handler', () => { 
    let scanSpy, getSpy, deleteSpy, putSpy; 

    // Test one-time setup and teardown, see more in https://jestjs.io/docs/en/setup-teardown 
    beforeAll(() => { 
        // Mock dynamodb methods
        // https://jestjs.io/docs/en/jest-object.html#jestspyonobject-methodname 
        scanSpy = jest.spyOn(DynamoDBDocument.prototype, 'scan'); 
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
        mockdate.reset();
    }); 
 
     it('should return list of locations', async () => { 
        const items =  {
            "Items": [
                {
                    "locationid": "f8216640-91a2-11eb-8ab9-57aa454facef",
                    "description": "Las Vegas",
                    "name": "The Venetian",
                    "timestamp": "2021-03-30T21:57:49.860Z"
                },
                {
                    "locationid": "31a9f940-917b-11eb-9054-67837e2c40b0",
                    "description": "Las Vegas",
                    "name": "Encore",
                    "timestamp": "2021-03-30T17:13:06.516Z"
                }
            ],
            "Count": 2,
            "ScannedCount": 2
        };
 
        // Return the specified value whenever the spied function is called 
        scanSpy.mockReturnValue(items); 
 
        const event = { 
            "routeKey": "GET /locations",
            "rawPath": "/locations",
            "requestContext": {
                "requestId":"e0GDshQXoAMEJug="
            }
        } 
 
        // Invoke Lambda handler 
        const result = await lambda.handler(event); 
 
        const expectedResult = { 
            statusCode: 200, 
            body: JSON.stringify(items),
            headers : {
                "Content-Type": "application/json"
              }
        }; 
 
        // Compare the result with the expected result 
        expect(result).toEqual(expectedResult); 
    }); 

    it('should return single location for valid ID', async () => { 
        const item =  {
            "Item": {
                "locationid": "f8216640-91a2-11eb-8ab9-57aa454facef",
                "description": "Las Vegas",
                "name": "The Venetian",
                "timestamp": "2021-03-30T21:57:49.860Z"
            }
        };
         
        // Return the specified value whenever the spied function is called 
        getSpy.mockReturnValue(item); 
 
        const event = { 
            "routeKey": "GET /locations/{locationid}",
            "rawPath": "/locations/f8216640-91a2-11eb-8ab9-57aa454facef",
            "requestContext": {
                "requestId":"e0GDshQXoAMEJug="
            },
            "pathParameters": {
                "locationid": "f8216640-91a2-11eb-8ab9-57aa454facef"
            }
        } 
 
        // Invoke Lambda handler 
        const result = await lambda.handler(event); 
 
        const expectedResult = { 
            statusCode: 200, 
            body: JSON.stringify(item),
            headers : {
                "Content-Type": "application/json"
              }
        }; 
 
        // Compare the result with the expected result 
        expect(result).toEqual(expectedResult); 
    }); 

    it('should return empty result for invalid ID', async () => { 
        const item =  {};
         
        // Return the specified value whenever the spied function is called 
        getSpy.mockReturnValue(item); 
 
        const event = { 
            "routeKey": "GET /locations/{locationid}",
            "rawPath": "/locations/fd6cdda0-917a-11eb-9054-67837e2c40b0",
            "requestContext": {
                "requestId":"e0GDshQXoAMEJug="
            },
            "pathParameters": {
                "locationid": "fd6cdda0-917a-11eb-9054-67837e2c40b0"
            }
        } 
 
        // Invoke Lambda handler 
        const result = await lambda.handler(event); 
 
        const expectedResult = { 
            statusCode: 200, 
            body: JSON.stringify(item),
            headers : {
                "Content-Type": "application/json"
              }
        }; 
 
        // Compare the result with the expected result 
        expect(result).toEqual(expectedResult); 
    }); 

    it('should add new location', async () => { 
        const item = {};
         
        // Return the specified value whenever the spied function is called 
        putSpy.mockReturnValue(item); 

        const event = { 
            "routeKey": "PUT /locations",
            "rawPath": "/locations",
            "requestContext": {
                "requestId":"e0GDshQXoAMEJug="
            },
            "body": "{\"imageUrl\":\"https://s3.amazonaws.com/spacefinder-public-image-repository/venetian.jpg\",\"description\":\"Las Vegas\",\"name\":\"The Venetian\"}",
        } 

        requestJSON = JSON.parse(event.body);
        const newItem = {
            locationid: uuidvalue,
            timestamp: new Date().toISOString(),
            description: requestJSON.description,
            imageUrl: requestJSON.imageUrl,
            name: requestJSON.name
  
        }
 
        // Invoke Lambda handler 
        const result = await lambda.handler(event); 
 
        const expectedNewItemResult = { 
            statusCode: 200, 
            body: JSON.stringify(newItem),
            headers : {
                "Content-Type": "application/json"
              }
        }; 
 
        // Compare the result with the expected result 
        expect(result).toEqual(expectedNewItemResult); 
    }); 

    it('should delete location by ID', async () => { 
        const deleteItem =  {};
         
        // Return the specified value whenever the spied function is called 
        deleteSpy.mockReturnValue(deleteItem); 
 
        const event = { 
            "routeKey": "DELETE /locations/{locationid}",
            "rawPath": "/locations/1ec9b8a0-9244-11eb-ab60-99d5acd6d148",
            "requestContext": {
                "requestId":"e0GDshQXoAMEJug="
            },
            "pathParameters": {
                "locationid": "1ec9b8a0-9244-11eb-ab60-99d5acd6d148"
            }
        } 
 
        // Invoke Lambda handler 
        const result = await lambda.handler(event); 
 
        const expectedDeletionResult = { 
            statusCode: 200, 
            body: JSON.stringify(deleteItem),
            headers : {
                "Content-Type": "application/json"
              }
        }; 
 
        // Compare the result with the expected result 
        expect(result).toEqual(expectedDeletionResult); 
    }); 

}); 
