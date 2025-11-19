# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from strands import Agent
import asyncio
import json

app = FastAPI()

bedrock_agent = Agent(
    model="us.amazon.nova-lite-v1:0",
    system_prompt="You are a helpful AI assistant.",
)

# Based on https://aws.amazon.com/blogs/opensource/introducing-strands-agents-1-0-production-ready-multi-agent-orchestration-made-simple/
async def stream_response(request: str): 
    async for event in bedrock_agent.stream_async(request): 
        if "data" in event: 
            yield event['data'] 

@app.post("/")
async def index(request: Request):
    # Get the JSON payload from the POST body
    body = await request.body()
    payload = json.loads(body.decode('utf-8'))
    request_param = payload.get("request")
    
    return StreamingResponse(stream_response(request_param), media_type="text/html")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}