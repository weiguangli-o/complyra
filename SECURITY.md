# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| latest  | Yes       |

## Reporting Vulnerabilities

If you discover a security vulnerability, please report it responsibly:

1. **Do not** open a public issue
2. Email security findings to the maintainers with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
3. You will receive an acknowledgment within 48 hours
4. A fix will be developed and released as soon as possible

## Security Features

Complyra includes the following security measures:

### Authentication & Authorization
- JWT-based authentication with configurable expiration
- RBAC with three roles: `admin`, `auditor`, `user`
- Secure cookie support (HttpOnly, Secure, SameSite)
- PBKDF2+SHA256 password hashing

### Data Protection
- Multi-tenant data isolation at API, database, and vector DB layers
- Tenant access verification on every request
- Input filename sanitization to prevent directory traversal

### Output Security
- Output policy guard scanning for secrets, API keys, and credentials
- Prompt injection guardrails in LLM prompts
- Human-in-the-loop approval workflow for generated answers

### Infrastructure Security
- Trusted host middleware
- Security headers middleware (CSP, X-Frame-Options, etc.)
- CORS configuration
- Non-root Docker container
- OPA/Conftest policy gate for infrastructure-as-code

### Audit & Compliance
- Full audit trail for all user actions
- Audit log search and CSV export
- Request ID tracing across services
