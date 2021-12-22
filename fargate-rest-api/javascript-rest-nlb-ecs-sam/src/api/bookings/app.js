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
    metrics.putMetric("ProcessedBookings", 1, "Count");
    metrics.setProperty("requestId", req.get('requestId'));
    metrics.setProperty('method', req.method);
    metrics.setProperty("routeKey", req.originalUrl);
    next();
});

app.use(AWSXRay.express.openSegment('bookings-service'));

app.get('/health', (req, res) => {
    res.status(200).send('Ok');
});

app.get('/locations/:locationid/resources/:resourceid/bookings', logBusinessMetric, async (req, res, next) => {
    try {
        const { locationid, resourceid } = req.params;

        // Get bookings
        const bookings = await handlers.getBookingsByResource(resourceid);

        res.json(bookings);
    }
    catch (err) {
        next(err)
    }
});

app.get('/users/:userid/bookings', logBusinessMetric, async (req, res, next) => {
    try {
        const { userid } = req.params;

        // Get bookings
        const bookings = await handlers.getBookingsByUser(userid);

        res.json(bookings);
    }
    catch (err) {
        next(err)
    }
});

app.get('/users/:userid/bookings/:bookingid', logBusinessMetric, async (req, res, next) => { 
    try {
        const { userid, bookingid } = req.params;

        // Get resource
        const resource = await handlers.getBooking(bookingid);

        res.json(resource);
    }
    catch (err) {
        next(err)
    }
});

app.put('/users/:userid/bookings/:bookingid?', logBusinessMetric, jsonParser, async (req, res, next) => {
    try {
        const { userid, bookingid } = req.params;
        const { resourceid, starttimeepochtime} = req.body;

        // Create booking
        const booking = await handlers.upsertBooking(bookingid, userid, resourceid, starttimeepochtime);

        res.status(201).json(booking);
    }
    catch (err) {
        next(err)
    }
});

app.delete('/users/:userid/bookings/:bookingid', logBusinessMetric, async (req, res, next) => {
    try {
        const { userid, bookingid } = req.params;

        // Delete location
        await handlers.deleteBooking(bookingid);

        res.status(200).send();
    }
    catch (err) {
        next(err)
    }
});

app.use(AWSXRay.express.closeSegment());

app.use(function (err, req, res, next) {
    const metricsLogger = createMetricsLogger();
    metricsLogger.putMetric("BookingsErrors", 1, "Count");
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