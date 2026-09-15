# Security baseline

1. Не хранить `.env` в Git.
2. Использовать длинные случайные SECRET_KEY, ADMIN_API_KEY и пароль PostgreSQL.
3. Только HTTPS для Telegram Mini App.
4. Не логировать Telegram initData, токены сессий и verification media IDs.
5. Материал верификации не является фотографией профиля и удаляется после решения/истечения retention.
6. Административные действия пишутся в audit_log.
7. Постоянный BAN разрешён роли ADMIN; MODERATOR ограничен операционной модерацией.
8. Публичные endpoints v4 используют подписанную сессию после серверной проверки Telegram initData.
9. Есть базовый rate limit. Для нескольких инстансов заменить in-memory limiter на Redis.
10. Перед production: CSP, CSRF для cookie-сценариев, reverse proxy HTTPS, WAF/rate limit, backups, secret manager, malware scanning, S3-compatible private storage, Alembic, централизованные логи и мониторинг.
11. Не собирать паспорт, адрес, место работы и иные данные, не необходимые для функции сервиса.
12. Не использовать автоматический risk score как доказательство нарушения: это только сигнал для ручной проверки.
