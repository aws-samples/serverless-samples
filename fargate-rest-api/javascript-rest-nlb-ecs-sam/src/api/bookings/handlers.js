// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
const { DynamoDB } = require("@aws-sdk/client-dynamodb");
const { DynamoDBDocument } = require("@aws-sdk/lib-dynamodb");
const uuid = require("uuid");

let ddbClient;
if (process.env.NODE_ENV != 'test') {
    const AWSXRay = require("aws-xray-sdk");
    ddbClient = AWSXRay.captureAWSv3Client(new DynamoDB({}));;
}
else {
    ddbClient = new DynamoDB({});
}

const dynamo = DynamoDBDocument.from(ddbClient);
const tableName = process.env.BOOKINGS_TABLE;

class ItemNotFoundError extends Error {
    constructor(params) {
        super(params);
        this.name = 'ItemNotFoundError';
    }
};

exports.ItemNotFoundError = ItemNotFoundError;

exports.getBookingsByResource = async (resourceID) => {
    const response = await dynamo.query({
        TableName: tableName,
        IndexName: "bookingsByResourceByTimeGSI",
        KeyConditionExpression: "resourceID = :resourceID",
        ExpressionAttributeValues: {
          ':resourceID': resourceID
        }
      });

    return response.Items;
};

exports.getBookingsByUser = async (userID) => {
    const response = await dynamo.query({
        TableName: tableName,
        IndexName: "userIDGSI",
        KeyConditionExpression: "userID = :userID",
        ExpressionAttributeValues: {
          ':userID': userID
        }
      });

    return response.Items;
};

exports.getBooking = async (bookingID) => {
    const response = await dynamo.get({ TableName: tableName, Key: { bookingID }});
    if (!response.Item) {
        throw new ItemNotFoundError('Item not found');
    }
    return response.Item;
};

exports.upsertBooking = async (bookingID, userID, resourceID, starttimeepochtime) => {
    const newitem = {
        bookingID: bookingID || uuid.v1(),
        userID,
        resourceID,
        starttimeepochtime,
        timestamp: new Date().toISOString()
    };

    await dynamo.put({ TableName: tableName, Item: newitem });

    return newitem;
};

exports.deleteBooking = async (bookingID) => {
    return dynamo.delete({ TableName: tableName, Key: { bookingID } });
};