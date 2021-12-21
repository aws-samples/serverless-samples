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

exports.getBookingsByResource = async (resourceid) => {
    const response = await dynamo.query({
        TableName: tableName,
        IndexName: "bookingsByResourceByTimeGSI",
        KeyConditionExpression: "resourceid = :resourceid",
        ExpressionAttributeValues: {
          ':resourceid': resourceid
        }
      });

    return response.Items;
};

exports.getBookingsByUser = async (userid) => {
    const response = await dynamo.query({
        TableName: tableName,
        IndexName: "useridGSI",
        KeyConditionExpression: "userid = :userid",
        ExpressionAttributeValues: {
          ':userid': userid
        }
      });

    return response.Items;
};

exports.getBooking = async (bookingid) => {
    const response = await dynamo.get({ TableName: tableName, Key: { bookingid }});
    if (!response.Item) {
        throw new ItemNotFoundError('Item not found');
    }
    return response.Item;
};

exports.upsertBooking = async (bookingid, userid, resourceid, starttimeepochtime) => {
    const newitem = {
        bookingid: bookingid || uuid.v1(),
        userid,
        resourceid,
        starttimeepochtime,
        timestamp: new Date().toISOString()
    };

    await dynamo.put({ TableName: tableName, Item: newitem });

    return newitem;
};

exports.deleteBooking = async (bookingid) => {
    return dynamo.delete({ TableName: tableName, Key: { bookingid } });
};