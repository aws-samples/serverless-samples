// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
const request = require('supertest');
const { app } = require('../app');
const { DynamoDBDocument } = require('@aws-sdk/lib-dynamodb');
const mockdate = require('mockdate');

// Mock uuid
const uuidvalue = 'f8216640-91a2-11eb-8ab9-57aa454facef'
jest.mock('uuid', () => ({ v1: () =>  uuidvalue}));

// This includes all tests for resources handler 
describe('Test resources handler', () => { 
    let scanSpy, getSpy, deleteSpy, putSpy; 

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
 
        // Invoke Express route
        const response = await request(app).get('/locations/f8216640-91a2-11eb-8ab9-57aa454facef/resources');
 
        // Compare the result with the expected result 

        const expectedItems = [
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
        ];
        expect(response.statusCode).toBe(200);
        expect(response.get('Content-Type')).toEqual("application/json; charset=utf-8");
        expect(response.body).toEqual(expectedItems); 
    }); 

    it('should return single resource for valid ID', async () => { 
        const item =  {
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
 
        // Invoke Express route
        const response = await request(app).get('/locations/f8216640-91a2-11eb-8ab9-57aa454facef/resources/246396e0-9308-11eb-87e3-8f538c287bfc');
 
        // Compare the result with the expected result

        const expectedItem =  {
            "locationid": "f8216640-91a2-11eb-8ab9-57aa454facef",
            "description": "Venetian Level 3",
            "name": "Toscana 3606, Room 6",
            "resourceid": "246396e0-9308-11eb-87e3-8f538c287bfc",
            "type": "room",
            "timestamp": "2021-04-01T16:34:34.446Z"
        };

        expect(response.statusCode).toBe(200);
        expect(response.get('Content-Type')).toEqual("application/json; charset=utf-8");
        expect(response.body).toEqual(expectedItem); 
    }); 

    it('should return 404', async () => { 
        const item =  {};
         
        // Return the specified value whenever the spied function is called 
        getSpy.mockReturnValue(item); 
 
        // Invoke Express route
        const response = await request(app).get('/locations/f8216640-91a2-11eb-8ab9-57aa454facef/resources/246396e0-9308-11eb-87e3-8f538c287000');
 
        // Compare the result with the expected result 
        expect(response.statusCode).toBe(404);
    }); 

    it('should add new resource to the location', async () => { 
        const item = {};
         
        // Return the specified value whenever the spied function is called 
        putSpy.mockReturnValue(item); 

        const locationid = 'f8216640-91a2-11eb-8ab9-57aa454facef';
        const payload = {
            name: 'Titian 2205',
            description: 'Venetian Level 2',
            type: 'room'
        };
        
        // Invoke Express route
        const response = await request(app).put(`/locations/${locationid}/resources`).send(payload);

        const expectedItem = {
            resourceid: uuidvalue,
            locationid,
            timestamp: new Date().toISOString(),
            description: payload.description,
            name: payload.name,
            type: payload.type
        }
 
        // Compare the result with the expected result 
        expect(response.statusCode).toBe(201);
        expect(response.get('Content-Type')).toEqual("application/json; charset=utf-8");
        expect(response.body).toEqual(expectedItem); 
    }); 

    it('should delete location by ID', async () => { 
        const deleteItem =  {};
         
        // Return the specified value whenever the spied function is called 
        deleteSpy.mockReturnValue(deleteItem);
 
        // Invoke Express route
        const response = await request(app).delete('/locations/1ec9b8a0-9244-11eb-ab60-99d5acd6d148/resources/246396e0-9308-11eb-87e3-8f538c287000');
 
        // Compare the result with the expected result 
        expect(response.statusCode).toBe(200);
    }); 
}); 
