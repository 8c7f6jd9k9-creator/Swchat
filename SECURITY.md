# Security baseline

1. Не хранить `.env` в Git.
2. Использовать длинный случайный SECRET_KEY и пароль PostgreSQL/S3/Redis.
3. Только HTTPS для Telegram Mini App (`PUBLIC_BASE_URL` обязан быть
   `https://` в production — проверяется при старте, см.
   `app/production_guard.py`).
4. Не логировать Telegram initData, токены сессий и verification media IDs.
   `app/middleware/access_log.py` логирует только method/path/status/
   duration — никогда query string или тело запроса.
5. Материал верификации не является фотографией профиля, хранится под
   отдельным префиксом в приватном object storage и удаляется (сам объект,
   а не только ссылка в БД) после решения/истечения retention.
6. Административные действия пишутся в `audit_log`.
7. Постоянный BAN разрешён роли ADMIN; MODERATOR ограничен операционной
   модерацией (проверяется на сервере, не только в UI).
8. Staff-вход — только Telegram allowlist + TOTP второй фактор
   (`/api/v8/staff/auth/telegram`). Простой ADMIN_API_KEY в браузере
   удалён из кодовой базы полностью, а не просто задепрекейчен.
9. Member-сессии — server-side, Redis-backed, с TTL и явным revoke
   (logout, удаление аккаунта, BAN/SUSPEND отзывают все активные сессии
   аккаунта, не только текущую). Нет in-memory fallback: при недоступности
   Redis сервис не переходит в небезопасный режим, а отказывает.
10. Rate limiting — Redis-backed, распределённый, применяется к auth,
    TOTP (защита от brute force), catalog, like, complaint, verification-
    start и profile-create.
11. Перед production: WAF, secret manager, container scanning,
    централизованный мониторинг поверх структурированных логов — то, что
    физически нельзя проверить без реальной инфраструктуры (см.
    VERIFICATION_REPORT.md).
12. Не собирать паспорт, адрес, место работы и иные данные, не
    необходимые для функции сервиса.
13. Не использовать автоматический risk score как доказательство
    нарушения: это только сигнал для ручной проверки.
14. Любой пользовательский текст, отображаемый в Mini App или admin-
    панели (псевдоним, описание, причина жалобы), должен экранироваться
    перед вставкой в DOM — см. `esc()` в `club.html`/`admin.html` и
    `tests/test_xss_regression.py`. Обнаруженный и исправленный в ходе
    аудита stored XSS показал, что это не гипотетический риск.
