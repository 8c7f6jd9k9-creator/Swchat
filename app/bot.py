import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from sqlalchemy import select
from .config import settings
from .db import SessionLocal
from .models import User, Consent, Verification, ProfilePhoto
from .services.upload_validation import validate_profile, validate_verification
from .services.malware import scan
from .services.object_storage import put_profile_photo, put_verification

async def _download(bot: Bot, file_id: str) -> bytes:
    f = await bot.get_file(file_id)
    buf = await bot.download_file(f.file_path)
    return buf.read()

dp=Dispatcher()
def keyboard(rows):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(**r)] for r in rows])

@dp.message(CommandStart())
async def start(m:types.Message):
    with SessionLocal() as db:
        u=db.execute(select(User).where(User.telegram_id==m.from_user.id)).scalar_one_or_none()
        if not u:
            u=User(telegram_id=m.from_user.id,telegram_username=m.from_user.username,status="NEW"); db.add(u); db.commit()
    await m.answer("Private Club — закрытое сообщество знакомств 18+. Доступ к участникам только после проверки и ручного одобрения.",
        reply_markup=keyboard([{"text":"Мне есть 18 лет","callback_data":"age_yes"},{"text":"Отказаться","callback_data":"age_no"}]))

@dp.callback_query(F.data=="age_no")
async def age_no(c:types.CallbackQuery):
    await c.message.edit_text("Регистрация прекращена. Сервис доступен только совершеннолетним."); await c.answer()

@dp.callback_query(F.data=="age_yes")
async def age_yes(c:types.CallbackQuery):
    with SessionLocal() as db:
        u=db.execute(select(User).where(User.telegram_id==c.from_user.id)).scalar_one()
        if u.status=="NEW":
            u.status="AGE_CONFIRMED"; db.add(Consent(user_id=u.id,kind="RULES_18_PLUS",version=settings.rules_version)); db.commit()
    rows=[{"text":"Открыть клуб","web_app":WebAppInfo(url=settings.public_base_url)}] if settings.public_base_url.startswith("https://") else []
    await c.message.edit_text("18+ подтверждено. Заполните анкету. Верификационный материал используется только для проверки и не показывается другим участникам.",
        reply_markup=keyboard(rows) if rows else None); await c.answer()

@dp.message(F.photo | F.video)
async def media(m:types.Message,bot:Bot):
    with SessionLocal() as db:
        u=db.execute(select(User).where(User.telegram_id==m.from_user.id)).scalar_one_or_none()
        if not u: return
        if u.status=="VERIFICATION_PENDING":
            v=db.execute(select(Verification).where(Verification.user_id==u.id).order_by(Verification.id.desc())).scalars().first()
            if not v: return
            file_id = m.photo[-1].file_id if m.photo else m.video.file_id
            try:
                data = await _download(bot, file_id)
                mime = validate_verification(data)
                scan(data)
                key = put_verification(data, mime)
            except Exception:
                await m.answer("Не удалось принять файл верификации. Отправьте фото или короткое видео в поддерживаемом формате (JPEG/PNG/WEBP/MP4, до 25 МБ).")
                return
            v.media_file_id=file_id; v.media_type="photo" if m.photo else "video"; v.storage_key=key
            v.status="SUBMITTED"; u.status="ADMIN_REVIEW"; db.commit()
            await m.answer("Верификация получена. Анкета передана администратору. До одобрения каталог закрыт.")
        elif u.status in {"AGE_CONFIRMED","PROFILE_CREATED","APPROVED"} and m.photo:
            count=len(db.execute(select(ProfilePhoto).where(ProfilePhoto.user_id==u.id)).scalars().all())
            if count>=settings.max_profile_photos:
                await m.answer("Достигнут лимит фотографий профиля."); return
            file_id = m.photo[-1].file_id
            try:
                data = await _download(bot, file_id)
                mime = validate_profile(data)
                scan(data)
                key = put_profile_photo(data, mime)
            except Exception:
                await m.answer("Не удалось принять фото. Поддерживаются JPEG/PNG/WEBP до 10 МБ.")
                return
            db.add(ProfilePhoto(user_id=u.id,telegram_file_id=file_id,storage_key=key,content_type=mime,position=count,status="PENDING",approved=False)); db.commit()
            await m.answer("Фото профиля принято и будет доступно после модерации.")

async def main():
    if not settings.telegram_bot_token: raise RuntimeError("TELEGRAM_BOT_TOKEN не задан")
    await dp.start_polling(Bot(settings.telegram_bot_token))
if __name__=="__main__": asyncio.run(main())
