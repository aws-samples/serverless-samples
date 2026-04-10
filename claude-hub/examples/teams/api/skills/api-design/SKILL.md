# API Design Review

Reviews API changes for consistency with the Acme API style guide, REST conventions, and backward compatibility.

## Steps

1. **Identify API surface changes**
   Find modified handlers, routes, and OpenAPI spec files:
   ```bash
   git diff --name-only main...HEAD | grep -E '\.(go|yaml|json)$'
   ```

2. **Check resource naming**
   - Plural nouns for collections (`/v1/users`, not `/v1/user`).
   - No verbs in paths (`POST /v1/orders`, not `POST /v1/create-order`).
   - Lowercase with hyphens for multi-word resources (`/user-profiles`, not `/userProfiles`).
   - `snake_case` for query parameters and JSON field names.
   - Nested resources go two levels deep max (`/v1/users/{id}/orders`, not deeper).

3. **Check request and response patterns**
   - `POST` returns `201 Created` with a `Location` header.
   - `DELETE` returns `204 No Content` with no body.
   - Single resources wrapped in `{ "data": { "id", "type", "attributes" } }`.
   - Collections include `pagination` with `has_more` and `next_cursor`. Default limit 25, max 100.
   - Error responses use the standard error body: `{ "error": { "code", "message", "details", "request_id" } }`.
   - All responses include rate limit headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`).

4. **Check backward compatibility**
   - No required fields added to existing request bodies without a version bump.
   - No removed or renamed fields in existing responses.
   - Deprecated endpoints must include `Deprecation` and `Sunset` headers.
   - If a breaking change is necessary, confirm a new version path exists (`/v2/...`).

5. **Check OpenAPI spec**
   - Every new or changed endpoint has a matching spec update.
   - Spec validates cleanly:
     ```bash
     npx @redocly/cli lint openapi.yaml
     ```
   - Response schemas include examples.

## Output

List each finding with the file, line, what's wrong, and how to fix it. Group by severity:
- **Breaking**: Changes that will break existing clients.
- **Style**: Deviations from the API style guide.
- **Suggestion**: Improvements that aren't required.
