# Terra.OS Security

## OWASP Top 10 Status (2026-07-07)

| # | Vulnerability | Status | Notes |
|---|---|---|---|
| A01 | Broken Access Control | ✅ Mitigated | RLS + TenantMiddleware + auth deps |
| A02 | Cryptographic Failures | ✅ Mitigated | HTTPS (Caddy), JWT HS256, bcrypt passwords |
| A03 | Injection | ✅ Mitigated | SQLAlchemy parameterized queries |
| A04 | Insecure Design | ⚠️ Partial | RFQ gate implemented, AI content gated |
| A05 | Security Misconfiguration | ✅ Mitigated | CSP/HSTS via Caddy, non-root Docker |
| A06 | Vulnerable Components | ⚠️ Monitoring | pip-audit + npm audit in CI |
| A07 | Auth Failures | ✅ Mitigated | JWT rotation, rate limit on auth endpoints |
| A08 | Software Integrity | ⚠️ Partial | Gitleaks in CI |
| A09 | Logging Failures | ✅ Mitigated | Structured JSON logs, audit_log table |
| A10 | SSRF | ⚠️ Partial | External API calls gated |

## Security Controls

### Authentication & Sessions
- **JWT** access tokens (60 min) + **refresh token rotation** (30 day, one-time-use)
- Tokens stored in DB (`refresh_tokens` table) with revocation support
- Passwords hashed with **bcrypt** (12 rounds)
- Rate limiting on auth endpoints via **slowapi** (10 req/min per IP)

### CSRF Protection (Task 119)
- **Double-submit cookie** pattern implemented in `middleware/csrf.py`
- Login/register set an `httpOnly=True` `session` cookie + a JS-readable `csrf_token` cookie
- State-changing requests (`POST/PUT/PATCH/DELETE`) must include matching `X-CSRF-Token` header
- Bearer-token based API calls are exempted (browsers never auto-send `Authorization`)

### Transport Security
- **HTTPS enforced** via Caddy reverse proxy
- HSTS header (`max-age=31536000; includeSubDomains`) set by `SecurityHeadersMiddleware`
- `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `X-XSS-Protection: 1; mode=block`

### Multi-Tenancy Isolation
- PostgreSQL **Row-Level Security** (RLS) scoped to `org_id`
- `TenantMiddleware` sets `app.current_tenant` on every request

### Dependency Scanning (Task 123)
- **pip-audit** runs on every CI push/PR and weekly (Monday 06:00 UTC)
- **npm audit** (`--audit-level=high`) runs for frontend dependencies
- Results are non-blocking (`|| true`) to avoid false positive blocks on informational advisories

### Secrets Detection (Task 122)
- **detect-secrets** baseline maintained at `.secrets.baseline`
- CI job fails when new secrets are detected compared to baseline

## Reporting

Security issues: **security@terra-os.pl** (placeholder — replace with real contact)

Please include:
1. Description of the vulnerability
2. Steps to reproduce
3. Potential impact assessment
4. (Optional) Suggested fix

We aim to respond within **72 hours** and issue a fix within **14 days** for critical findings.
