// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { BedrockRuntimeClient, InvokeModelWithResponseStreamCommand } from "@aws-sdk/client-bedrock-runtime";

const MODEL_ID = 'us.amazon.nova-lite-v1:0';
const bedrockClient = new BedrockRuntimeClient({ region: process.env.BEDROCK_REGION || 'us-west-1' });

export const handler = awslambda.streamifyResponse(
    async (event, responseStream) => {
        responseStream.write('{"statusCode": 200}');
        responseStream.write("\x00".repeat(8));

        try {
            // Extract message from event
            const message = event.body ? JSON.parse(event.body).message : event.message;

            // Prepare request for Nova Lite model
            const requestBody = {
                messages: [
                    {
                        role: "user",
                        content: [
                            {
                                text: message
                            }
                        ]
                    }
                ],
                inferenceConfig: {
                    max_new_tokens: 4096,
                    temperature: 0.7
                }
            };

            const command = new InvokeModelWithResponseStreamCommand({
                modelId: MODEL_ID,
                contentType: "application/json",
                accept: "application/json",
                body: JSON.stringify(requestBody)
            });

            const response = await bedrockClient.send(command);

            // Stream response chunks for Nova Lite
            for await (const chunk of response.body) {
                const chunkData = JSON.parse(new TextDecoder().decode(chunk.chunk?.bytes));

                if (chunkData.contentBlockDelta?.delta?.text) {
                    responseStream.write(chunkData.contentBlockDelta.delta.text);
                }
            }
        } catch (error) {
            responseStream.write(`Error: ${error.message}`);
        } finally {
            responseStream.end();
        }
    }
);
