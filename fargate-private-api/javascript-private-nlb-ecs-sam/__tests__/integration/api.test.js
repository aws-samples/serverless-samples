// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

// The test suite expects test_init.sh to run in advance to clean up databse, 
// export user identity information, etc. It is performed automatically by testpec.yml in CI/CD pipeline

var supertest = require('supertest');

const apiEndpoint = process.env.API_ENDPOINT;
const regularUserIdToken = process.env.REGULAR_USER_ID_TOKEN;
const regularUserSub = process.env.REGULAR_USER_SUB;
const adminUserIdToken = process.env.ADMIN_USER_ID_TOKEN;
const adminUserSub = process.env.ADMIN_USER_SUB;

// This includes all tests for API 
describe('Test API endpoint', () => {
    var request;
    var newLocationId;
    var newResourceId;
    var newBookingId;
    var newLocation = {"imageUrl": "https://api.example.com/venetian.jpg", "description": "Headquorters in New Yorks", "name": "HQ"};
    var newInvalidLocation = {"imageURL": "https://api.example.com/venetian.jpg", "description": "Headquorters in New Yorks"};
    var newResource = {"description": "Fishbowl, Level 2", "name": "FL-2", "type": "room"};
    var newBooking = {"starttimeepochtime" : 1617278400};

    // One-time setup 
    beforeAll(() => {
        request = supertest(apiEndpoint);
        jest.setTimeout(10000)
    });

    // Clean up after the tests are over 
    afterAll(() => {
    });

    it('deny access to the locations without authentication', async () => {
        return request.get("/locations")
            .send()
            .expect(401)
    });

    it('returns an array of locations', async () => {
        const response = await request.get("/locations")
            .set('Authorization', regularUserIdToken)
            .send()
            .expect(200)
        expect(response.body).toHaveProperty("items");
        expect(response.body.items).toEqual(expect.any(Array))
    });

    it('deny adding location by regular user', async () => {
        const response = await request.put("/locations")
            .set('Authorization', regularUserIdToken)
            .send(newLocation)
            .expect(403)
    });

    it('deny adding invalid location', async () => {
        const response = await request.put("/locations")
            .set('Authorization', adminUserIdToken)
            .send(newInvalidLocation)
            .expect(400)
    });

    it('allow adding location by administrative user', async () => {
        const response = await request.put("/locations")
            .set('Authorization', adminUserIdToken)
            .send(newLocation)
            .expect(201)
        expect(response.body.name).toBe(newLocation.name);
        expect(response.body).toHaveProperty("locationID");
        newLocationId = response.body.locationID;
    });

    it('allow getting location details by regular user', async () => {
        const response = await request.get(`/locations/${newLocationId}`)
            .set('Authorization', regularUserIdToken)
            .send()
            .expect(200)
        expect(response.body.name).toBe(newLocation.name);
        expect(response.body.locationID).toBe(newLocationId);
    });

    it('deny access to the resources without authentication', async () => {
        return request.get(`/locations/${newLocationId}/resources`)
            .send()
            .expect(401)
    });

    it('return empty list of resouces for a new location', async () => {
        const response = await request.get(`/locations/${newLocationId}/resources`)
            .set('Authorization', regularUserIdToken)
            .send()
            .expect(200)
        expect(response.body.length).toBe(0);
    });

    it('deny adding resource by regular user', async () => {
        const response = await request.put(`/locations/${newLocationId}/resources`)
            .set('Authorization', regularUserIdToken)
            .send(newResource)
            .expect(403)
    });

    it('allow adding resource by administrative user', async () => {
        const response = await request.put(`/locations/${newLocationId}/resources`)
            .set('Authorization', adminUserIdToken)
            .send(newResource)
            .expect(201)
        expect(response.body.name).toBe(newResource.name);
        expect(response.body).toHaveProperty("resourceID");
        expect(response.body).toHaveProperty("locationID");
        expect(response.body.locationID).toBe(newLocationId);
        newResourceId = response.body.resourceID;
        newBooking.resourceID = newResourceId;
    });

    it('allow getting resource details by regular user', async () => {
        const response = await request.get(`/locations/${newLocationId}/resources/${newResourceId}`)
            .set('Authorization', regularUserIdToken)
            .send()
            .expect(200)
        expect(response.body.name).toBe(newResource.name);
        expect(response.body.resourceID).toBe(newResourceId);
        expect(response.body.locationID).toBe(newLocationId);
    });

    it('deny access to the bookings without authentication', async () => {
        return request.get(`/locations/${newLocationId}/resources/${newResourceId}/bookings`)
            .send()
            .expect(401)
    });

    it('return empty list of bookings for a new resource', async () => {
        const response = await request.get(`/locations/${newLocationId}/resources/${newResourceId}/bookings`)
            .set('Authorization', regularUserIdToken)
            .send()
            .expect(200)
        expect(response.body.length).toBe(0);
    });

    it('deny adding booking for somebody else', async () => {
        const response = await request.put(`/users/${adminUserSub}/bookings`)
            .set('Authorization', regularUserIdToken)
            .send(newBooking)
            .expect(403)
    });

    it('deny adding booking for somebody else even if you are administrator', async () => {
        const response = await request.put(`/users/${regularUserSub}/bookings`)
            .set('Authorization', adminUserIdToken)
            .send(newBooking)
            .expect(403)
    });

    it('deny getting bookings list for somebody else', async () => {
        const response = await request.get(`/users/${adminUserSub}/bookings`)
            .set('Authorization', regularUserIdToken)
            .send(newBooking)
            .expect(403)
    });

    it('deny getting bookings list for somebody else even if you are administrator', async () => {
        const response = await request.get(`/users/${regularUserSub}/bookings`)
            .set('Authorization', adminUserIdToken)
            .send(newBooking)
            .expect(403)
    });

    it('return empty list of bookings for a new user', async () => {
        const response = await request.get(`/users/${regularUserSub}/bookings`)
            .set('Authorization', regularUserIdToken)
            .send()
            .expect(200)
        expect(response.body.length).toBe(0);
    });

    it('allow adding booking for yourself', async () => {
        const response = await request.put(`/users/${regularUserSub}/bookings`)
            .set('Authorization', regularUserIdToken)
            .send(newBooking)
            .expect(201)
        expect(response.body).toHaveProperty("bookingID");
        expect(response.body).toHaveProperty("userID");
        expect(response.body.userID).toBe(regularUserSub);
        expect(response.body.resourceID).toBe(newResourceId);
        newBookingId = response.body.bookingID;
    });

    it('return list with a single newly added booking for a resource', async () => {
        const response = await request.get(`/locations/${newLocationId}/resources/${newResourceId}/bookings`)
            .set('Authorization', regularUserIdToken)
            .send()
            .expect(200)
        expect(response.body.length).toBe(1);
    });

    it('return list with a single newly added booking for a user', async () => {
        const response = await request.get(`/users/${regularUserSub}/bookings`)
            .set('Authorization', regularUserIdToken)
            .send()
            .expect(200)
        expect(response.body.length).toBe(1);
    });

    it('allow getting details for your booking', async () => {
        const response = await request.get(`/users/${regularUserSub}/bookings/${newBookingId}`)
            .set('Authorization', regularUserIdToken)
            .send()
            .expect(200)
        expect(response.body.bookingID).toBe(newBookingId);
        expect(response.body.resourceID).toBe(newResourceId);
        expect(response.body.userID).toBe(regularUserSub);
    });

    it('deny getting details for somebody else\'s booking even if you are administrator', async () => {
        const response = await request.get(`/users/${regularUserSub}/bookings/${newBookingId}`)
            .set('Authorization', adminUserIdToken)
            .send()
            .expect(403)
    });

    it('deny deleting of somebody else\'s booking even if you are administrator', async () => {
        const response = await request.delete(`/users/${regularUserSub}/bookings/${newBookingId}`)
            .set('Authorization', adminUserIdToken)
            .send()
            .expect(403)
    });

    it('allow deleting of your own booking', async () => {
        const response = await request.delete(`/users/${regularUserSub}/bookings/${newBookingId}`)
            .set('Authorization', regularUserIdToken)
            .send()
            .expect(200)
    });

    it('deny deleting resource by regular user', async () => {
        const response = await request.delete(`/locations/${newLocationId}/resources/${newResourceId}`)
            .set('Authorization', regularUserIdToken)
            .send()
            .expect(403)
    });

    it('allow deleting resource by administrative user', async () => {
        const response = await request.delete(`/locations/${newLocationId}/resources/${newResourceId}`)
            .set('Authorization', adminUserIdToken)
            .send()
            .expect(200)
    });

    it('deny deleting location by regular user', async () => {
        const response = await request.delete(`/locations/${newLocationId}`)
            .set('Authorization', regularUserIdToken)
            .send()
            .expect(403)
    });

    it('allow deleting location by administrative user', async () => {
        const response = await request.delete(`/locations/${newLocationId}`)
            .set('Authorization', adminUserIdToken)
            .send()
            .expect(200)
    });
});
