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
const tableName = process.env.RESOURCES_TABLE;

class ItemNotFoundError extends Error {
    constructor(params) {
        super(params);
        this.name = 'ItemNotFoundError';
    }
};

exports.ItemNotFoundError = ItemNotFoundError;

exports.getResources = async (locationid) => {
    const response = await dynamo.query({
        TableName: tableName,
        IndexName: "locationidGSI",
        KeyConditionExpression: "locationid = :locationid",
        ExpressionAttributeValues: {
            ':locationid': locationid
        }
    });

    return response.Items;
};

exports.getResource = async (resourceid) => {
    const response = await dynamo.get({ TableName: tableName, Key: { resourceid }});
    if (!response.Item) {
        throw new ItemNotFoundError('Item not found');
    }
    return response.Item;
};

exports.upsertResource = async (resourceid, locationid, type, description, name) => {
    const newitem = {
        resourceid: resourceid || uuid.v1(),
        locationid,
        timestamp: new Date().toISOString(),
        description,
        type,
        name
    };

    await dynamo.put({ TableName: tableName, Item: newitem });

    return newitem;
};

exports.deleteResource = async (resourceid) => {
    return dynamo.delete({ TableName: tableName, Key: { resourceid } });
};