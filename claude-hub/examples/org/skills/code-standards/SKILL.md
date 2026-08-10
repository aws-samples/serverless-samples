# Code Standards Review

Checks code against organizational standards for naming conventions, documentation, error handling, and code quality.

## Steps

1. **Identify changed files**
   Determine the scope of changes to review. If in a git repo:
   ```bash
   git diff --name-only main...HEAD
   ```

2. **Naming conventions**
   - **Python**: snake_case for functions, variables, modules. PascalCase for classes. UPPER_SNAKE_CASE for constants.
   - **JavaScript/TypeScript**: camelCase for functions and variables. PascalCase for classes and components. UPPER_SNAKE_CASE for constants.
   - **Files**: snake_case for Python modules. kebab-case or camelCase for JS/TS files (match project convention).
   - **CloudFormation resources**: PascalCase logical IDs.
   - **DynamoDB**: snake_case for attribute names. PascalCase for table logical IDs.
   - Boolean variables and functions should read as predicates: `is_valid`, `has_access`, `should_retry`.

3. **Documentation standards**
   - Public functions and classes should have docstrings explaining purpose and parameters.
   - Complex business logic should have inline comments explaining "why", not "what".
   - README should be updated when adding new features or changing setup steps.
   - API endpoints should document request/response formats.

4. **Error handling patterns**
   - Never silently swallow exceptions. Always log with `logger.exception()` in except blocks.
   - Use specific exception types, not bare `except:` or `except Exception:` at low levels.
   - Lambda handlers should catch at the top level and return appropriate HTTP status codes.
   - Distinguish between client errors (4xx) and server errors (5xx) in API responses.
   - Include correlation IDs (request ID from context) in error responses and logs.

5. **Logging standards**
   - Use structured logging (key-value pairs or JSON), not string concatenation.
   - Log at appropriate levels: DEBUG for development detail, INFO for business events, WARNING for recoverable issues, ERROR for failures.
   - Include context in log messages: identifiers, counts, durations.
   - Never log secrets, passwords, tokens, or PII.

6. **Code organization**
   - Functions should do one thing. If a function exceeds ~50 lines, consider splitting.
   - No circular imports.
   - Shared utilities belong in a common module or Lambda layer, not duplicated across handlers.
   - Configuration should come from environment variables, not hardcoded values.
   - Use dataclasses or typed dicts for structured data, not raw dicts with string keys.

7. **Testing standards**
   - New code should have corresponding tests.
   - Tests should be independent and not rely on execution order.
   - Use descriptive test names that explain the scenario: `test_returns_404_when_item_not_found`.
   - Mock external dependencies, not internal logic.

## Output

Provide a summary organized by category:
- **Naming**: Any naming convention violations with suggested corrections.
- **Documentation**: Missing or inadequate documentation.
- **Error handling**: Improper error handling patterns.
- **Logging**: Logging issues or gaps.
- **Code organization**: Structural concerns.
- **Testing**: Missing or inadequate test coverage.

For each finding, include the file path, line number, the issue, and the recommended fix.
