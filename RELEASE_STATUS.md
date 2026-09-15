# Private Club — release status

Updated after the v10 → v11 engineering audit. This distinguishes what was
actually executed from what's still blocked, per repository rule.

## Выполнено в коде (this audit)

- **Test-suite reproducibility.** Fixed a settings/engine singleton bug that
  made pytest results order-dependent (`app.config.settings` was built once
  at first import; per-file `os.environ` assignments after that were
  silent no-ops). Moved required env defaults into `tests/conftest.py`.
- **`/ready` was silently broken.** `readiness()` called `sqlalchemy.text()`
  without importing it; the `NameError` was swallowed by a bare `except`,
  so the database check reported `false` forever, even against a healthy
  Postgres. Fixed and verified against a real local Postgres + Redis.
- **Removed the ADMIN_API_KEY browser admin surface entirely**
  (`/api/admin/*`), which the spec explicitly forbids. Staff auth is now
  Telegram allowlist + TOTP (`/api/v8/staff/auth/telegram`) only, and it's
  the *only* staff login path — the previous TOTP-less
  `/api/v7/staff/auth/telegram` login route is gone too.
- **Removed a full-scope IDOR.** `/api/users/{uid}/...` endpoints took the
  caller's identity from the URL path with no session check — any caller
  could view/act as any member, including deleting their account. Session-
  authenticated `/api/v6/*` endpoints (identity from a Redis-backed bearer
  token, no uid parameter to substitute) now cover every member action:
  profile creation, verification start, catalog, like/match, contact
  reveal, visibility, block, complaint, account deletion. The uid-path
  functions survive only as internal helpers, and are re-exposed as routes
  (alongside a `/api/demo/register` dev shortcut) only when
  `ENVIRONMENT != "production"` — verified absent from the route table
  under `ENVIRONMENT=production`.
- **Removed `/api/v4/*`** (stateless, non-revocable bearer sessions) and the
  dead module behind it — the live Mini App was actually wired to this
  weaker path instead of the Redis-backed sessions that already existed
  alongside it. `club.html`/`admin.html` are rewired to the secured API.
- **Stored XSS, fixed.** `club.html`/`admin.html` built DOM via `innerHTML`
  template literals with unescaped member-supplied text (profile fields,
  complaint reasons). Confirmed exploitable and fixed with a real
  Chromium/Playwright run (payload executed before the fix, was inert
  after); regression-guarded with a static test.
- **Uploads now actually go through validation/AV/storage.** The bot stored
  raw Telegram `file_id`s for both profile photos and verification media —
  magic-byte validation, ClamAV scanning, and the private MinIO layer were
  fully implemented but never called. Now wired end to end; verification
  media and profile photos are stored under private object keys, never
  Telegram's own CDN reference.
- **Real account-deletion lifecycle.** Previously only flipped a status
  column. Now anonymizes the profile, attempts to delete profile-photo and
  verification-media objects (fail-safe: keeps the pointer for retry if the
  object store is unreachable, never just drops it), and revokes *every*
  active session for the account (new Redis reverse index), not just the
  one used to call delete. BAN/SUSPEND also revoke sessions immediately.
- **Outbox worker: real backoff + dead-letter.** Was retrying every pending
  row every 5s regardless of failure count. Now schedules exponential
  backoff (`next_attempt_at`, migration 0003) and dead-letters
  (`FAILED` + audit entry) after 5 attempts.
- **TrustedHost + strengthened production guard.** Production now requires
  `TELEGRAM_BOT_TOKEN` and an `https://` `PUBLIC_BASE_URL` at startup
  (previously neither was checked), and rejects a forged `Host` header.
- **`Base.metadata.create_all` no longer runs against Postgres** — only for
  the sqlite databases tests/local dev use. Postgres is Alembic-only.
- **Structured access logging added** (method/path/status/duration only —
  verified it never logs the query string/body, where initData/tokens/TOTP
  codes live). There was previously no logging at all in the codebase.
- **Photo moderation.** Profile photos now have an explicit
  PENDING/APPROVED/REJECTED status with staff list/approve/reject
  endpoints; the catalog and `/me` only ever serve APPROVED photos via
  short-lived signed URLs.
- Deleted two confirmed-dead modules (`app/auth.py`, a non-revocable v4
  session helper; `app/services/storage.py`, a superseded local-filesystem
  storage helper) rather than leaving them as unreachable code implying a
  security property that wasn't actually wired up.

## Проверено фактически (with evidence, this session)

| Check | Result | Evidence |
|---|---|---|
| Compile all modules | PASS | `python -m py_compile` — 0 errors |
| Static release audit | PASS | `scripts/release_audit.py` exit 0 (1 WARN: dev defaults in docker-compose.yml, expected) |
| Unit + integration pytest | PASS | 49 passed, 1 skipped (staging-only marker), against **sqlite** |
| Same suite against real PostgreSQL | PASS | Local PostgreSQL 16 + Redis 7 (not Docker — installed directly in this sandbox, since no Docker daemon was reachable), `alembic upgrade head` on a clean DB each run, 49 passed |
| `/health`, `/ready` | PASS | Verified against the real Postgres/Redis above |
| E2E flow (register → 18+ → profile → verification → ADMIN_REVIEW → approve → catalog → like → match → contact reveal → block → complaint → deletion) | PASS | `tests/test_member_flow.py`, exercised via the real HTTP API with genuine Telegram-initData HMAC signatures and real TOTP codes (not stubbed) |
| Negative-path coverage | PASS | Not-yet-approved blocked, revoked/logged-out session rejected, wrong TOTP rejected, TOTP brute force rate-limited, non-allowlisted Telegram id rejected, MODERATOR blocked from BAN / ADMIN can BAN, MIME-spoofed/oversized/empty uploads rejected, malware-scan protocol (clean/infected/scanner-unreachable) against a real fake-clamd TCP server |
| Backup → restore drill | PASS | Real `pg_dump`/`pg_restore` via `scripts/backup.sh`/`scripts/restore_test.sh` into a **separate** database; verified row counts *and* content match across all 6 tables the spec names (users, profiles, verifications, complaints, audit_log, outbox) — not just that a backup file exists |
| Stored XSS in Mini App/admin templates | FOUND & FIXED | Reproduced with a real headless-Chromium run before the fix, confirmed inert after |

## Не может быть подтверждено без дополнительной инфраструктуры

- **MinIO и ClamAV.** No Docker daemon was reachable in this sandbox
  (`docker ps` fails: no socket), and neither has a usable local binary
  here. Postgres and Redis *were* verified for real (installed directly,
  not via Docker) — MinIO/ClamAV integration is code-reviewed and unit/
  protocol-tested (a real fake-clamd TCP server; upload validation logic)
  but not exercised against live instances. **This is the single largest
  remaining gap before staging sign-off.**
- Real Telegram Mini App initData from an actual bot/client (tests sign
  fixtures with the same HMAC algorithm against a test token — this
  exercises the real verification code, but isn't a live Telegram round
  trip).
- Telegram notification delivery to a real chat.
- Container vulnerability scanning.
- Load/performance figures.
- Legal fitness for any specific operator/jurisdiction (out of scope by
  the mandate — never fabricated here).

## Решение

Кодовая база готова к staging-развёртыванию **при условии** подключения
реального MinIO и ClamAV и повторного прогона `tests/integration/` с
`RUN_INTEGRATION=1` против них — это единственный пункт, который в этой
песочнице физически невозможно было проверить (нет Docker и нет локальных
бинарников для этих двух сервисов). Postgres и Redis проверены по-настоящему.
Production launch остаётся заблокирован до: реального стейджинг-прогона с
MinIO/ClamAV, живого теста с реальным Telegram-ботом, container scanning и
явного решения оператора по юридическим требованиям.
