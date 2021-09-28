// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

// Implementation of the API backend for locations

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
const tableName = process.env.LOCATIONS_TABLE;

exports.handler = metricScope(metrics => async (event, context) => {
  let body;
  let statusCode = 200;
  const headers = {
    "Content-Type": "application/json"
  };

  // Initialize putting common business metrics using EMF
  var metricPayload = {}
  metrics.putDimensions({ Service: "Locations" });
  metrics.putMetric("ProcessedLocations", 1, "Count");
  metrics.setProperty("requestId", event.requestContext.requestId);
  metrics.setProperty("routeKey", event.routeKey);

  try {
    switch (event.routeKey) {
      // Get all locations
      case "GET /locations":
        // add business metrics for the route
        metricPayload.operation = "GET";
        // get data from the database
        body = await dynamo.scan({ TableName: tableName });
        break;
      // Location CRUD operations
      case "GET /locations/{locationid}":
        // add business metrics for the route
        metricPayload.operation = "GET";
        metricPayload.locationid = event.pathParameters.locationid;
        // get data from the database
        body = await dynamo
          .get({
            TableName: tableName,
            Key: {
              locationid: event.pathParameters.locationid
            }
          });
        break;
      case "DELETE /locations/{locationid}":
        // add business metrics for the route
        metricPayload.operation = "DELETE";
        metricPayload.locationid = event.pathParameters.locationid;
        // delete item in the database
        await dynamo
          .delete({
            TableName: tableName,
            Key: {
              locationid: event.pathParameters.locationid
            }
          });
        body = {};
        break;
      case "PUT /locations":
        let requestJSON = JSON.parse(event.body);
        // generate unique id if it isn't present in the request
        let id = requestJSON.locationid || uuid.v1();
        let newitem = {
          locationid: id,
          timestamp: new Date().toISOString(),
          description: requestJSON.description,
          imageUrl: requestJSON.imageUrl,
          name: requestJSON.name
        }
        // add business metrics for the route
        metricPayload.operation = "PUT";
        metricPayload.locationid = id;
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
