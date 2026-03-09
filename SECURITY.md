# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |

## Reporting Vulnerabilities

If you discover a security vulnerability, please report it responsibly:

1. **Do not** open a public issue
2. Email security findings to the maintainers with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Suggested fix (if any)
3. You will receive an acknowledgment within 48 hours
4. A fix will be developed and released as soon as possible

## Security Architecture

### Authentication & Authorization

```
┌──────────────┐     ┌───────────────┐     ┌──────────────┐
│   Client     │────▶│  JWT Verify   │────▶│ Role Check   │
│  (Bearer /   │     │  (HS256)      │     │ (admin/      │
│   Cookie)    │     │               │     │  auditor/    │
│              │     │               │     │  user)       │
└──────────────┘     └───────────────┘     └──────────────┘
                                                  │
                                           ┌──────▼──────┐
                                           │ Tenant      │
                                           │ Isolation   │
                                           │ (X-Tenant-  │
                                           │  ID header) │
                                           └─────────────┘
```

- **JWT tokens** with configurable expiration (default 60 min)
- **HttpOnly secure cookies** (configurable Secure, SameSite, Domain)
- **PBKDF2+SHA256** password hashing
- **RBAC** with three roles:
  - `admin` — full access including user/tenant management
  - `auditor` — read access to documents, approvals, and audit logs
  - `user` — chat and document preview only

### Multi-Tenant Data Isolation

Data isolation is enforced at three layers:

| Layer | Mechanism |
|-------|-----------|
| **API** | `X-Tenant-ID` header verified against `user_tenants` table |
| **Database** | All queries filtered by `tenant_id` column |
| **Vector DB** | Qdrant payload filter: `tenant_id` match on every search |

A user can only access tenants they are explicitly assigned to via the `user_tenants` join table.

### Output Security

- **Output policy guard** — Configurable regex patterns scan every LLM response for:
  - AWS access keys (`AKIA...`, `ASIA...`)
  - API secret keys (`sk-...`, `rk-...`)
  - Private keys (RSA, SSH, EC, DSA)
  - Inline credentials (`password=...`)
- **Prompt injection guardrails** — System prompts instruct the LLM to refuse data exfiltration attempts
- **Human-in-the-loop approval** — Answers can be held for human review before release

### Input Security

- **Filename sanitization** — Uploaded filenames are sanitized to prevent directory traversal
- **File extension allowlist** — Only configured extensions are accepted (default: pdf, txt, md, png, jpg, jpeg)
- **File size limit** — Configurable maximum upload size (default: 20MB)
- **Document preview path traversal protection** — Resolved paths verified against configured storage root
- **CSV export formula injection mitigation** — Cell values prefixed to prevent Excel formula execution

### Infrastructure Security

- **Trusted host middleware** — Rejects requests from untrusted Host headers
- **Security headers** — CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy
- **CORS** — Configurable allowed origins
- **Non-root Docker container** — API runs as unprivileged user
- **OPA/Conftest policy gate** — Infrastructure-as-code changes validated against security policies
- **TLS** — HTTPS enforced via ALB in production

### Audit & Compliance

- **Full audit trail** — Every user action is logged with timestamp, user, tenant, action, input, output, and metadata
- **Audit log search** — Query by action, user, date range
- **CSV export** — Download audit logs for compliance reporting
- **Request ID tracing** — Unique request ID propagated across all service calls

## Security Checklist for Production

- [ ] Change `APP_JWT_SECRET_KEY` from default
- [ ] Set `APP_COOKIE_SECURE=true`
- [ ] Set `APP_COOKIE_SAMESITE=strict` or `lax`
- [ ] Configure `APP_CORS_ORIGINS` to production domains only
- [ ] Configure `APP_TRUSTED_HOSTS` to production domains only
- [ ] Use `APP_DEMO_PASSWORD_HASH` instead of `APP_DEMO_PASSWORD`
- [ ] Use PostgreSQL instead of SQLite (`APP_DATABASE_URL`)
- [ ] Set `APP_METRICS_TOKEN` for Prometheus endpoint protection
- [ ] Enable TLS termination at load balancer
- [ ] Review and customize `APP_OUTPUT_POLICY_BLOCK_PATTERNS`
- [ ] Set `APP_ENV=production` and `APP_LOG_FORMAT=json`
