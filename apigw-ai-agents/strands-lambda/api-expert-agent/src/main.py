# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. 
# SPDX-License-Identifier: MIT-0

from strands import Agent, tool
from strands_tools import retrieve
import logging
import json
import os

# This code uses environment variables KNOWLEDGE_BASE_ID, and MIN_SCORE
# See retrieve tool code for more details and default values:
# https://github.com/strands-agents/tools/blob/d1de6cf71aaca2b5d1c4d1f7ee8629df10b733ab/src/strands_tools/retrieve.py#L203

bedrock_model=os.environ.get("BEDROCK_MODEL", "amazon.nova-pro-v1:0")

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Lambda function to provide responses based on Amazon Bedrock Knowledge Base content
    """
    logger.info(f"Processing event: {json.dumps(event, default=str)}")

    try:
        request = event["request"]

        agent = Agent(tools=[retrieve], model=bedrock_model)
        logger.info("Agent initialized successfully")

        response = agent(request)
        logger.info(f"Response: {response}")

        return response.message["content"][0]["text"]

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise RuntimeError(f"Request processing failed: {str(e)}")