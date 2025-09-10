# API Requirements Gatherer Agent

An interactive AI agent built with the Strands framework that systematically gathers comprehensive requirements for Amazon API Gateway projects through intelligent questioning and conversation flow.

## Features

- **Interactive Requirements Gathering**: Conducts structured conversations to collect all necessary API project details
- **Comprehensive Questionnaire**: Covers authentication, integration targets, security, networking, and deployment requirements
- **AI-Powered Conversation**: Uses Amazon Bedrock (Nova Pro) for intelligent follow-up questions and clarifications
- **Structured Output**: Produces well-formatted requirements documents ready for development teams
- **User-Friendly Interface**: Provides clear, conversational interactions with minimal technical jargon
- **Complete Coverage**: Ensures no critical requirements are missed through systematic questioning

## Architecture

The agent consists of:
- **Python Application**: Interactive console application for local use
- **Strands Framework**: Agent orchestration with user interaction tools
- **Amazon Bedrock**: AI model for intelligent conversation management (Nova Pro)
- **Handoff Tool**: Enables interactive user communication and question flow

## Installation

### 1. Install dependencies

```bash
cd src/
pip install -r requirements.txt
```

### 2. Configure AWS credentials

Ensure your AWS credentials are configured for Bedrock access:

```bash
aws configure
```

## Usage

### Interactive Mode

Run the agent locally for interactive requirements gathering:

```bash
python src/main.py
```

The agent will:
1. Ask for your initial API description
2. CGather detailed requirements
3. Ask follow-up questions based on your responses
4. Generate a requirements document


## Output Format

The agent produces structured requirements in this format:

```xml
<request>Original user request</request>
<requirements>
- Detailed requirement 1
- Detailed requirement 2
- Integration specifications
- Security configurations
- Deployment preferences
</requirements>
```

## Configuration

### Environment Variables

- `BEDROCK_MODEL`: Bedrock model ID (default: `amazon.nova-pro-v1:0`)
- `STRANDS_TOOL_CONSOLE_MODE`: Set to `enabled` for interactive console mode

## Local Development

The agent is designed primarily for local interactive use:

```bash
python src/main.py
```



