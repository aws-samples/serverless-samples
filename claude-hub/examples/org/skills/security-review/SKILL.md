# Security Review

Performs a security review of code changes, checking for common vulnerabilities and security issues.

## Steps

1. **Identify changed files**
   Determine the scope of changes to review. If in a git repo, compare against the base branch:
   ```bash
   git diff --name-only main...HEAD
   ```

2. **Check for hardcoded secrets**
   Search for potential secrets, API keys, tokens, and credentials in changed files:
   - AWS access keys (patterns starting with `AKIA`)
   - Private key blocks in PEM format
   - Connection strings with embedded passwords
   - Hardcoded tokens, passwords, or passphrases
   - `.env` files or credentials files committed to the repo

3. **Check for injection vulnerabilities**
   Review code for:
   - **SQL injection**: Raw string concatenation in SQL queries. Require parameterized queries.
   - **Command injection**: Unsanitized input passed to shell-executing functions (subprocess with `shell=True`, etc.). Require argument lists instead of shell strings.
   - **XSS**: User input rendered in HTML without escaping.
   - **Template injection**: User input in format strings, Jinja templates, or f-strings used in prompts.
   - **Path traversal**: User-supplied file paths without validation (directory traversal with `../`).

4. **Review OWASP Top 10 concerns**
   - **Broken access control**: Missing authorization checks, overly permissive IAM policies, CORS misconfigurations.
   - **Cryptographic failures**: Weak algorithms (MD5, SHA1 for security), missing encryption at rest or in transit.
   - **Insecure design**: Missing rate limiting, no input validation at system boundaries.
   - **Security misconfiguration**: Debug mode enabled, default credentials, unnecessary permissions.
   - **Vulnerable dependencies**: Check `requirements.txt` / `package.json` for known vulnerable versions.
   - **Authentication failures**: Weak token generation, missing MFA considerations, session management issues.
   - **Data integrity failures**: Missing signature verification, insecure deserialization (unsafe YAML loading, untrusted binary deserialization).
   - **Logging failures**: Sensitive data in logs (passwords, tokens, PII).
   - **SSRF**: User-controlled URLs in server-side HTTP requests without validation.

5. **Check dependency security**
   If dependency files changed:
   ```bash
   # Python
   pip audit  # if pip-audit is installed
   # Node.js
   npm audit
   ```

6. **Review IAM and infrastructure**
   For CloudFormation/SAM templates:
   - No wildcard (`*`) in IAM actions or resources unless justified.
   - Principle of least privilege applied.
   - No overly permissive security groups (0.0.0.0/0 on sensitive ports).
   - Encryption enabled for data at rest (DynamoDB, S3, RDS).

## Output

Provide a summary with:
- **Critical**: Issues that must be fixed before merge (secrets, injection, broken auth).
- **High**: Issues that should be fixed soon (weak crypto, missing validation).
- **Medium**: Issues to address (verbose error messages, missing rate limiting).
- **Low**: Suggestions for improvement (logging hygiene, dependency updates).

For each finding, include the file path, line number, description, and a recommended fix.
