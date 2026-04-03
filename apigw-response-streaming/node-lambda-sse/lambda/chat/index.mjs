import {
  BedrockRuntimeClient,
  ConverseStreamCommand,
} from "@aws-sdk/client-bedrock-runtime";

const client = new BedrockRuntimeClient({ region: "eu-west-2" });

export const handler = awslambda.streamifyResponse(
  async (event, responseStream, _context) => {
    let body;
    try {
      body = JSON.parse(event.body);
    } catch {
      responseStream = awslambda.HttpResponseStream.from(responseStream, {
        statusCode: 400,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
        },
      });
      responseStream.write(JSON.stringify({ error: "Invalid JSON in request body" }));
      responseStream.end();
      return;
    }

    if (!body.messages || !Array.isArray(body.messages) || body.messages.length === 0) {
      responseStream = awslambda.HttpResponseStream.from(responseStream, {
        statusCode: 400,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
        },
      });
      responseStream.write(
        JSON.stringify({ error: "Request body must contain a non-empty 'messages' array" })
      );
      responseStream.end();
      return;
    }

    responseStream = awslambda.HttpResponseStream.from(responseStream, {
      statusCode: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "Access-Control-Allow-Origin": "*",
      },
    });

    try {
      const command = new ConverseStreamCommand({
        modelId: "amazon.nova-lite-v1:0",
        messages: body.messages.map((msg) => ({
          role: msg.role,
          content: [{ text: msg.content }],
        })),
        inferenceConfig: { maxTokens: 4096 },
      });

      const response = await client.send(command);

      for await (const event of response.stream) {
        if (event.contentBlockDelta?.delta?.text) {
          const chunk = event.contentBlockDelta.delta.text;
          responseStream.write(`data: ${JSON.stringify({ text: chunk })}\n\n`);
        }
      }
    } catch (error) {
      responseStream.write(
        `data: ${JSON.stringify({ error: error.message })}\n\n`
      );
    }

    responseStream.write("data: [DONE]\n\n");
    responseStream.end();
  }
);
