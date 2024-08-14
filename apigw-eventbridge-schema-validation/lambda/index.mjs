// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { SchemasClient, ExportSchemaCommand } from "@aws-sdk/client-schemas";

import Ajv from 'ajv-draft-04';
const ajv = new Ajv();

import { APIGatewayClient, UpdateModelCommand, CreateDeploymentCommand } from "@aws-sdk/client-api-gateway";
const apiClient = new APIGatewayClient();

const schemaName = process.env.SchemaName;
const apiId = process.env.ApiId;
const apiModelName = process.env.ApiModelName;
const schemaRegistry = process.env.SchemaRegistry;

// Deploys API to specific stage.  For instance, after updating model, deploy changes to dev stage
async function deployApiToStage(restApiId, stageName) {
    const deploymentParams = {
        restApiId,
        stageName,
        stageDescription: `Deployed to ${stageName} stage`,
        description: `Deployment to ${stageName} stage`,
    };

    try {
        const createDeploymentCommand = new CreateDeploymentCommand(deploymentParams);
        const deployment = await apiClient.send(createDeploymentCommand);

        console.log(`API deployed to ${stageName} stage. Deployment ID: ${deployment.Id}`);
        return deployment.Id;
    } catch (error) {
        console.error(`Error deploying API to ${stageName} stage:`, error);
        throw error;
    }
}


// uploads modified schema to API Gateway and replaces existing model
async function uploadSchema(schema, restApiId, modelName) {

    console.log("updating API " + restApiId + " model " + modelName);
    const updateModelParams = {
        restApiId,
        modelName,
        patchOperations: [
            {
                op: "replace",
                path: "/schema",
                value: JSON.stringify(schema),
            },
        ],
    };

    try {
        const updateModelCommand = new UpdateModelCommand(updateModelParams);
        const updatedModel = await apiClient.send(updateModelCommand);

        console.log("Updated model:", updatedModel);
        // enable request validator on body

        return {
            statusCode: 200,
            body: JSON.stringify({ message: "Model updated successfully" }),
        };
    } catch (error) {
        console.error("Error updating model:", error);
        return {
            statusCode: 500,
            body: JSON.stringify({ error: error.message }),
        };
    }

}

// removes metadata added by AWS Eventbridge so this is not required by the API GW model
function modifySchema(schemaJson) {
    const schema = JSON.parse(schemaJson);

    // remove the x-amazon-events-detail-type property from the schema
    delete schema['x-amazon-events-detail-type'];
    delete schema['x-amazon-events-source'];

    // delete properties added by EventBridge so they aren't required by producers
    // you can modify any of these as needed
    delete schema.properties.account;
    delete schema.properties.region;
    delete schema.properties.id;
    delete schema.properties.version;
    delete schema.properties.resources;
    delete schema.properties.time;

    // remove required fields: account, region, id, version, resources, time from the schema
    schema.required = schema.required.filter(item => item !== 'account' && item !== 'region' && item !== 'id' && item !== 'version' && item !== 'resources' && item !== 'time');

    // Validate the modified schema
    console.log("validating schema...")
    const validate = ajv.compile(schema);

    console.log("\n ** new schema: \n" + JSON.stringify(schema));
    return schema;
}

// Downloads latest schema version from the registry
async function downloadSchema(schemaRegistry, schemaName) {
    const config = { }
    const client = new SchemasClient(config);
    const input = { // ExportSchemaRequest
        RegistryName: schemaRegistry, // required
        SchemaName: schemaName, // required
        //SchemaVersion: "STRING_VALUE",
        Type: "JSONSchemaDraft4" // required
    };
    const command = new ExportSchemaCommand(input);
    const response = await client.send(command);
    return response.Content;
}

// Lambda Handler
export const handler = async (event) => {

    console.log('Event received:', JSON.stringify(event, null, 2));

    // check required variables
    if (!apiId || !schemaName || !apiModelName || !schemaRegistry) {
        const errorMsg = 'Missing environment variables.  apiId, apiModelName, schemaRegistry, schemaName and validSchemaNames are required.'
        console.error(errorMsg);
        return {
            statusCode: 400,
            body: errorMsg
        };
    }

    // download, modify and upload the schema
    try {
        const existingSchema = await downloadSchema(schemaRegistry, schemaName)
        const modifiedSchema = modifySchema(existingSchema);
        await uploadSchema(modifiedSchema, apiId, apiModelName);
        await deployApiToStage(apiId, 'dev');
    }
    catch(error) {
            console.error("error encountered while downloading or uploading schema. Details:" + error);
            return {
                statusCode: 400,
                body: error
             };
    }

    return {
        statusCode: 200,
        body: 'Schema ' + schemaName + ' updated successfully.'
    };
};
