import https from 'node:https';
import assert from 'node:assert';

export async function testEvent(options, requestData) {
    return new Promise((resolve, reject) => {
        const req = https.request(options, (res) => {
            let responseData = '';
            res.on('data', (chunk) => {
                responseData += chunk;
            });

            res.on('end', () => {
                try {
                    const parsedResponse = JSON.parse(responseData);
                    console.log("response: " + responseData);
                    assert.strictEqual(parsedResponse.FailedEntryCount, 0);
                    resolve(parsedResponse);
                } catch (error) {
                    reject(error);
                }
            });
        });

        req.on('error', (error) => {
            reject(error);
        });

        if (requestData) {
            req.write(requestData);
        }
        req.end();
    });
}
