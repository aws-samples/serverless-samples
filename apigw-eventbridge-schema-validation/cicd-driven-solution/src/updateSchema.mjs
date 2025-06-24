// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { SchemasClient, ExportSchemaCommand, ListSchemaVersionsCommand } from "@aws-sdk/client-schemas";

import Ajv from 'ajv-draft-04';
const ajv = new Ajv();

import { APIGatewayClient, UpdateModelCommand, CreateDeploymentCommand, GetModelCommand } from "@aws-sdk/client-api-gateway";
const apiClient = new APIGatewayClient();

const schemaName = process.env.SchemaName;
const apiId = process.env.ApiId;
const apiModelName = process.env.ApiModelName;
const schemaRegistry = process.env.SchemaRegistry;
let currentSchemaVersion = process.env.CurrentSchemaVersion;
const rollback = process.env.Rollback;


/**
 * Retrieves the list of schema versions from the EventBridge Schema Registry
 * @param registryName
 * @param schemaName
 * @returns {Promise<*>}
 */
async function getSchemaVersions(registryName, schemaName) {
    const client = new SchemasClient();
    const versions = [];
    let nextToken = null;

    try {
        do {
            const input = {
                RegistryName: registryName,
                SchemaName: schemaName,
                NextToken: nextToken
            };

            const command = new ListSchemaVersionsCommand(input);
            const response = await client.send(command);

            if (response.SchemaVersions) {
                versions.push(...response.SchemaVersions);
            }

            nextToken = response.NextToken;
        } while (nextToken);

        // extract schema versions from JSON and return an ordered list
        return extractSchemaVersions(versions).sort((a, b) => a - b);

    } catch (error) {
        console.error('Error fetching schema versions:', error);
        throw error;
    }
}

/**
 * parses the response from EventBridge Schema Registry to extract schema versions
 * @param jsonString
 * @returns {*}
 */
function extractSchemaVersions(jsonString) {
    try {
        // Parse JSON string to array if input is a string
        const schemaArray = typeof jsonString === 'string'
            ? JSON.parse(jsonString)
            : jsonString;

        return schemaArray
            .map(schema => parseInt(schema.SchemaVersion, 10))
            .filter(version => !isNaN(version));
    } catch (error) {
        console.error('Error processing schema versions:', error);
        throw error;
    }
}

/**
 * Deploys the model changes to an API Gateway stage
 * @param restApiId
 * @param stageName
 * @returns {Promise<*>}
 */
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

        console.log(`API deployed to ${stageName} stage. Deployment ID: ` + JSON.stringify(deployment.id));
        return deployment.id;
    } catch (error) {
        console.error(`Error deploying API to ${stageName} stage:`, error);
        throw error;
    }
}


/**
 * Updates the API Gateway model with latest schema
 * @param schema
 * @param restApiId
 * @param modelName
 * @returns {Promise<{statusCode: number, body: string}>}
 */
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

/**
 * Modifies the schema to remove properties that are only for EventBridge and include version as id
 * @param schemaJson
 * @param schemaVersion
 * @returns {any}
 */
function modifySchema(schemaJson, schemaVersion) {
    const schema = JSON.parse(schemaJson);

    // Use description field to keep track of what schema version this came from
    schema.description = schemaVersion.toString();

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

/**
 * Downloads schema from the registry
 * @param schemaRegistry
 * @param schemaName
 * @param schemaVersion
 * @returns {Promise<*>}
 */
async function downloadSchema(schemaRegistry, schemaName, schemaVersion) {
    const config = { }
    const client = new SchemasClient(config);
    const input = { // ExportSchemaRequest
        RegistryName: schemaRegistry, // required
        SchemaName: schemaName, // required
        SchemaVersion: schemaVersion.toString(), // Convert to string in case number is passed
        Type: "JSONSchemaDraft4" // required
    };

    try {
        const command = new ExportSchemaCommand(input);
        const response = await client.send(command);
        return response.Content;
    } catch (error) {
        console.error('Error downloading schema:', error);
        throw error;
    }
}


/**
 * Downloads latest schema version from the registry and updates API Gateway model
 * @param latestVersion
 * @returns {Promise<void>}
 */
async function downloadAndUpdateSchema(latestVersion) {
    const schema = await downloadSchema(schemaRegistry, schemaName, latestVersion);
    const modifiedSchema = modifySchema(schema, latestVersion);
    await uploadSchema(modifiedSchema, apiId, apiModelName);
    await deployApiToStage(apiId, 'dev');
}

/**
 * Gets the current schema version from the API Gateway model
 * @param apiId - API Gateway ID
 * @param modelName -  API Gateway model name
 * @returns {Promise<*>}
 */
async function getCurrentSchemaVersionFromApiModel(apiId, modelName) {

    const params = {
        restApiId: apiId,
        modelName: modelName,
        flatten: true // This flattens model schema if it has references
    };

    let versionInModel = "0";

    try {
        // Get the model
        console.log("retrieving model from API Gateway.  ApiId:" + apiId + "  modelName:" +modelName);
        const command = new GetModelCommand(params);
        const response = await apiClient.send(command);

        // Parse the schema from the response
        const modelSchema = JSON.parse(response.schema);

        // Extract the version stored in the description field
        versionInModel = modelSchema.description;
        console.log('Retrieved schema model description field value from API Gateway:', versionInModel);

        // if modelId is null or not a number greater than zero, then set it to zero
        if (versionInModel == null || isNaN(versionInModel) || versionInModel < 1) {
            console.log('Model ID not found in schema. Setting to zero.');
            versionInModel = 0;
        }

    } catch (error) {
        console.error('Error downloading or parsing model:', error);
        versionInModel = 0;
    }

    return versionInModel;
}

/**
 * Downloads previous schema version and applies it to API Gateway model
 * @param schemaVersions list of schema versions from EventBridge Schema Registry
 * @returns {Promise<void>}
 */
async function rollbackSchemaPreviousVersion(schemaVersions) {
    console.log("rollback detected");
    let schemaVersionToDownload = currentSchemaVersion - 1;
    // if schemaVersionToDownload is not in the list of schemaVersions, exit
    if (schemaVersionToDownload < 1 || !schemaVersions.includes(schemaVersionToDownload)) {
        console.error("schema version to download:" + schemaVersionToDownload + " is not in the list of schema versions");
        process.exit(1);
    }
    console.log("rolling back to previous version.  setting current schema version to:" + schemaVersionToDownload);
    await downloadAndUpdateSchema(schemaVersionToDownload);
    currentSchemaVersion = schemaVersionToDownload;
}

/**
 * Updates the schema to the latest version if the latest version is greater than the current version
 * @param schemaVersionToDownload
 * @returns {Promise<void>}
 */
async function updateSchemaToLatest(schemaVersionToDownload) {
    if (Number(schemaVersionToDownload) > Number(currentSchemaVersion)) {
        console.log("Updating schema to latest.  Current schema version in EventBridge registry:" + schemaVersionToDownload);
        await downloadAndUpdateSchema(schemaVersionToDownload);
        console.log("schema updated successfully to: " + schemaVersionToDownload);
        currentSchemaVersion = schemaVersionToDownload;
    } else {
        console.log("no new schema version detected.");
    }
}


    // If a new schema version exists, download and update.  If rollback is true, revert schema to previous version
    try {
        // check required variables
        console.log("api_id:" + apiId + "  model:" + apiModelName + "  schemaName:" + schemaName + "  registry:" + schemaRegistry);
        if (!apiId || !schemaName || !apiModelName || !schemaRegistry) {
            const errorMsg = 'Missing environment variables.  apiId, apiModelName, schemaRegistry and schemaName are required.'
            console.error(errorMsg);
            process.exit(1);
        }

        // get the currently applied schema version for the model in API Gateway.  If none exist, current version is set to zero
        currentSchemaVersion = await getCurrentSchemaVersionFromApiModel(apiId, apiModelName);
        console.log("current schema version:" + currentSchemaVersion);

        // get the available versions of the schema from EventBridge
        const schemaVersions = await getSchemaVersions(schemaRegistry, schemaName);
        console.log("schema versions:" + JSON.stringify(schemaVersions));

        // if no versions of this schema exist, exit.
        if (!schemaVersions || schemaVersions.length === 0) {
            console.error("no schema versions found");
            process.exit(1);
        }

        // retrieve the last value in the schemaVersions list and store as the schemaVersion
        const schemaVersionToDownload = schemaVersions[schemaVersions.length - 1];

        // if rollback is not null and set to true, decrement version to download from current
        if(rollback != null && rollback.toLowerCase() === "true") {
            await rollbackSchemaPreviousVersion(schemaVersions);
        }
        else {
            await updateSchemaToLatest(schemaVersionToDownload);
        }

    }
    catch(error) {
            console.error("error encountered while downloading or uploading schema. Details:" + error);
    }


