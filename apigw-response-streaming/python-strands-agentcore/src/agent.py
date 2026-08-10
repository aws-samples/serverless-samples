# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from strands import Agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp

strands_agent = Agent(
    model="us.amazon.nova-lite-v1:0",
    system_prompt="You are a helpful AI assistant.",    
)
app = BedrockAgentCoreApp()

@app.entrypoint
async def invoke(payload):
    request = payload.get("prompt", "Hello")
    async for event in strands_agent.stream_async(request):
        if "data" in event: 
            yield event['data']

if __name__ == "__main__":
    app.run()