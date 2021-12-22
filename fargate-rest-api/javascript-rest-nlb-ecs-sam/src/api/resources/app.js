// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

// Implementation of the API backend for locations

const handlers = require('./handlers');
const express = require('express');
const bodyParser = require('body-parser');
const { metricScope, createMetricsLogger } = require("aws-embedded-metrics");
const AWSXRay = require("aws-xray-sdk");

// App
const app = express();
const jsonParser = bodyParser.json()

const logBusinessMetric = metricScope(metrics => function (req, res, next) {
    metrics.putMetric("ProcessedResources", 1, "Count");
    metrics.setProperty("requestId", req.get('requestId'));
    metrics.setProperty('method', req.method);
    metrics.setProperty("routeKey", req.originalUrl);
    next();
});

app.use(AWSXRay.express.openSegment('resources-service'));

app.get('/health', (req, res) => {
    res.status(200).send('Ok');
});

app.get('/locations/:locationid/resources', logBusinessMetric, async (req, res, next) => {
    try {
        const { locationid } = req.params;

        // Get resources
        const resources = await handlers.getResources(locationid);

        res.json(resources);
    }
    catch (err) {
        next(err)
    }
});

app.get('/locations/:locationid/resources/:resourceid', logBusinessMetric, async (req, res, next) => { 
    try {
        const { locationid, resourceid } = req.params;

        // Get resource
        const resource = await handlers.getResource(resourceid);

        res.json(resource);
    }
    catch (err) {
        next(err)
    }
});

app.put('/locations/:locationid/resources/:resourceid?', logBusinessMetric, jsonParser, async (req, res, next) => {
    try {
        const { locationid, resourceid } = req.params;
        const { type, description, name } = req.body;

        // Create resource
        const resource = await handlers.upsertResource(resourceid, locationid, type, description, name);

        res.status(201).json(resource);
    }
    catch (err) {
        next(err)
    }
});

app.delete('/locations/:locationid/resources/:resourceid', logBusinessMetric, async (req, res, next) => {
    try {
        const { resourceid } = req.params;

        // Delete resource
        await handlers.deleteResource(resourceid);

        res.status(200).send();
    }
    catch (err) {
        next(err)
    }
});

app.use(AWSXRay.express.closeSegment());

app.use(function (err, req, res, next) {
    const metricsLogger = createMetricsLogger();
    metricsLogger.putMetric("ResourcesErrors", 1, "Count");
    metricsLogger.setProperty("requestId", req.get('requestId'));
    metricsLogger.setProperty('method', req.method);
    metricsLogger.setProperty("routeKey", req.originalUrl);
    metricsLogger.flush();

    console.error(err.stack)
    if (err instanceof handlers.ItemNotFoundError) {
        res.status(404).send(err.message);
    }
    else {
        res.status(500).send('Something broke!')
    }
  })

exports.app = app;