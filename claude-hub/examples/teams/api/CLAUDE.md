# API Team

## Team Overview

- **Team name**: API
- **Domain**: Public and internal REST APIs
- **Slack channel**: #team-api
- **On-call rotation**: https://pagerduty.internal.acme.com/schedules/api
- **Team lead**: John Doe

## Tech Stack

- **Languages**: Python 3.12
- **Frameworks**: FastAPI, SQLAlchemy
- **Infrastructure**: Terraform, ECS Fargate
- **Databases**: PostgreSQL 16, Redis 7 (caching)
- **CI/CD**: GitHub Actions with shared workflows from `acme-ci-templates`
- **Testing**: pytest, testcontainers-python for integration tests

## ACME API Team Conventions

### Code Style

- Use Ruff for linting and formatting with the team's `pyproject.toml` config.
- Type-annotate all function signatures. Run mypy in strict mode.
- Keep route handlers thin: extract business logic into service classes, keep HTTP concerns in routers.
- Use Pydantic models for all request and response schemas.

### API Design

Full style guide: https://wiki.internal.acme.com/api-style. Key rules below.

#### URLs and resources

- Plural nouns for collections: `/users`, `/products`, `/orders`.
- Lowercase with hyphens for multi-word resources: `/user-profiles`, `/order-items`.
- No file extensions in URLs.
- Limit nesting to 2 levels: `/users/123/orders` is fine, deeper is not.
- `snake_case` for query parameters: `?created_after=2024-01-01&status=active`.

#### HTTP methods

- `GET` must be safe (no side effects) and cacheable.
- `POST` creates a resource. Return `201 Created` with a `Location` header.
- `PUT` replaces the entire resource. Must be idempotent. Include all required fields.
- `PATCH` for partial updates. Include only the fields being changed.
- `DELETE` returns `204 No Content`. Must be idempotent. Return `404` if the resource doesn't exist.

#### Request and response format

- `application/json` for all request and response bodies.
- `snake_case` for JSON field names.
- ISO 8601 for dates: `"2024-01-15T10:30:00Z"`.
- All resources include `id`, `created_at`, and `updated_at`.
- Single resource response: `{ "data": { "id": "...", "type": "...", "attributes": { ... } } }`.
- Collection response: `{ "data": [...], "pagination": { "has_more": true, "next_cursor": "..." } }`.

#### Error handling

- Return `application/problem+json` (RFC 9457) for all errors.
- Error body structure:
  ```json
  {
    "error": {
      "code": "validation_failed",
      "message": "Human-readable description",
      "details": [{ "field": "email", "code": "invalid_format", "message": "..." }],
      "request_id": "req_123456789"
    }
  }
  ```
- Standard error codes: `invalid_request`, `authentication_failed`, `permission_denied`, `resource_not_found`, `validation_failed`, `rate_limit_exceeded`.
- Never expose internal system details in error messages.

#### Status codes

- `200` for successful GET, PUT, PATCH. `201` for successful POST. `204` for successful DELETE.
- `400` bad request, `401` missing/invalid auth, `403` insufficient permissions, `404` not found, `409` conflict, `422` valid syntax but semantic error, `429` rate limited.

#### Authentication

- HTTPS for all endpoints.
- Bearer token in `Authorization` header.
- `401` for invalid auth, `403` for insufficient permissions.

#### Versioning

- Major version in URL path: `/v1/users`, `/v2/users`.
- Backward compatible within a major version.
- Support previous major version for at least 12 months after deprecation.

#### Pagination

- Cursor-based pagination by default: `?limit=25&after=cursor_abc123`.
- Default limit 25, max 100.
- Response includes `has_more` and `next_cursor`.

#### Rate limiting

- Return rate limit headers with all responses: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.
- `429 Too Many Requests` with `retry_after` in the error body.

#### Documentation

- OpenAPI 3.x spec for all endpoints. Every new or changed endpoint needs a spec update.
- Specs must include descriptions, request/response examples, and error response examples.
- Every new endpoint needs an OpenAPI spec before implementation starts.

### Branching Strategy

- Short-lived feature branches off `main`.
- Branch naming: `{type}/{ticket-id}-{short-desc}` (e.g., `feat/API-342-add-teams-endpoint`).
- Squash merge to main.

### Testing Standards

- All endpoints must have integration tests using testcontainers-python (real Postgres, real Redis).
- Do not mock the database. We got burned when mocked tests passed but a migration broke prod.
- Minimum 80% coverage on new packages.
- Contract tests for any endpoint consumed by another team.

### Deployment

- Merge to main triggers deploy to staging.
- Production deploy requires passing staging smoke tests and one approval in CI.
- Breaking API changes require a deprecation notice at least two sprints before removal.

## Overrides

### API Versioning

- **Org standard**: URL path versioning (`/v1/resource`).
- **Team override**: We use URL path versioning too, but additionally require a `Sunset` header on deprecated versions and a `Deprecation` header per the draft IETF standard. The org standard does not mention deprecation signaling.

### PR Size Limit

- **Org standard**: Keep PRs under 400 lines of diff.
- **Team override**: OpenAPI spec changes and database migrations can push PRs to 600+ lines. Reviewers should focus on the non-generated portions; the spec diff is validated by CI.
