# CLAUDE.md — Private Club Telegram

## Mission
Continue this repository as a security-first closed 18+ Telegram dating club. Discovery is available only after explicit 18+ confirmation, profile creation, verification and manual approval.

## Non-negotiable invariants
- Never admit minors.
- Before APPROVED, server APIs expose no member profiles, photos, likes, matches or contacts.
- Verification media is private staff evidence and never member-facing.
- Keep profile and verification media separate.
- Contacts remain hidden until voluntary mutual consent after a match.
- Blocks prevent relevant discovery/interaction.
- Permanent BAN requires ADMIN.
- Risk signals may prioritize review but never make irreversible moderation decisions.
- Never log initData, session tokens, TOTP/bot/S3 secrets or verification-media identifiers.
- Do not weaken production security to make tests pass.
- Never invent legal compliance.

## State machine
NEW → AGE_CONFIRMED → PROFILE_CREATED → VERIFICATION_PENDING → ADMIN_REVIEW → APPROVED
Other: REVISION_REQUIRED / REJECTED / SUSPENDED / BANNED / DELETED.
Roles: USER / MODERATOR / ADMIN.

## Architecture
Telegram Bot + Mini App → FastAPI → PostgreSQL
→ Redis sessions/rate limiting
→ private MinIO/S3
→ ClamAV
→ retention + notification-outbox workers.

## Current evidence
Previous build compiled 27 Python modules with zero compile errors and passed its static release audit. Pytest was attempted but collection stopped because that execution environment lacked the `redis` Python package. Rerun tests after installing exact dependencies. Read RELEASE_STATUS.md and VERIFICATION_REPORT.md.

## Work autonomously in this order
1. Create a reproducible isolated environment; install dependencies; run pytest; fix actual failures with regression tests.
2. Start staging PostgreSQL/Redis/MinIO/ClamAV; run Alembic on a clean DB; verify /health and /ready.
3. E2E: 18+ → profile → verification → ADMIN_REVIEW → approval → catalog → like → match → contact consent → block → complaint → sanctions → deletion/anonymization.
4. Connect uploads end-to-end: magic-byte/size validation → malware scan → private storage. Approved profile photos only. Verification evidence staff-only, short-lived and audited. Delete physical verification objects at retention expiry.
5. Complete admin UI: pending verification/photos, complaints, audit, sanctions, reasons, appeal/support. Require Telegram allowlist + TOTP. MODERATOR cannot permanent-ban.
6. Security review: IDOR, CSRF where relevant, CORS/TrustedHost, proxy headers, CSP against actual Telegram embedding requirements, TOTP brute-force protection, redacted structured logs, secret/dependency/container scanning.
7. Data lifecycle: configurable retention and deletion/anonymization; preserve only minimal justified evidence.
8. Operations: backup→restore drill, worker retry/dead-letter behavior, monitoring and incident-response runbook.
9. Remove/disable legacy demo and uid-based APIs in production. Production must not depend on Base.metadata.create_all.

## Definition of staging-ready
Tests pass reproducibly; clean migration succeeds; services healthy; E2E and backup/restore pass; no unresolved critical security findings; no repo secrets; verification media inaccessible to normal users.

## Reporting
Update RELEASE_STATUS.md, VERIFICATION_REPORT.md and CHANGELOG_CLAUDE.md. Report only checks actually executed. Never claim production readiness without evidence.
