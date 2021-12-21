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
const tableName = process.env.LOCATIONS_TABLE;

class ItemNotFoundError extends Error {
    constructor(params) {
        super(params);
        this.name = 'ItemNotFoundError';
    }
};

exports.ItemNotFoundError = ItemNotFoundError;

exports.getLocations = async () => {
    const response = await dynamo.scan({ TableName: tableName });

    return response.Items;
};

exports.getLocation = async (locationid) => {
    const response = await dynamo.get({ TableName: tableName, Key: { locationid }});
    if (!response.Item) {
        throw new ItemNotFoundError('Item not found');
    }
    return response.Item;
};

exports.upsertLocation = async (locationid, imageUrl, description, name) => {  
    const newitem = {
      locationid: locationid || uuid.v1(),
      timestamp: new Date().toISOString(),
      description,
      imageUrl,
      name
    };
  
    await dynamo.put({ TableName: tableName, Item: newitem });

    return newitem;
};

exports.deleteLocation = async (locationid) => {  
    return dynamo.delete({ TableName: tableName, Key: { locationid } });
};