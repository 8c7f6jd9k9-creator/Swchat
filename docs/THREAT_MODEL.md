# Threat model — concise
Assets: identity linkage, profile photos, verification media, Telegram IDs, matches, complaints, staff decisions.
Primary threats: unauthorized pre-approval access; IDOR; leaked verification media; stolen admin credential; scraping; spam; impersonation; block bypass; malicious uploads; database/object-store exposure.
Controls present: server-side APPROVED gate; Telegram initData validation; Redis server sessions; rate limiting; block filtering; separate verification/profile media; no member signed URL for verification; staff Telegram allowlist + roles; audit log; outbox; retention worker.
Required before public launch: malware/content upload validation, HTTPS/CSP/security headers, 2FA or stronger staff second factor, reviewed DB migration, object-store network isolation, backup/restore test, E2E, dependency/container scanning, incident response and legal/privacy review.
