from aiogram import Bot
from ..config import settings

MESSAGES = {
    "approved": "Ваша анкета одобрена. Доступ к закрытому каталогу открыт.",
    "revision": "Нужна повторная верификация. Откройте бота и следуйте новому заданию.",
    "rejected": "Заявка не одобрена.",
    "suspended": "Доступ к клубу временно ограничен администрацией.",
}

async def send_telegram(telegram_id: int | None, text: str) -> bool:
    if not telegram_id or not settings.telegram_bot_token:
        return False
    bot = Bot(settings.telegram_bot_token)
    try:
        await bot.send_message(telegram_id, text)
        return True
    finally:
        await bot.session.close()
