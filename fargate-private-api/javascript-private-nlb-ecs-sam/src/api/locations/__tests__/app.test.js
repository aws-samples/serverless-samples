// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
const request = require('supertest');
const { app } = require('../app');
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
                    "locationID": "f8216640-91a2-11eb-8ab9-57aa454facef",
                    "description": "Las Vegas",
                    "name": "The Venetian",
                    "timestamp": "2021-03-30T21:57:49.860Z"
                },
                {
                    "locationID": "31a9f940-917b-11eb-9054-67837e2c40b0",
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
 
        // Invoke Express route
        const response = await request(app).get('/locations');
 
        // Compare the result with the expected result 

        const expectedItems = {
            items: [
                {
                    "locationID": "f8216640-91a2-11eb-8ab9-57aa454facef",
                    "description": "Las Vegas",
                    "name": "The Venetian",
                    "timestamp": "2021-03-30T21:57:49.860Z"
                },
                {
                    "locationID": "31a9f940-917b-11eb-9054-67837e2c40b0",
                    "description": "Las Vegas",
                    "name": "Encore",
                    "timestamp": "2021-03-30T17:13:06.516Z"
                }
            ]
        };
        expect(response.statusCode).toBe(200);
        expect(response.get('Content-Type')).toEqual("application/json; charset=utf-8");
        expect(response.body).toEqual(expectedItems); 
    }); 

    it('should return single location for valid ID', async () => { 
        const item =  {
            "Item": {
                "locationID": "f8216640-91a2-11eb-8ab9-57aa454facef",
                "description": "Las Vegas",
                "name": "The Venetian",
                "timestamp": "2021-03-30T21:57:49.860Z"
            }
        };
         
        // Return the specified value whenever the spied function is called 
        getSpy.mockReturnValue(item); 
 
        // Invoke Express route
        const response = await request(app).get('/locations/f8216640-91a2-11eb-8ab9-57aa454facef');
 
        // Compare the result with the expected result

        const expectedItem =  {
            "locationID": "f8216640-91a2-11eb-8ab9-57aa454facef",
            "description": "Las Vegas",
            "name": "The Venetian",
            "timestamp": "2021-03-30T21:57:49.860Z"
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
        const response = await request(app).get('/locations/fd6cdda0-917a-11eb-9054-67837e2c40b0');
 
        // Compare the result with the expected result 
        expect(response.statusCode).toBe(404);
    }); 

    it('should add new location', async () => { 
        const item = {};
         
        // Return the specified value whenever the spied function is called 
        putSpy.mockReturnValue(item); 

        const payload = {
            imageUrl: 'https://s3.amazonaws.com/spacefinder-public-image-repository/venetian.jpg',
            description: 'Las Vegas',
            name: 'The Venetian'
        };
        
        // Invoke Express route
        const response = await request(app).put('/locations').send(payload);

        const expectedItem = {
            locationID: uuidvalue,
            timestamp: new Date().toISOString(),
            description: payload.description,
            imageUrl: payload.imageUrl,
            name: payload.name
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
        const response = await request(app).delete('/locations/1ec9b8a0-9244-11eb-ab60-99d5acd6d148');
 
        // Compare the result with the expected result 
        expect(response.statusCode).toBe(200);
    }); 
}); 
