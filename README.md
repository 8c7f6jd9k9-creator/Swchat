# Private Club v10 — staging candidate

v10 adds production configuration refusal, readiness checks, static release audit and an evidence report from checks actually executed in this build environment.

## Important
`/health` means the API process is alive. `/ready` additionally checks PostgreSQL and Redis.
When `ENVIRONMENT=production`, unsafe/missing critical settings cause startup refusal.

Run:
- `python scripts/release_audit.py`
- `pytest -q`
- `docker compose -f docker-compose.staging.yml up -d --build`
- `alembic upgrade head`
- then execute the staging runbook.

See `VERIFICATION_REPORT.md` and `RELEASE_STATUS.md` for the exact current evidence and remaining gates.
