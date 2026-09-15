# Claude takeover changelog

## v11 engineering audit

Repository imported from the handoff archive into a fresh repo (this one
had none of the project's history — see git log for the import commit),
then audited and hardened per CLAUDE.md. Commits, in order:

1. **Import Private Club v10** — the handoff archive's `private_club_v10/`
   contents as the starting point.
2. **Fix test-suite isolation bug** — `app.config.settings`/`app.db.engine`
   are process-wide singletons built once at first import; several test
   modules set `os.environ` per-file assuming isolation that didn't exist.
   Moved required env defaults into `tests/conftest.py`.
3. **Fix `/ready` always reporting database unhealthy** — missing
   `sqlalchemy.text` import, silently swallowed by a bare `except`.
4. **Remove insecure legacy auth surfaces; wire uploads through
   validation/AV/S3** — deleted `/api/admin/*` (ADMIN_API_KEY-in-browser,
   explicitly forbidden), `/api/v4/*` (non-revocable sessions), the v1
   `/api/auth/telegram`, and the TOTP-less staff login path. Fixed a
   full-scope IDOR in the uid-path member endpoints (now internal helpers
   only, or dev-only routes). Wired `app/bot.py`'s photo/video handling
   through the previously-unused validation/malware-scan/object-storage
   services instead of storing raw Telegram file_ids.
5. **Rewire Mini App/admin templates to the secured API; add real profile
   creation** — `club.html`/`admin.html` were still calling the endpoints
   removed in the previous commit. Added `/api/v6/profile` (there was
   previously no way for a real Telegram user to ever create a Profile
   row). Added a bot `/staff` entry point for the admin Mini App.
6. **Implement real account-deletion lifecycle** — anonymize profile,
   attempt real object-storage deletion (fail-safe on an unreachable
   store), revoke every active session for the account, not just flip a
   status column. Also bounded the MinIO client's retry/timeout budget
   (was stalling requests 10+ seconds on an unreachable store).
7. **Add TrustedHost middleware and strengthen production config guard** —
   production now requires `TELEGRAM_BOT_TOKEN` and an `https://`
   `PUBLIC_BASE_URL` at startup; rejects a forged `Host` header.
8. **Give the outbox worker real exponential backoff and a dead-letter
   path** — was retrying every pending row every 5s regardless of prior
   failures.
9. **Remove unused local-filesystem storage module** — dead code
   superseded by the MinIO-backed object storage service.
10. **Fix stored XSS** — `club.html`/`admin.html` interpolated
    member-supplied text (profile fields, complaint reasons) into
    `innerHTML` template literals unescaped. Confirmed exploitable and
    fixed with a real headless-Chromium run.
11. **Add structured access logging** — there was none at all previously.
    Deliberately narrow (method/path/status/duration only) to avoid ever
    logging initData/session tokens/TOTP codes.

See RELEASE_STATUS.md and VERIFICATION_REPORT.md for what's verified vs.
still blocked (MinIO/ClamAV live testing and a live Telegram round trip
need a real environment/bot token that wasn't available in this sandbox).
