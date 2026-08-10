# API Gateway AI Agents - Strands Framework + Amazon Bedrock AgentCore

Developer experience customization and centralized guidance using [Strands framework](https://github.com/strands-agents) and [Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/).

Implementation uses single AI agent with access to a knowledge base and various tools. The same agent can be used as an API expert or API Inspector.

## Code
- [iac](./iac/README.md) - Amazon Bedrock Knowledge Base used by the AI agent
- [api-expert-agent](./api-expert-agent/README.md) - Implementation of the agent using Strands framework and Amazon Bedrock AgentCore Runtime
- [mcp](./mcp/README.md) - Implementation and configuration of Model Context Protocol (MCP) server for API Expert agent
- [eda](./eda/README.md) - Implementation of event-driven inspection of an Amazon API Gateway endpoint
