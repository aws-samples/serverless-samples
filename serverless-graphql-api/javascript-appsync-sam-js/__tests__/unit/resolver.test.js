// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

const AWS = require('@aws-sdk/client-appsync')
const appSyncClient = new AWS.AppSyncClient({});
const fs = require('fs');

const mappingsBasePath = "./src/resolvers/";
const locationContext = {
    arguments:
    {
        locationid: "1234567890",
        name: "Location Name",
        description: "Location Description",
        imageUrl: "https://www.example.com/image.jpg"
    },
    result: {
        locationid: "1234567890",
        imageUrl: "https://www.example.com/image.jpg",
        name: "Location Name",
        description: "Location Description",
        timestamp: "2023-01-01T00:00:00.000Z"
    }
};
const resourceContext = {
    arguments:
    {
        resourceid: "1234567890",
        locationid: "abcdefghij",
        name: "Resource Name",
        description: "Resource Description",
        type: "Resource Type"
    },
    result:
    {
        resourceid: "1234567890",
        locationid: "abcdefghij",
        name: "Resource Name",
        description: "Resource Description",
        type: "Resource Type",
        timestamp: "2023-01-01T00:00:00.000Z"
    }
};
const bookingContext = {
    arguments:
    {
        bookingid: "1234567890",
        resourceid: "abcdefghij",
    },
    identity:
    {
        sub: "123456-abcdeefg-7890",
        issuer: "",
        username: "johndoe",
        claims: {},
        sourceIp: [
            "x.x.x.x"
        ],
        defaultAuthStrategy: "ALLOW"
    },
    result:
    {
        bookingid: "1234567890",
        resourceid: "abcdefghij",
        starttimeepochtime: 1672578000,
        userid: "123456-abcdeefg-7890",
        timestamp: "2023-01-01T00:00:00.000Z"
    }
};

function getEvaluationResponse(codeFileName, context, functionType) {
    return appSyncClient.send(
        new AWS.EvaluateCodeCommand({
            code: fs.readFileSync(mappingsBasePath + codeFileName, 'utf8'),
            context: JSON.stringify(context),
            runtime: { name: 'APPSYNC_JS', runtimeVersion: '1.0.0' },
            function: functionType
        })
    );
}

describe('Test AppSync resolvers', () => {

    // One-time setup 
    beforeAll(() => {
    });

    // Clean up after the tests are over 
    afterAll(() => {
    });

    it('location create resolver with location id passed as a parameter', async () => {
        var context = JSON.parse(JSON.stringify(locationContext));

        //Test request code
        response = await getEvaluationResponse('create_location_function.js', context, 'request');
        evaluationResult = JSON.parse(response.evaluationResult);
        expect(evaluationResult.operation).toBe("PutItem");
        expect(evaluationResult.key.locationid.S).toBe(context.arguments.locationid);
        expect(evaluationResult.attributeValues.name.S).toBe(context.arguments.name);
        expect(evaluationResult.attributeValues.description.S).toBe(context.arguments.description);
        expect(evaluationResult.attributeValues).toHaveProperty("timestamp");

        //Test response code
        response = await getEvaluationResponse('create_location_function.js', context, 'response');
        evaluationResult = JSON.parse(response.evaluationResult);
        // Check that all result fields are present in the response after transformation
        for (const [key, value] of Object.entries(evaluationResult)) {
            expect(evaluationResult[key]).toBe(context.result[key]);
        }

    });

    it('location create resolver without location id passed as a parameter', async () => {
        var context = JSON.parse(JSON.stringify(locationContext));

        //Test request code
        delete context["arguments"].locationid;
        response = await getEvaluationResponse('create_location_function.js', context, 'request');
        evaluationResult = JSON.parse(response.evaluationResult);
        expect(evaluationResult.operation).toBe("PutItem");
        expect(evaluationResult.key).toHaveProperty("locationid");
        expect(evaluationResult.attributeValues.name.S).toBe(context.arguments.name);
        expect(evaluationResult.attributeValues.description.S).toBe(context.arguments.description);
        expect(evaluationResult.attributeValues).toHaveProperty("timestamp");

        //Test response code
        response = await getEvaluationResponse('create_location_function.js', context, 'response');
        evaluationResult = JSON.parse(response.evaluationResult);
        // Check that all result fields are present in the response after transformation
        for (const [key, value] of Object.entries(evaluationResult)) {
            expect(evaluationResult[key]).toBe(context.result[key]);
        }

    });

    it('location delete resolver', async () => {
        var context = JSON.parse(JSON.stringify(locationContext));

        //Test request code
        response = await getEvaluationResponse('delete_location_function.js', context, 'request');
        evaluationResult = JSON.parse(response.evaluationResult);
        expect(evaluationResult.operation).toBe("DeleteItem");
        expect(evaluationResult.key.locationid.S).toBe(context.arguments.locationid);

        //Test response code
        response = await getEvaluationResponse('delete_location_function.js', context, 'response');
        evaluationResult = JSON.parse(response.evaluationResult);
        expect(evaluationResult).toBe(context.result.locationid);
    });

    it('get single location resolver', async () => {
        var context = JSON.parse(JSON.stringify(locationContext));

        //Test request code
        response = await getEvaluationResponse('get_location_function.js', context, 'request');
        evaluationResult = JSON.parse(response.evaluationResult);
        expect(evaluationResult.operation).toBe("GetItem");
        expect(evaluationResult.key.locationid.S).toBe(context.arguments.locationid);

        //Test response code
        response = await getEvaluationResponse('get_location_function.js', context, 'response');
        evaluationResult = JSON.parse(response.evaluationResult);
        // Check that all result fields are present in the response after transformation
        for (const [key, value] of Object.entries(evaluationResult)) {
            expect(evaluationResult[key]).toBe(context.result[key]);
        }
    });

    it('get all locations resolver', async () => {
        var context = {
            arguments:
            {
            },
            result: {
                items: [
                    {
                        locationid: "0",
                        imageUrl: "url",
                        name: "name",
                        description: "description",
                        timestamp: "2023-01-01T00:00:00.000Z"
                    },
                    {
                        locationid: "2",
                        imageUrl: "url2",
                        name: "name2",
                        description: "description2",
                        timestamp: "2023-01-01T00:00:00.000Z"
                    },
                    {
                        locationid: "1",
                        imageUrl: "url1",
                        name: "name1",
                        description: "description1",
                        timestamp: "2023-01-01T00:00:00.000Z"
                    }
                ],
                "scannedCount": 3
            }
        };

        //Test request code
        response = await getEvaluationResponse('get_locations_function.js', context, 'request');
        evaluationResult = JSON.parse(response.evaluationResult);
        expect(evaluationResult.operation).toBe("Scan");

        //Test response code
        response = await getEvaluationResponse('get_locations_function.js', context, 'response');
        evaluationResult = JSON.parse(response.evaluationResult);
        expect(evaluationResult.length).toBe(Object.keys(context.result.items).length);
        // Check that all items in the results list are present in the response after transformation
        for (i = 0; i < evaluationResult.length; i++) {
            // Check that all result fields are present in the response after transformation
            for (const [key, value] of Object.entries(evaluationResult[i])) {
                expect(evaluationResult[i][key]).toBe(context.result.items[i][key]);
            }
        };
    });

    it('create resource resolver with resource id passed as a parameter ', async () => {
        var context = JSON.parse(JSON.stringify(resourceContext));

        //Test request code
        response = await getEvaluationResponse('create_resource_function.js', context, 'request');
        evaluationResult = JSON.parse(response.evaluationResult);
        expect(evaluationResult.operation).toBe("PutItem");
        expect(evaluationResult.key.resourceid.S).toBe(context.arguments.resourceid);
        expect(evaluationResult.attributeValues.locationid.S).toBe(context.arguments.locationid);
        expect(evaluationResult.attributeValues.name.S).toBe(context.arguments.name);
        expect(evaluationResult.attributeValues.description.S).toBe(context.arguments.description);
        expect(evaluationResult.attributeValues.type.S).toBe(context.arguments.type);
        expect(evaluationResult.attributeValues).toHaveProperty("timestamp");

        //Test response code
        response = await getEvaluationResponse('create_resource_function.js', context, 'response');
        evaluationResult = JSON.parse(response.evaluationResult);
        // Check that all result fields are present in the response after transformation
        for (const [key, value] of Object.entries(evaluationResult)) {
            expect(evaluationResult[key]).toBe(context.result[key]);
        }

    });

    it('create resource resolver without resource id passed as a parameter ', async () => {
        var context = JSON.parse(JSON.stringify(resourceContext));
        delete context["arguments"].resourceid;

        //Test request code
        response = await getEvaluationResponse('create_resource_function.js', context, 'request');
        evaluationResult = JSON.parse(response.evaluationResult);
        expect(evaluationResult.operation).toBe("PutItem");
        expect(evaluationResult.key).toHaveProperty("resourceid");
        expect(evaluationResult.attributeValues.locationid.S).toBe(context.arguments.locationid);
        expect(evaluationResult.attributeValues.name.S).toBe(context.arguments.name);
        expect(evaluationResult.attributeValues.description.S).toBe(context.arguments.description);
        expect(evaluationResult.attributeValues.type.S).toBe(context.arguments.type);
        expect(evaluationResult.attributeValues).toHaveProperty("timestamp");

        //Test response code
        response = await getEvaluationResponse('create_resource_function.js', context, 'response');
        evaluationResult = JSON.parse(response.evaluationResult);
        // Check that all result fields are present in the response after transformation
        for (const [key, value] of Object.entries(evaluationResult)) {
            expect(evaluationResult[key]).toBe(context.result[key]);
        }
    });

    it('delete resource resolver', async () => {
        var context = JSON.parse(JSON.stringify(resourceContext));

        //Test request code
        response = await getEvaluationResponse('delete_resource_function.js', context, 'request');
        evaluationResult = JSON.parse(response.evaluationResult);
        expect(evaluationResult.operation).toBe("DeleteItem");
        expect(evaluationResult.key.resourceid.S).toBe(context.arguments.resourceid);

        //Test response code
        response = await getEvaluationResponse('delete_resource_function.js', context, 'response');
        evaluationResult = JSON.parse(response.evaluationResult);
        expect(evaluationResult).toBe(context.result.resourceid);
    });

    it('get single resource resolver', async () => {
        var context = JSON.parse(JSON.stringify(resourceContext));

        //Test request code
        response = await getEvaluationResponse('get_resource_function.js', context, 'request');
        evaluationResult = JSON.parse(response.evaluationResult);
        expect(evaluationResult.operation).toBe("GetItem");
        expect(evaluationResult.key.resourceid.S).toBe(context.arguments.resourceid);

        //Test response code
        response = await getEvaluationResponse('get_resource_function.js', context, 'response');
        evaluationResult = JSON.parse(response.evaluationResult);
        // Check that all result fields are present in the response after transformation
        for (const [key, value] of Object.entries(evaluationResult)) {
            expect(evaluationResult[key]).toBe(context.result[key]);
        }
    });

    it('get resources for location resolver ', async () => {
        var context = {
            arguments: {
                locationid: "abcdefghij"
            },
            result: {
                items: [
                    {
                        resourceid: "0",
                        locationid: "abcdefghij",
                        name: "Resource Name 0",
                        description: "Resource Description 0",
                        type: "Resource Type 0",
                        timestamp: "2023-01-01T00:00:00.000Z"
                    },
                    {
                        resourceid: "1",
                        locationid: "abcdefghij",
                        name: "Resource Name 1",
                        description: "Resource Description 1",
                        type: "Resource Type 1",
                        timestamp: "2023-01-01T00:00:00.000Z"
                    }
                ],
                scannedCount: 2
            }
        }
        
        //Test request code
        response = await getEvaluationResponse('get_resources_for_location_function.js', context, 'request');
        evaluationResult = JSON.parse(response.evaluationResult);
        expect(evaluationResult.operation).toBe("Query");
        expect(evaluationResult.query.expression).toBe("locationid = :locationid");
        expect(evaluationResult.query.expressionValues[":locationid"].S).toBe(context.arguments.locationid);
        expect(evaluationResult.index).toBe("locationidGSI");

        //Test response code
        response = await getEvaluationResponse('get_resources_for_location_function.js', context, 'response');
        evaluationResult = JSON.parse(response.evaluationResult);
        expect(evaluationResult.length).toBe(Object.keys(context.result.items).length);
        // Check that all items in the results list are present in the response after transformation
        for (i = 0; i < evaluationResult.length; i++) {
            // Check that all result fields are present in the response after transformation
            for (const [key, value] of Object.entries(evaluationResult[i])) {
                expect(evaluationResult[i][key]).toBe(context.result.items[i][key]);
            }
        };
    });

    it('create booking resolver with booking id passed as a parameter', async () => {
        var context = JSON.parse(JSON.stringify(bookingContext));

        //Test request code
        response = await getEvaluationResponse('create_booking_function.js', context, 'request');
        evaluationResult = JSON.parse(response.evaluationResult);
        expect(evaluationResult.operation).toBe("PutItem");
        expect(evaluationResult.key.bookingid.S).toBe(context.arguments.bookingid);
        expect(evaluationResult.attributeValues.resourceid.S).toBe(context.arguments.resourceid);
        expect(evaluationResult.attributeValues.userid.S).toBe(context.identity.sub);
        expect(evaluationResult.attributeValues).toHaveProperty("timestamp");

        //Test response code
        response = await getEvaluationResponse('create_booking_function.js', context, 'response');
        evaluationResult = JSON.parse(response.evaluationResult);
        // Check that all result fields are present in the response after transformation
        for (const [key, value] of Object.entries(evaluationResult)) {
            expect(evaluationResult[key]).toBe(context.result[key]);
        }
    });

    it('create booking resolver without booking id passed as a parameter', async () => {
        var context = JSON.parse(JSON.stringify(bookingContext));
        delete context["arguments"].bookingid;

        //Test request code
        response = await getEvaluationResponse('create_booking_function.js', context, 'request');
        evaluationResult = JSON.parse(response.evaluationResult);
        expect(evaluationResult.operation).toBe("PutItem");
        expect(evaluationResult.key).toHaveProperty("bookingid");
        expect(evaluationResult.attributeValues.resourceid.S).toBe(context.arguments.resourceid);
        expect(evaluationResult.attributeValues.userid.S).toBe(context.identity.sub);
        expect(evaluationResult.attributeValues).toHaveProperty("timestamp");

        //Test response code
        response = await getEvaluationResponse('create_booking_function.js', context, 'response');
        evaluationResult = JSON.parse(response.evaluationResult);
        // Check that all result fields are present in the response after transformation
        for (const [key, value] of Object.entries(evaluationResult)) {
            expect(evaluationResult[key]).toBe(context.result[key]);
        }
    });

    it('get single booking resolver', async () => {
        var context = JSON.parse(JSON.stringify(bookingContext));

        //Test request code
        response = await getEvaluationResponse('get_booking_function.js', context, 'request');
        evaluationResult = JSON.parse(response.evaluationResult);
        expect(evaluationResult.operation).toBe("GetItem");
        expect(evaluationResult.key.bookingid.S).toBe(context.arguments.bookingid);

        //Test response code
        response = await getEvaluationResponse('get_booking_function.js', context, 'response');
        evaluationResult = JSON.parse(response.evaluationResult);
        // Check that all result fields are present in the response after transformation
        for (const [key, value] of Object.entries(evaluationResult)) {
            expect(evaluationResult[key]).toBe(context.result[key]);
        }
    });

    it('get bookings for resource resolver ', async () => {
        context = {
            arguments:
            {
                resourceid: "1234567890",
            },
            result: {
                items: [
                    {
                        bookingid: "0",
                        resourceid: "1234567890",
                        starttimeepochtime: 1672578000,
                        userid: "123456-abcdeefg-7890",
                        timestamp: "2023-01-01T00:00:00.000Z"
                    },
                    {
                        bookingid: "1",
                        resourceid: "1234567890",
                        starttimeepochtime: 1672578000,
                        userid: "abcd-123456-efgh",
                        timestamp: "2023-01-01T00:00:00.000Z"
                    }
                ],
                scannedCount: 2
        }
        };

        //Test request code
        response = await getEvaluationResponse('get_bookings_for_resource_function.js', context, 'request');
        evaluationResult = JSON.parse(response.evaluationResult);
        expect(evaluationResult.operation).toBe("Query");
        expect(evaluationResult.query.expression).toBe("resourceid = :resourceid");
        expect(evaluationResult.query.expressionValues[":resourceid"].S).toBe(context.arguments.resourceid);
        expect(evaluationResult.index).toBe("bookingsByResourceByTimeGSI");

        //Test response code
        response = await getEvaluationResponse('get_bookings_for_resource_function.js', context, 'response');
        evaluationResult = JSON.parse(response.evaluationResult);
        // Check that all items in the results list are present in the response after transformation
        for (i = 0; i < evaluationResult.length; i++) {
            // Check that all result fields are present in the response after transformation
            for (const [key, value] of Object.entries(evaluationResult[i])) {
                expect(evaluationResult[i][key]).toBe(context.result.items[i][key]);
            }
        };
    });

    it('get bookings for user resolver ', async () => {
        context = {
            arguments:
            {
            },
            identity:
            {
                sub: "123456-abcdeefg-7890",
                issuer: "",
                username: "johndoe",
                claims: {},
                sourceIp: [
                    "x.x.x.x"
                ],
                defaultAuthStrategy: "ALLOW"
            },
            result: {
                items: [
                    {
                        bookingid: "0",
                        resourceid: "1234567890",
                        starttimeepochtime: 1672578000,
                        userid: "123456-abcdeefg-7890",
                        timestamp: "2023-01-01T00:00:00.000Z"
                    },
                    {
                        bookingid: "1",
                        resourceid: "1234567890",
                        starttimeepochtime: 1672578000,
                        userid: "abcd-123456-efgh",
                        timestamp: "2023-01-01T00:00:00.000Z"
                    }
                ],
                scannedCount: 2
        }
        };

        //Test request code
        response = await getEvaluationResponse('get_bookings_for_user_function.js', context, 'request');
        evaluationResult = JSON.parse(response.evaluationResult);
        expect(evaluationResult.operation).toBe("Query");
        expect(evaluationResult.query.expression).toBe("userid = :userid");
        expect(evaluationResult.query.expressionValues[":userid"].S).toBe(context.identity.sub);
        expect(evaluationResult.index).toBe("useridGSI");

        //Test response code
        response = await getEvaluationResponse('get_bookings_for_user_function.js', context, 'response');
        evaluationResult = JSON.parse(response.evaluationResult);
        // Check that all items in the results list are present in the response after transformation
        for (i = 0; i < evaluationResult.length; i++) {
            // Check that all result fields are present in the response after transformation
            for (const [key, value] of Object.entries(evaluationResult[i])) {
                expect(evaluationResult[i][key]).toBe(context.result.items[i][key]);
            }
        };
    });

    it('delete booking resolver', async () => {
        var context = JSON.parse(JSON.stringify(bookingContext));

        //Test deletion of the booking user owns
        //Test request code
        response = await getEvaluationResponse('delete_booking_function.js', context, 'request');
        evaluationResult = JSON.parse(response.evaluationResult);
        expect(evaluationResult.operation).toBe("DeleteItem");
        expect(evaluationResult.key.bookingid.S).toBe(context.arguments.bookingid);
        expect(evaluationResult.condition.expression).toBe("userid = :userid");
        expect(evaluationResult.condition.expressionValues[":userid"].S).toBe(context.identity.sub);
        //Test response code
        response = await getEvaluationResponse('delete_booking_function.js', context, 'response');
        evaluationResult = JSON.parse(response.evaluationResult);
        expect(evaluationResult).toBe(context.result.bookingid);

        //Test deletion of the booking by an admin user
        context.identity.claims["cognito:groups"] = ["user", "apiAdmins"];
        //Test request code
        response = await getEvaluationResponse('delete_booking_function.js', context, 'request');
        evaluationResult = JSON.parse(response.evaluationResult);
        expect(evaluationResult.operation).toBe("DeleteItem");
        expect(evaluationResult.key.bookingid.S).toBe(context.arguments.bookingid);
        expect(evaluationResult).not.toHaveProperty("condition");
        //Test response code
        response = await getEvaluationResponse('delete_booking_function.js', context, 'response');
        evaluationResult = JSON.parse(response.evaluationResult);
        expect(evaluationResult).toBe(context.result.bookingid);

    });

})

