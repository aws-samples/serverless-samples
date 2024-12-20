import assert from 'node:assert';
import { testEvent } from './utils/testUtils.mjs';

const apiId = process.env.API_ID;
const region = process.env.AWS_REGION;

if (!apiId || !region) {
    throw new Error('API_ID and AWS_REGION must be set');
}

const hostname = apiId + '.execute-api.' + region + '.amazonaws.com';
const port = '443';
const path = "/dev/"
const method = "POST"
const contentType = "application/json";

const stageOneEvent = JSON.stringify({
    "detail-type": "surgical",
    "source": "scheduling.event",
    "detail": {
        "schedule": {
            "date": "5/15/2024",
            "time": "10:00 AM",
            "location": "Building 6"
        },
        "team": {
            "surgeon": "Jane Someone",
            "assistant": "John Person"
        }
    }

});

describe('Stage 1 tests', () => {

    it('stage-1', async () => {

        const options = {
            hostname: hostname,
            port: port,
            path: path,
            method: method,
            headers: {
                'Content-Type': contentType,
                'Content-Length': stageOneEvent.length,
            },
        };

        try {
            const response = await testEvent(options, stageOneEvent);
            console.log("Stage 1 event response: " + JSON.stringify(response));
            assert.strictEqual(response.FailedEntryCount, 0);
        } catch (err) {
            console.error('Error sending request:', err);
            assert.fail(err);
        }

    });

});