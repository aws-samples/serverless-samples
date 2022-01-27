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
describe('Test bookings handler', () => { 
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
        querySpy.mockRestore();
        mockdate.reset();
    }); 
 
     it('should return list of bookings for the user', async () => { 
        const items = {
            "Items": [
                {
                    "bookingID": "15f5c040-933c-11eb-ae5f-13d2a94dc9c8",
                    "resourceID": "f8216640-91a2-11eb-8ab9-57aa454facef",
                    "userID": "123456",
                    "timestamp": "2021-04-01T22:46:24.068Z"
                }
            ],
            "Count": 1,
            "ScannedCount": 1
        };
 
        // Return the specified value whenever the spied function is called 
        querySpy.mockReturnValue(items);
 
        // Invoke Express route
        const response = await request(app).get('/users/123456/bookings');
 
        // Compare the result with the expected result 

        const expectedItems = [
            {
                "bookingID": "15f5c040-933c-11eb-ae5f-13d2a94dc9c8",
                "resourceID": "f8216640-91a2-11eb-8ab9-57aa454facef",
                "userID": "123456",
                "timestamp": "2021-04-01T22:46:24.068Z"
            }
        ];
        expect(response.statusCode).toBe(200);
        expect(response.get('Content-Type')).toEqual("application/json; charset=utf-8");
        expect(response.body).toEqual(expectedItems); 
    });

    it('should return list of bookings for the resource', async () => { 
        const items = {
            "Items": [
                {
                    "bookingID": "b4c755b0-933e-11eb-bbca-998fedd8816f",
                    "starttimeepochtime": 1617278400,
                    "resourceID": "f8216640-91a2-11eb-8ab9-57aa454facef",
                    "userID": "123456",
                    "timestamp": "2021-04-01T23:05:09.515Z"
                }
            ],
            "Count": 1,
            "ScannedCount": 1
        };
 
        // Return the specified value whenever the spied function is called 
        querySpy.mockReturnValue(items);
 
        // Invoke Express route
        const response = await request(app).get('/locations/31a9f940-917b-11eb-9054-67837e2c40b0/resources/f8216640-91a2-11eb-8ab9-57aa454facef/bookings');
 
        // Compare the result with the expected result 

        const expectedItems = [
            {
                "bookingID": "b4c755b0-933e-11eb-bbca-998fedd8816f",
                "starttimeepochtime": 1617278400,
                "resourceID": "f8216640-91a2-11eb-8ab9-57aa454facef",
                "userID": "123456",
                "timestamp": "2021-04-01T23:05:09.515Z"
            }
        ];
        expect(response.statusCode).toBe(200);
        expect(response.get('Content-Type')).toEqual("application/json; charset=utf-8");
        expect(response.body).toEqual(expectedItems); 
    }); 

    it('should return single booking for valid ID', async () => { 
        const item =  {
            "Item": {
                "bookingID": "15f5c040-933c-11eb-ae5f-13d2a94dc9c8",
                "resourceID": "f8216640-91a2-11eb-8ab9-57aa454facef",
                "userID": "123456",
                "timestamp": "2021-04-01T22:46:24.068Z"
            }
        };
         
        // Return the specified value whenever the spied function is called 
        getSpy.mockReturnValue(item); 
 
        // Invoke Express route
        const response = await request(app).get('/users/123456/bookings/15f5c040-933c-11eb-ae5f-13d2a94dc9c8');
 
        // Compare the result with the expected result

        const expectedItem =  {
            "bookingID": "15f5c040-933c-11eb-ae5f-13d2a94dc9c8",
                "resourceID": "f8216640-91a2-11eb-8ab9-57aa454facef",
                "userID": "123456",
                "timestamp": "2021-04-01T22:46:24.068Z"
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
        const response = await request(app).get('/users/123456/bookings/15f5c040-933c-11eb-ae5f-13d2a94dc9c8');
 
        // Compare the result with the expected result 
        expect(response.statusCode).toBe(404);
    }); 

    it('should add new booking for the user', async () => { 
        const item = {};
         
        // Return the specified value whenever the spied function is called 
        putSpy.mockReturnValue(item); 

        const userID = "123456";
        const payload = {
            resourceID: 'f8216640-91a2-11eb-8ab9-57aa454facef',
            starttimeepochtime: 1617278400
        };
        
        // Invoke Express route
        const response = await request(app).put(`/users/${userID}/bookings`).send(payload);

        const expectedItem = {
            bookingID: uuidvalue,
            userID,
            resourceID: payload.resourceID,
            timestamp: new Date().toISOString(),
            starttimeepochtime: payload.starttimeepochtime
        }
 
        // Compare the result with the expected result 
        expect(response.statusCode).toBe(201);
        expect(response.get('Content-Type')).toEqual("application/json; charset=utf-8");
        expect(response.body).toEqual(expectedItem); 
    }); 

    it('should delete booking by ID', async () => { 
        const deleteItem =  {};
         
        // Return the specified value whenever the spied function is called 
        deleteSpy.mockReturnValue(deleteItem);
 
        // Invoke Express route
        const response = await request(app).delete('/users/123456/bookings/246396e0-9308-11eb-87e3-8f538c287000');
 
        // Compare the result with the expected result 
        expect(response.statusCode).toBe(200);
    }); 
}); 
