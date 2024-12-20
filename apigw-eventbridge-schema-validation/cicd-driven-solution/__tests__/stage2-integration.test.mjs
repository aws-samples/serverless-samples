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

const stageTwoEvent = JSON.stringify({
    "detail-type": "surgical",
    "source": "scheduling.event",
    "detail": {
        "schedule": {
            "date": "5/15/2024",
            "time": "10:00 AM",
            "location": "Building 6",
            "duration": "120 mins"
        },
        "medication": "Oxycodone 5 mg every 4 hours.",
        "team": {
            "surgeon": "Jane Someone",
            "assistant": "John Person"
        },
        "procedure": {
            "type": "Anterior Cruciate Ligament",
            "location": "left knee"
        }
    }
});

describe('Stage 2 tests', () => {

    it('stage-2', async () => {

        const options = {
            hostname: hostname,
            port: port,
            path: path,
            method: method,
            headers: {
                'Content-Type': contentType,
                'Content-Length': stageTwoEvent.length,
            },
        };

        try {
            const response = await testEvent(options, stageTwoEvent);
            console.log("Stage 2 event response: " + JSON.stringify(response));
            assert.strictEqual(response.FailedEntryCount, 0);
        } catch (err) {
            console.error('Error sending request:', err);
            assert.fail(err);
        }

    });

});