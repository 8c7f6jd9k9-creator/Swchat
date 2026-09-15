# Staging runbook
1. Create staging-only secrets; never reuse production.
2. Start `docker compose -f docker-compose.staging.yml up -d --build`.
3. Run Alembic upgrade against staging Postgres.
4. Confirm Redis, MinIO and ClamAV are reachable only on the internal Docker network.
5. Run unit tests, then `RUN_INTEGRATION=1 pytest tests/integration -q`.
6. Test with a dedicated Telegram test bot and HTTPS staging domain.
7. Exercise: 18+ → profile → verification → moderation → APPROVED → catalog → like → match → contact consent → block → complaint.
8. Confirm verification media cannot be retrieved through member endpoints.
9. Trigger retention cleanup and inspect audit log.
10. Create backup; restore into disposable database with `scripts/restore_test.sh`.
11. Run dependency/container scans.
12. Only after all gates pass, prepare a limited pilot.
