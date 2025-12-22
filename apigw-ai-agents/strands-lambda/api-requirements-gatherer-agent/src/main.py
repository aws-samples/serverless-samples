# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved. 
# SPDX-License-Identifier: MIT-0

from strands import Agent, tool
from strands_tools import handoff_to_user
import logging
import json
import os

bedrock_model=os.environ.get("BEDROCK_MODEL", "amazon.nova-pro-v1:0")

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

SYSTEM_PROMPT = """
    <task_description>
        You are an experienced API developer tasked with initializing a project to create an Amazon API Gateway for a REST API. Your goal is to gather the necessary information from the user for building API and related code artifacts.
        Ask questions using handoff to user tool until you have enough information. Use `message` property of the tool to present your question.
    </task_description>

    <instructions>

    <user_interaction>
        Ask user to describe use case in more details if it is not in the original request.
        Also ask the user the following questions to identify features required for the project:

        <user_questions>
            - What is your preferred programming language to be used if code examples need to be generated?
            - Do you need a private or public API endpoint?
            - What is the integration target for the API? Valid options:
            - Existing public resource over HTTP
            - Lambda function
            - Other AWS service
            - Existing resources in a private VPC (e.g., container orchestrator, on-premises applications accessible via DirectConnect)
            - What identity provider will be used to determine authentication and authorization for the API? Valid options:
            - None
            - IAM
            - Amazon Cognito
            - 3rd party OIDC/OAuth compliant identity provider
            - Custom
            (Do not offer to use API keys for authentication/authorization.)
            - Are rate limiting and usage quotas needed?
            - Will you use this API by a web application and need to add CORS configuration to the API? If yes, which domains should be allowed?
            - What CI/CD tools do you use or are familiar with?
        </user_questions>

        If API uses private endpoint, ask follow-up questions:
        <user_questions>
            - What is VPC ID from where this API should be accessible
            - What are subnet IDs from where this API should be accessible
        </user_questions>

        If integration target uses existing public resources over HTTP, ask follow-up question:
        <user_questions>
            - What is URL of the resource to be used in the integration target definition
        </user_questions>

        If integration target uses existing resources in a private VPC, ask follow-up questions:
        <user_questions>
            - What is load balancer ARN to be used in VPC Link configuration
            - What is load balancer DNS name to be used in the integration target definition
        </user_questions>

        If integration target uses Lambda functions, ask follow-up questions:
        <user_questions>
            - Are these new or already existing Lambda functions
            - In case of already existing functions - what are ARN of the functions to be used for each resource and method
            _ if new functions will be used - should functions generated include basics business logics
        </user_questions>

        If authentication uses Amazon Cognito, ask follow-up question:
        <user_questions>
            - Do you want to use existing Amazon Cognito user pool, and if so - what is ID of the user pool
        </user_questions>

        If CORS configuration is needed and domain was not provided, ask follow-up question:
        <user_questions>
            - Which domain should be allowed in the CORS configuration
        </user_questions>

    </user_interaction>

    </instructions>

    <response_format>
        Provide your response immediately without any preamble, enclosed in <requirements></requirements> tags. 
        Include original user request within <request></request> tags
        Response example:
        <request>Build pet store e-commerce API</request>
        <requirements>
        - Build e-commerce API for a pet store. 
        - Include endpoints for inventory, orders, customer management, shopping cart
        - Use public API endpoints
        - Create new Lambda functions to be used as integration targets, include business logics samples into the code
        - Use Okta as identity provider and create Lambda Authorizer
        - Configure CORS allowing access from www.example.com domain
        - Do not use throttling or metering of the API
        - Use GitHub for CI/CD pipelines and actions
        </requirements>
    </response_format>
"""

# Custom callback handler to control verbosity
def minimal_callback_handler(**kwargs):

    # Initialize static variables for tracking thinking tags
    if not hasattr(minimal_callback_handler, 'buffer'):
        minimal_callback_handler.buffer = ""
        minimal_callback_handler.in_thinking = False
    
    # Print "Thinking..." when the message starts
    if "event" in kwargs and "messageStart" in kwargs["event"]:
        print("\nThinking...", end="", flush=True)
        # Reset state for new message
        minimal_callback_handler.buffer = ""
        minimal_callback_handler.in_thinking = False
 
    # Process incoming text data, filter out thinking sections
    elif "delta" in kwargs and kwargs["delta"] is not None:
        # Get text from delta.text structure
        text = kwargs.get("delta", {}).get("text", "")
        
        if text:
            # Add new text to buffer
            minimal_callback_handler.buffer += text
            
            # Process buffer to handle thinking tags
            output = ""
            processed_up_to = 0
            
            while processed_up_to < len(minimal_callback_handler.buffer):
                if not minimal_callback_handler.in_thinking:
                    # Look for opening thinking tag
                    thinking_start = minimal_callback_handler.buffer.find("<thinking>", processed_up_to)
                    if thinking_start != -1:
                        # Output text before thinking tag
                        output += minimal_callback_handler.buffer[processed_up_to:thinking_start]
                        minimal_callback_handler.in_thinking = True
                        processed_up_to = thinking_start + 10  # Skip past "<thinking>"
                    else:
                        # No thinking tag found, check if we might have partial tag at end
                        partial_tags = ["<", "<t", "<th", "<thi", "<thin", "<think", "<thinki", "<thinkin", "<thinking"]
                        buffer_end = minimal_callback_handler.buffer[processed_up_to:]
                        has_partial = any(buffer_end.endswith(tag) for tag in partial_tags)
                        
                        if has_partial:
                            # Keep potential partial tag in buffer
                            cutoff = next(len(tag) for tag in partial_tags if buffer_end.endswith(tag))
                            output += buffer_end[:-cutoff]
                            minimal_callback_handler.buffer = buffer_end[-cutoff:]
                        else:
                            # Output remaining text and clear buffer
                            output += buffer_end
                            minimal_callback_handler.buffer = ""
                        break
                else:
                    # Look for closing thinking tag
                    thinking_end = minimal_callback_handler.buffer.find("</thinking>", processed_up_to)
                    if thinking_end != -1:
                        minimal_callback_handler.in_thinking = False
                        processed_up_to = thinking_end + 11  # Skip past "</thinking>"
                        # Continue processing from after the closing tag
                    else:
                        # No closing tag found, check if we might have partial closing tag at end
                        partial_tags = ["<", "</", "</t", "</th", "</thi", "</thin", "</think", "</thinki", "</thinkin", "</thinking"]
                        buffer_end = minimal_callback_handler.buffer[processed_up_to:]
                        has_partial = any(buffer_end.endswith(tag) for tag in partial_tags)
                        
                        if has_partial:
                            # Keep potential partial tag in buffer
                            cutoff = next(len(tag) for tag in partial_tags if buffer_end.endswith(tag))
                            minimal_callback_handler.buffer = buffer_end[-cutoff:]
                        else:
                            # Clear buffer (all thinking content)
                            minimal_callback_handler.buffer = ""
                        break
            
            # Update buffer to remove processed content
            if processed_up_to > 0 and minimal_callback_handler.buffer:
                minimal_callback_handler.buffer = minimal_callback_handler.buffer[processed_up_to:]
            
            # Print the filtered output
            if output:
                print(output, end="", flush=True)
 
    # Add final newline when message is complete
    elif "event" in kwargs and "messageStop" in kwargs["event"]:
        print("\n")
        # Reset state for next message
        minimal_callback_handler.buffer = ""
        minimal_callback_handler.in_thinking = False


def main():
    """
    Local invocation function for testing the agent
    """
    os.environ["STRANDS_TOOL_CONSOLE_MODE"] = "enabled"

    print("Starting local invocation of API Requirements Gatherer Agent...")
    print("Please provide your API request as input:")
    
    try:
        # Get user input for the request
        user_request = input("Enter your API requirements: ")
        
        if not user_request.strip():
            print("No request provided. Exiting.")
            return
        
        request_event = {"request": user_request}
        print(f"Processing request: {user_request}")
        print("-" * 50)

        agent = Agent(
            system_prompt=SYSTEM_PROMPT,
            tools=[handoff_to_user],
            model=bedrock_model,
            callback_handler=minimal_callback_handler  # This replaces the default verbose output
            )
        logger.info("Agent initialized successfully")

        response = agent(user_request)
        logger.info(f"Response: {response}")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"Error during local invocation: {e}")


if __name__ == "__main__":
    main()        