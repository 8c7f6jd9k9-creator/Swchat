
from pathlib import Path
import re,sys
root=Path(__file__).resolve().parents[1]
errors=[]; warnings=[]
required=["docker-compose.staging.yml","deploy/nginx.production.conf","SECURITY.md","DEPLOYMENT_CHECKLIST.md","docs/STAGING_RUNBOOK.md"]
for x in required:
    if not (root/x).exists(): errors.append("missing "+x)
env=(root/".env.example").read_text()
for k in ["SECRET_KEY","POSTGRES_PASSWORD","TELEGRAM_BOT_TOKEN","REDIS_URL","S3_SECRET_KEY","STAFF_TOTP_SECRET","STAFF_TELEGRAM_IDS"]:
    if k not in env: errors.append("env missing "+k)
for p in root.rglob("*.py"):
    txt=p.read_text(errors="ignore")
    if re.search(r'(sk-[A-Za-z0-9]{20,}|[0-9]{8,10}:[A-Za-z0-9_-]{30,})',txt):
        errors.append("possible embedded credential: "+str(p.relative_to(root)))
if "change-me" in (root/"docker-compose.yml").read_text():
    warnings.append("docker-compose.yml contains development defaults; never use them in production")
print("RELEASE AUDIT")
for x in errors: print("ERROR:",x)
for x in warnings: print("WARN:",x)
print("RESULT:", "FAIL" if errors else "PASS")
sys.exit(1 if errors else 0)
