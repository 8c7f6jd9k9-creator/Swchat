# Roadmap после v4

## P0 перед реальным запуском
- Alembic и контролируемые миграции PostgreSQL.
- Private S3-compatible media storage + signed URLs.
- Redis: distributed rate limiting, sessions/one-time state, background jobs.
- HTTPS + reverse proxy + secure headers.
- Полная staff-auth: привязка ADMIN/MODERATOR к Telegram IDs или отдельному IdP, 2FA для администраторов.
- Уведомления: заявка принята, одобрено, повторная проверка, отклонено, новый match, новая жалоба для staff.
- Retention worker для verification media.
- Политика резервного копирования и восстановления.
- E2E тесты ключевого пути.

## P1 продукт
- Галерея до 6 фото с ручной модерацией каждого фото.
- География без точных координат.
- Расширенные фильтры и сохранённые предпочтения.
- "Не показывать больше", undo последнего пропуска.
- Очередь жалоб с категориями и доказательствами.
- Повторная верификация при существенной смене фото.
- Invite codes с лимитами и репутацией приглашений.
- Ненавязчивые push/Telegram уведомления с настройками приватности.

## P2 масштабирование
- Redis/Celery или другой job queue.
- Object storage/CDN только для разрешённого публичного контента.
- Метрики SLA, moderation turnaround, abuse rate, match conversion.
- Горизонтальное масштабирование API и bot workers.
