# Acme Corp - Organization CLAUDE.md

<!-- TODO: Replace "Acme Corp" with your actual organization name throughout this file. -->

This file defines organization-wide standards and guidance for all teams using Claude Code at Acme Corp.

## Organization Coding Standards

### General Principles

- Write clear, readable code. Favor explicitness over cleverness.
- Follow the language-specific style guide adopted by the organization (see links below).
- All production code must be reviewed by at least one peer before merging.
- Keep functions focused and small. If a function exceeds ~50 lines, consider splitting it.
- Use meaningful names for variables, functions, and classes. Avoid single-letter names outside of trivial loop counters.

<!-- TODO: Link to your organization's style guides for each language. -->
<!-- Example:
- Python: https://wiki.internal.acme.com/style/python
- TypeScript: https://wiki.internal.acme.com/style/typescript
- Go: https://wiki.internal.acme.com/style/go
-->

### Code Review Expectations

- PRs should be reviewed within one business day.
- Reviewers must check for correctness, readability, test coverage, and security concerns.
- Use conventional comments (e.g., `suggestion:`, `nit:`, `blocker:`) to clarify review intent.
- Approve only when all blocker comments are resolved.

## Project Creation

New projects and services should be created through the Backstage developer portal.

<!-- TODO: Replace with your actual Backstage or developer portal URL. -->
- **Portal URL**: https://backstage.internal.acme.com
- Use the appropriate template for your project type (service, library, infrastructure).
- All new repositories must include a `CLAUDE.md` at the project root with project-specific guidance.
- Register new services in the service catalog within the first week of creation.

### Repository Naming

<!-- TODO: Adjust naming conventions to match your organization's standards. -->
- Services: `{team-name}-{service-name}` (e.g., `platform-auth-service`)
- Libraries: `lib-{name}` (e.g., `lib-common-utils`)
- Infrastructure: `infra-{name}` (e.g., `infra-networking`)

## Internal Tools

### CI/CD

<!-- TODO: Replace with your actual CI/CD platform and URLs. -->
- **Platform**: GitHub Actions / Jenkins / GitLab CI (pick one)
- **Pipeline dashboard**: https://ci.internal.acme.com
- All repositories must have CI pipelines that run linting, tests, and security scans on every PR.
- Production deployments require passing CI and at least one approval.
- Use the shared workflow templates from the `acme-ci-templates` repository when available.

### Observability

<!-- TODO: Configure with your actual observability stack. -->
- **Logging**: All services must emit structured JSON logs.
- **Metrics**: Expose standard metrics (request count, latency, error rate) via the shared metrics library.
- **Tracing**: Use distributed tracing for all inter-service communication.
- **Dashboards**: https://grafana.internal.acme.com
- **Alerting**: https://pagerduty.internal.acme.com

### MCP servers

MCP servers configured in `org/settings.json` are distributed to all developers automatically. These give Claude Code direct access to internal tools during a session. See `org/settings.json` for the current list of org-wide servers and `teams/<team>/settings.json` for team-specific additions.

<!-- TODO: Document any authentication requirements for your MCP servers here.
   For example: "The Jira MCP server uses SSO. Run `jira-auth login` before your
   first Claude Code session to store credentials." -->

### Internal APIs

<!-- TODO: Add links to your API catalog and standards documentation. -->
- All internal APIs must be documented in the API catalog.
- Use OpenAPI 3.x specifications for REST APIs.
- Follow the organization API versioning strategy: URL path versioning (e.g., `/v1/resource`).
- Rate limiting and authentication are required for all APIs, even internal ones.

## Security and Compliance

### Security Requirements

- Never commit secrets, API keys, or credentials to source control.
- All dependencies must be scanned for known vulnerabilities in CI.
- Apply the principle of least privilege for all IAM roles and service accounts.
- Enable encryption at rest and in transit for all data stores and communication channels.
- Conduct threat modeling for any new service that handles PII or financial data.

<!-- TODO: Link to your security policies and incident response procedures. -->
<!-- Example:
- Security policy: https://wiki.internal.acme.com/security/policy
- Incident response: https://wiki.internal.acme.com/security/incident-response
-->

### Dependency Management

- Use Dependabot or Renovate for automated dependency updates.
- Review and merge dependency update PRs within one week.
- Pin major versions in production services; allow minor/patch auto-updates for libraries.
- Prohibited licenses: GPL-3.0, AGPL-3.0 in any service distributed externally.

<!-- TODO: Add any additional license restrictions or approved-license lists. -->

### Secrets Handling

<!-- TODO: Replace with your actual secrets management platform. -->
- Use the organization secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault) for all secrets.
- Rotate secrets on a regular schedule (at least every 90 days for service credentials).
- Never pass secrets via environment variables in CI logs or error messages.
- Use short-lived tokens and assume-role patterns where possible.

## Communication and Collaboration

### Pull Request Conventions

- PR titles must follow Conventional Commits format: `type(scope): description`
  - Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`
- Include a description of **what** changed and **why**.
- Link related issues or tickets in the PR description.
- Keep PRs focused and reasonably sized (under 400 lines of diff when practical).
- Use draft PRs for work-in-progress that needs early feedback.

### Documentation Expectations

- All services must have a README with: purpose, setup instructions, architecture overview, and runbook links.
- Architecture Decision Records (ADRs) should be created for significant technical decisions.
- Keep documentation close to the code it describes (prefer in-repo docs over external wikis).
- Update documentation as part of the same PR that changes behavior.

### Team Communication

<!-- TODO: Replace with your actual communication channels. -->
- **Primary channel**: Slack `#engineering`
- **Incident channel**: Slack `#incidents`
- **Architecture discussions**: Slack `#architecture`
- Use threads for extended discussions to keep channels readable.
