// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

// Implementation of the API backend for bookings

const { DynamoDB } = require("@aws-sdk/client-dynamodb");
const { DynamoDBDocument } = require("@aws-sdk/lib-dynamodb");
const { metricScope } = require("aws-embedded-metrics");
const uuid = require("uuid");
ddbClient = new DynamoDB({});

// Check if code is running in SAM Local environment and disable X-Ray in such case
if (!process.env.AWS_SAM_LOCAL) {
  const AWSXRay = require("aws-xray-sdk-core");
  ddbClient = AWSXRay.captureAWSv3Client(new DynamoDB({}));
}

const dynamo = DynamoDBDocument.from(ddbClient);
const tableName = process.env.BOOKINGS_TABLE;

exports.handler = metricScope(metrics => async (event, context) => {
  let body;
  let statusCode = 200;
  const headers = {
    "Content-Type": "application/json"
  };

  // Initialize putting common business metrics using EMF
  var metricPayload = {}
  metrics.putDimensions({ Service: "Bookings" });
  metrics.putMetric("ProcessedBookings", 1, "Count");
  metrics.setProperty("requestId", event.requestContext.requestId);
  metrics.setProperty("routeKey", event.routeKey);

  try {
    switch (event.routeKey) {
      // Get bookings for resource
      case "GET /locations/{locationid}/resources/{resourceid}/bookings":
        // add business metrics for the route
        metricPayload.operation = "GET";
        metricPayload.locationid = event.pathParameters.locationid;
        metricPayload.resourceid = event.pathParameters.resourceid;
        // get data from the database
        body = await dynamo.query({
          TableName: tableName,
          IndexName: "bookingsByResourceByTimeGSI",
          KeyConditionExpression: "resourceid = :resourceid",
          ExpressionAttributeValues: {
            ':resourceid': event.pathParameters.resourceid
          }
        });
        break;
      // Get bookings for user
      case "GET /users/{userid}/bookings":
        // add business metrics for the route
        metricPayload.operation = "GET";
        metricPayload.userid = event.pathParameters.userid;
        // get data from the database
        body = await dynamo.query({
          TableName: tableName,
          IndexName: "useridGSI",
          KeyConditionExpression: "userid = :userid",
          ExpressionAttributeValues: {
            ':userid': event.pathParameters.userid
          }
        });
        break;
      // Booking CRUD operations
      case "GET /users/{userid}/bookings/{bookingid}":
        // add business metrics for the route  
        metricPayload.operation = "GET";
        metricPayload.bookingid = event.pathParameters.bookingid;
        metricPayload.userid = event.pathParameters.userid;
        // get data from the database
        body = await dynamo
          .get({
            TableName: tableName,
            Key: {
              bookingid: event.pathParameters.bookingid
            }
          });
        break;
      case "DELETE /users/{userid}/bookings/{bookingid}":
        // add business metrics for the route
        metricPayload.operation = "DELETE";
        metricPayload.bookingid = event.pathParameters.bookingid;
        metricPayload.userid = event.pathParameters.userid;
        // delete item in the database
        await dynamo
          .delete({
            TableName: tableName,
            Key: {
              bookingid: event.pathParameters.bookingid
            }
          });
        body = {};
        break;
      case "PUT /users/{userid}/bookings":
        let requestJSON = JSON.parse(event.body);
        // generate unique id if it isn't present in the request
        let id = requestJSON.bookingid || uuid.v1();
        let newitem = {
          bookingid: id,
          userid: event.pathParameters.userid,
          resourceid: requestJSON.resourceid,
          starttimeepochtime: requestJSON.starttimeepochtime,
          timestamp: new Date().toISOString()
        }
        // add business metrics for the route
        metricPayload.operation = "PUT";
        metricPayload.bookingid = id;
        metricPayload.userid = event.pathParameters.userid;
        // update the database
        await dynamo
          .put({
            TableName: tableName,
            Item: newitem
          });
        body = newitem;
        break;
      default:
        throw new Error(`Unsupported route: "${event.routeKey}"`);
    }
  } catch (err) {
    statusCode = 400;
    body = err.message;
    console.error(err.message);
  } finally {
    // Add route specific business metrics
    metrics.setProperty("Payload", metricPayload);
    body = JSON.stringify(body);
  }

  return {
    statusCode,
    body,
    headers
  };
});
