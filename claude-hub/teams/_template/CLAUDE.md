# {Team Name} - Team CLAUDE.md

<!--
  HOW TO USE THIS TEMPLATE:

  1. Copy this entire `_template/` directory to a new folder under `teams/`:
     cp -r teams/_template teams/your-team-name

  2. Replace all {placeholders} with your team's actual values.

  3. Fill in each section with your team-specific standards.

  4. Use the "Overrides" section to explicitly override any org-level
     guidance from org/CLAUDE.md that does not apply to your team.
     Be specific about what you are overriding and why.

  5. Remove these instructions and any sections that are not relevant
     to your team.
-->

## Team Overview

<!-- Briefly describe your team's mission, domain, and key responsibilities. -->

- **Team name**: {Team Name}
- **Domain**: {e.g., Payments, Platform, Identity, Data Engineering}
- **Slack channel**: {e.g., #team-payments}
- **On-call rotation**: {link to PagerDuty or on-call schedule}
- **Team lead**: {Name}

## MCP Servers

<!-- If your team uses MCP servers beyond the org-wide ones, add them to
     teams/{team-name}/settings.json under the mcpServers key. These are
     merged with org-level servers on sync. Example:
     {
       "mcpServers": {
         "team-data-lake": {
           "type": "streamable-http",
           "url": "https://mcp.internal.acme.com/data-lake"
         }
       }
     }
-->

## Tech Stack

<!-- List the primary technologies your team uses. This helps Claude Code
     understand which languages, frameworks, and tools to default to. -->

- **Languages**: {e.g., Python 3.12, TypeScript 5.x}
- **Frameworks**: {e.g., FastAPI, Next.js, Express}
- **Infrastructure**: {e.g., AWS SAM, Terraform, CDK}
- **Databases**: {e.g., DynamoDB, PostgreSQL, Redis}
- **CI/CD**: {e.g., GitHub Actions with shared workflows}
- **Testing**: {e.g., pytest, Jest, Playwright}

## Team Conventions

<!-- Define standards specific to your team that go beyond or refine
     the org-level guidance. -->

### Code Style

<!-- Example entries - replace with your team's actual conventions:
- Use Black for Python formatting with line length 100.
- Use ESLint with the team's shared config for TypeScript.
- Prefer dataclasses over dicts for structured data in Python.
-->

### Branching Strategy

<!-- Example:
- Use short-lived feature branches off `main`.
- Branch naming: `{type}/{ticket-id}-{short-description}` (e.g., `feat/PAY-123-add-refunds`).
- Squash merge to main.
-->

### Testing Standards

<!-- Example:
- Minimum 80% code coverage for new code.
- All API endpoints must have integration tests.
- Use Hypothesis for property-based testing of data models.
-->

### Deployment

<!-- Example:
- Deploy to staging automatically on merge to main.
- Production deploys require manual approval in CI.
- Use canary deployments for user-facing services.
-->

## Overrides

<!--
  OVERRIDE PATTERN:

  Use this section to explicitly override org-level guidance from org/CLAUDE.md.
  Each override should state:
    1. What org-level guidance is being overridden
    2. What the team does instead
    3. Why the override exists

  This makes it clear where team practices intentionally differ from the org default.
-->

<!-- EXAMPLE OVERRIDE (remove or replace with your actual overrides):

### PR Size Limit

- **Org standard**: Keep PRs under 400 lines of diff.
- **Team override**: We allow PRs up to 800 lines for database migration changes,
  because migrations often include verbose schema definitions that inflate the diff
  but are straightforward to review.

### API Versioning

- **Org standard**: URL path versioning (e.g., `/v1/resource`).
- **Team override**: We use header-based versioning (`Accept: application/vnd.acme.v2+json`)
  for our internal microservices because our API gateway handles version routing
  and path-based versioning conflicts with our URL structure.

-->
