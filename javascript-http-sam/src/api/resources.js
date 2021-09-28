// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

// Implementation of the API backend for resources

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
const tableName = process.env.RESOURCES_TABLE;

exports.handler = metricScope(metrics => async (event, context) => {
  let body;
  let statusCode = 200;
  const headers = {
    "Content-Type": "application/json"
  };

  // Initialize putting common business metrics using EMF
  var metricPayload = {}
  metrics.putDimensions({ Service: "Resources" });
  metrics.putMetric("ProcessedResources", 1, "Count");
  metrics.setProperty("requestId", event.requestContext.requestId);
  metrics.setProperty("routeKey", event.routeKey);

  try {
    switch (event.routeKey) {
      // Get all resources
      case "GET /locations/{locationid}/resources":
        // add business metrics for the route
        metricPayload.operation = "GET";
        metricPayload.locationid = event.pathParameters.locationid;
        // get data from the database
        body = await dynamo.query({
          TableName: tableName,
          IndexName: "locationidGSI",
          KeyConditionExpression: "locationid = :locationid",
          ExpressionAttributeValues: {
            ':locationid': event.pathParameters.locationid
          }
        });
        break;
      // Resource CRUD operations
      case "GET /locations/{locationid}/resources/{resourceid}":
        // add business metrics for the route
        metricPayload.operation = "GET";
        metricPayload.resourceid = event.pathParameters.resourceid;
        metricPayload.locationid = event.pathParameters.locationid;
        // get data from the database
        body = await dynamo
          .get({
            TableName: tableName,
            Key: {
              resourceid: event.pathParameters.resourceid
            }
          });
        break;
      case "DELETE /locations/{locationid}/resources/{resourceid}":
        // add business metrics for the route
        metricPayload.operation = "DELETE";
        metricPayload.resourceid = event.pathParameters.resourceid;
        metricPayload.locationid = event.pathParameters.locationid;
        // delete item in the database
        await dynamo
          .delete({
            TableName: tableName,
            Key: {
              resourceid: event.pathParameters.resourceid
            }
          });
        body = {};
        break;
      case "PUT /locations/{locationid}/resources":
        let requestJSON = JSON.parse(event.body);
        // generate unique id if it isn't present in the request
        let id = requestJSON.resourceid || uuid.v1();
        let newitem = {
          resourceid: id,
          locationid: event.pathParameters.locationid,
          timestamp: new Date().toISOString(),
          description: requestJSON.description,
          name: requestJSON.name,
          type: requestJSON.type
        }
        // add business metrics for the route
        metricPayload.operation = "PUT";
        metricPayload.resourceid = id;
        metricPayload.locationid = event.pathParameters.locationid;
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
