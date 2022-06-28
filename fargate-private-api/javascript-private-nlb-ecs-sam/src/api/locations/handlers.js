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

const PAGE_SIZE = 20;

class ItemNotFoundError extends Error {
    constructor(params) {
        super(params);
        this.name = 'ItemNotFoundError';
    }
};

exports.ItemNotFoundError = ItemNotFoundError;

exports.getLocations = async (lastLocationID) => {
    const params = { Limit: PAGE_SIZE, TableName: tableName };
    
    if (lastLocationID) {
        params.ExclusiveStartKey = {
            locationID: lastLocationID
        }
    }

    // Note: Performing scans is typically not recommended for production use. 
    // A Scan operation always scans the entire table or secondary index. Consider using filters or the Query operation instead.
    // (See more: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-query-scan.html#bp-query-scan-performance)
    const response = await dynamo.scan(params);

    return { items: response.Items, lastLocationID: response.LastEvaluatedKey?.locationID };
};

exports.getLocation = async (locationID) => {
    const response = await dynamo.get({ TableName: tableName, Key: { locationID }});
    if (!response.Item) {
        throw new ItemNotFoundError('Item not found');
    }
    return response.Item;
};

exports.upsertLocation = async (locationID, imageUrl, description, name) => {  
    const newitem = {
      locationID: locationID || uuid.v1(),
      timestamp: new Date().toISOString(),
      description,
      imageUrl,
      name
    };
  
    await dynamo.put({ TableName: tableName, Item: newitem });

    return newitem;
};

exports.deleteLocation = async (locationID) => {  
    return dynamo.delete({ TableName: tableName, Key: { locationID } });
};