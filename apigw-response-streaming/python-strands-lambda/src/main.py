# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from strands import Agent
import asyncio
import json

app = FastAPI()

strands_agent = Agent(
    model="us.amazon.nova-lite-v1:0",
    system_prompt="You are a helpful AI assistant.",
)

# Based on https://aws.amazon.com/blogs/opensource/introducing-strands-agents-1-0-production-ready-multi-agent-orchestration-made-simple/
async def streamer(request: str): 
    async for event in strands_agent.stream_async(request): 
        if "data" in event: 
            yield event['data'] 

@app.get("/{request_path:path}")
async def catch_all(request: Request, request_path: str):
    # Catch-all route to handle all GET requests
    return

@app.post("/{request_path:path}")
async def index(request: Request):
    # Get the JSON payload from the POST body
    body = await request.body()
    payload = json.loads(body.decode('utf-8'))
    request_param = payload.get("request")
    
    return StreamingResponse(streamer(request_param))

