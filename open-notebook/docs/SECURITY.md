# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| master  | ✅ Active development |
| latest release | ✅ |

## Reporting a Vulnerability

Please **do not** open a public issue for security vulnerabilities.

Report privately by email or via a [private security advisory]
(https://github.com/SCurrya/notebook-evo/security/advisories/new)
if available. You should receive a response within 48 hours.

Include in your report:

- The affected endpoint / component and version
- Steps to reproduce
- Impact assessment (data exposure? RCE? etc.)

## Security Posture

This project applies several hardening measures:

- **SSRF / DNS rebinding protection** — outbound URL validation rejects
  link-local (`169.254.x.x`) and AWS IMDSv6 addresses (see
  `open_notebook/utils/url_validation.py`)
- **SurrealQL injection protection** — all queries use parameter binding
  via `_ensure_safe_identifier` instead of string interpolation
- **Jinja2 template injection protection** — transformation templates are
  fixed; user instructions are injected as plain variables
- **Password auth** — constant-time comparison (`secrets.compare_digest`),
  Swagger docs also protected
- **Model provider fallback** — cross-provider degradation keeps the
  service running when the primary model provider fails

For the full audit trail see `docs/SECURITY_REVIEW.md`.
