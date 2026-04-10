<!-- claude-hub:fragment:begin — This section is managed centrally. Do not edit manually. Run /hub-fragment-update to update. -->
# Python Lambda / SAM — Toolchain Reference

## SAM CLI

### Build & Deploy
```bash
sam build                          # Build all functions and layers
sam build --use-container          # Build in Docker (ensures correct Python version)
sam validate                       # Validate template.yaml
sam deploy                         # Deploy using samconfig.toml defaults
sam deploy --guided                # Interactive deploy (first time)
sam delete                         # Tear down the stack
```

### Local Development
```bash
sam local invoke FunctionName -e events/event.json   # Invoke a single function
sam local start-api                                   # Start local API Gateway
sam local generate-event apigateway http-api-proxy    # Generate test events
```

### Testing
```bash
pytest                             # Run all tests
pytest tests/unit/                 # Unit tests only
pytest tests/integration/          # Integration tests only
pytest -x -v                       # Stop on first failure, verbose
pytest --tb=short -q               # Compact output
```

## Project Structure

```
.
├── template.yaml              # SAM/CloudFormation template
├── samconfig.toml             # Deploy configuration
├── src/
│   ├── handlers/              # Lambda function handlers
│   │   └── my_function/
│   │       ├── __init__.py
│   │       └── app.py
│   └── shared/                # Shared code (or use a Layer)
├── layers/                    # Lambda layers (source root, no python/ nesting)
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── events/                    # Sample event payloads
└── scripts/                   # Seed data, utilities
```

## Lambda Handler Pattern

```python
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

def lambda_handler(event, context):
    logger.info("Received event", extra={"event": json.dumps(event)})
    try:
        # Business logic here
        result = process(event)
        logger.info("Processing complete", extra={"result_count": len(result)})
        return {
            "statusCode": 200,
            "body": json.dumps(result),
        }
    except Exception:
        logger.exception("Unhandled error processing event")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"}),
        }
```

## DynamoDB Patterns

- Always use `ExpressionAttributeNames` for potentially reserved words (`#status`, `#name`, `#type`, etc.).
- Use conditional writes for idempotency: `ConditionExpression="attribute_not_exists(pk)"`.
- Handle pagination: loop until `LastEvaluatedKey` is absent.
- TTL values must be Unix epoch timestamps (number), not ISO strings.
- Use `ADD` for atomic counters: `UpdateExpression="ADD #count :inc"`.

## Testing with pytest and moto

- Use `mock_aws` context manager (not legacy `mock_dynamodb`).
- Create DynamoDB tables in fixtures matching the CloudFormation template exactly (all GSIs, key schemas, attribute definitions).
- Provide a `make_api_event()` helper for API Gateway proxy events.
- Reset module-level caches between tests.
- Accept optional boto3 clients via constructor for testability.
- Use Hypothesis for property-based testing of serialization round-trips.

## Environment Variables

Lambda functions should read configuration from environment variables defined in `template.yaml`. Common variables:

- `LOG_LEVEL` - Logging verbosity
- `TABLE_NAME` - DynamoDB table name (use `!Ref` in template)
- `STACK_NAME` - From `!Ref AWS::StackName`, used in user-visible strings
- `POWERTOOLS_SERVICE_NAME` - If using AWS Lambda Powertools

## Key Pitfalls

- `sam build` requires the exact Python version on PATH matching the runtime. Use `--use-container` if unavailable locally.
- SAM layer `BuildMethod` adds a `python/` prefix automatically. Do not nest source under `python/`.
- HTTP API v2 has a hard 30-second integration timeout. Use async patterns (SQS, EventBridge) for long operations.
- Never reference `ServerlessRestApi`/`ServerlessHttpApi` in function environment variables (circular dependency).
- `!Sub` cannot be used as a CloudFormation Parameter default.
- First deploy may fail with KMS/CreateGrant race condition. Delete the failed stack and redeploy.
<!-- claude-hub:fragment:end — Add your project-specific content below this line. -->

# Project Notes

<!-- Add project-specific guidance here: architecture, conventions, deployment notes, lessons learned. -->
