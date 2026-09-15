# Verification report — v11 audit

Strictly separates compile-check / unit / integration / E2E / staging /
live-Telegram, per repository rule. Every PASS below has actual command
output behind it (reproduced in this session); nothing here is inferred
from code reading alone.

## Compile-check

```
$ python -m py_compile $(find app -name '*.py')
$ echo $?
0
```
24 modules, 0 errors. PASS.

```
$ python scripts/release_audit.py; echo $?
RELEASE AUDIT
WARN: docker-compose.yml contains development defaults; never use them in production
RESULT: PASS
0
```
PASS (the WARN is expected/by design — it's flagging that the dev-defaults
compose file exists at all, not that production config is weak; see
`docker-compose.staging.yml`/`docker-compose.yml` for the real deployment
configs, which require every secret via environment variable).

## Unit + integration (pytest)

Environment: Python 3.11, a clean virtualenv, exact `requirements.txt`
pins. Two full runs, same test session, different `DATABASE_URL`:

```
$ python -m pytest -q                                    # sqlite
49 passed, 1 skipped, 1 warning in 4.86s

$ DATABASE_URL="postgresql+psycopg://...@localhost/privateclub_staging" \
  python -m pytest -q                                     # real PostgreSQL 16
49 passed, 1 skipped, 1 warning in 5.20s
```

The 1 skip is `tests/integration/test_core_flow.py`, gated on
`RUN_INTEGRATION=1` and real staging service URLs — see "Blocked" below.

Redis: a real local Redis 7 (`redis-cli ping` → `PONG`), not mocked —
`app/redis_store.py` has no in-memory fallback, so session/rate-limit tests
are exercising the genuine Redis-backed code path.

PostgreSQL: `alembic upgrade head` run against a freshly-created, empty
database before each Postgres run (`DROP DATABASE` / `CREATE DATABASE`
each time) — this is a real clean-database migration test, not just "the
migration file parses".

### What the suite actually covers (not a mock inventory — every item below
### is asserted against real behavior)

- Telegram initData HMAC-SHA256 signature verification (`app/security.py`)
  — fixtures are signed with the documented WebAppData algorithm against a
  test bot token, the same computation `validate_telegram_init_data` does,
  not a stub of that function.
- Real TOTP codes via `pyotp` against `app/staff_2fa.py`.
- Redis-backed session issue/resolve/revoke, including revoking *every*
  session for an account (multi-device) and immediate revocation on ban.
- Role-gated BAN (MODERATOR 403, ADMIN 200).
- Rate limiting: staff TOTP brute force (5/5min, 6th attempt → 429).
- Upload validation: magic-byte detection (JPEG/PNG/WEBP/MP4), MIME
  spoofing, oversized/empty files, per-context limits (profile vs.
  verification).
- Malware scanning: a real TCP server speaking clamd's INSTREAM wire
  protocol (clean/infected/reply-parsing), plus fail-open-in-dev /
  fail-closed-in-production when no ClamAV host is configured.
- Outbox worker: exponential backoff scheduling, dead-letter after 5
  attempts, both on a failed send and on an exception during send.
- Account deletion: profile anonymized, storage_key handling correct
  whether or not the object store is reachable, all sessions revoked.
- Production startup guard: rejects missing `TELEGRAM_BOT_TOKEN` /
  non-https `PUBLIC_BASE_URL`; `TrustedHostMiddleware` accepts the
  configured host and rejects a forged one.
- Stored-XSS regression guard (static check that every known
  member-supplied field stays wrapped in the templates' `esc()`).
- Structured access logging never includes the query string/body (where
  initData/tokens/TOTP codes would be).
- IDOR structural guard: none of the `/api/v6/*` member functions accept a
  `uid` parameter at all (inspected via `inspect.signature`), and the
  uid-path routes are absent from the route table under
  `ENVIRONMENT=production`.

PASS, with the above evidence.

## E2E (API-level, real crypto, not live Telegram)

`tests/test_member_flow.py::test_full_gate_approve_catalog_like_match_contact_block_complaint_delete`
drives the full state machine through the real HTTP API:
register (v6, real signed initData) → blocked pre-approval → staff
ADMIN_REVIEW → approve (v7/v8, real TOTP) → catalog → like → mutual match →
contact reveal (both sides) → complaint → block → re-verify catalog
excludes blocked user → delete account → session revoked.

PASS at the API/DB level. This is **not** a live Telegram round trip — see
"Blocked" below for what would make it one.

## Staging (real services, not Docker — no daemon reachable in this
## sandbox)

- **PostgreSQL 16**: installed directly in this sandbox (not via Docker —
  `docker ps` fails, no daemon socket). `alembic upgrade head` against a
  clean database: PASS, 12 tables (3 migrations: 0001 initial schema, 0002
  photo-moderation storage columns, 0003 outbox backoff column).
- **Redis 7**: installed directly, `PING` → `PONG`. Real sessions/rate
  limiting exercised throughout the suite above.
- **`/health`**, **`/ready`**: PASS against the real Postgres+Redis above —
  `{"ready": true, "checks": {"database": true, "redis": true}}`.
- **Backup → restore drill**: PASS. `scripts/backup.sh` → real `pg_dump`
  against the populated staging DB (17 users, 8 profiles, 3 verifications,
  1 complaint, 10 audit_log rows, 9 outbox rows — populated by the test
  suite runs above, not synthetic filler). `scripts/restore_test.sh` →
  restored into a **separate**, freshly-created database
  (`privateclub_restore_test`); verified row counts match exactly across
  all 6 tables the spec names, and spot-checked that content (including an
  anonymized-on-delete profile alias) survived intact — not just that the
  restore command exited 0.
- **MinIO, ClamAV**: **BLOCKED**. No Docker daemon reachable, no local
  binaries available in this sandbox. The code paths that use them (upload
  validation, malware scanning protocol, object storage key handling) are
  unit/protocol-tested (a real fake-clamd server; a real-but-unreachable
  MinIO endpoint exercising the fail-safe "don't lose the pointer" delete
  path), but never against live instances. This is the one item that
  genuinely needs a real environment (or Docker access) to close out.

## Live Telegram

**BLOCKED — not attempted.** No real bot token, domain, or Telegram client
was available or in scope for this sandbox. `app/bot.py`'s aiogram
handlers are code-reviewed and their DB-side effects are replicated
exactly in test fixtures (see `tests/test_member_flow.py`'s docstring),
but a live `getUpdates`/webhook round trip with a real Telegram client has
not been run. This requires the next step in the master prompt's own
list — a real bot token and domain — which is explicitly something to stop
and ask for, not fabricate.

## Summary

| Level | Result |
|---|---|
| Compile-check | PASS |
| Unit + integration (pytest) | PASS — 49 passed, 1 skipped, on both sqlite and real PostgreSQL+Redis |
| E2E (API-level) | PASS |
| Staging — PostgreSQL/Redis/backup-restore | PASS (real, non-Docker local services) |
| Staging — MinIO/ClamAV | BLOCKED (no Docker daemon, no local binaries in this sandbox) |
| Live Telegram | BLOCKED (needs a real bot token/domain — not fabricated) |
