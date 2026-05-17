"""
Driver application flow ("Ulanish uchun Ariza").

FSM steps:
  full_name -> phone -> warning_ack ->
  passport_front -> passport_back ->
  license_front  -> license_back  ->
  texpassport_front -> texpassport_back ->
  [save + notify admin]
"""

import logging
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    FSInputFile,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession

from database.admin import get_notification_chat_ids
from database.assets import get_prompt_image_file_id, save_prompt_image_file_id
from database.db import get_session
from database.models import Application, User
from database.reports import add_application_notification
from database.users import get_or_create_user
from keyboards.reply import continue_kb, main_menu_kb, phone_request_kb, remove_kb
from services.google_sheets import schedule_google_sheets_sync
from states.forms import DriverStates

router = Router()
logger = logging.getLogger(__name__)
IMAGES_DIR = Path(__file__).resolve().parent / "images"

WARNING_TEXT = (
    "⚠️ <b>Diqqat!</b>\n\n"
    "Endi sizdan hujjatlaringizning originalini rasmga olib jo'natishingiz so'raladi.\n\n"
    "❌ Soliqdan olingan skrinshot <b>QABUL QILINMAYDI!</b>\n\n"
    "Davom etish uchun pastdagi knopkani bosing."
)

# ── Entry point ───────────────────────────────────────────────────────────────

@router.message(F.text == "📝 Ulanish uchun Ariza")
async def driver_start(message: Message, state: FSMContext) -> None:
    user = await get_or_create_user(
        message.from_user.id,  # type: ignore[union-attr]
        message.from_user.username,  # type: ignore[union-attr]
    )
    await state.clear()
    await state.update_data(promocode=user.promocode)
    await message.answer(
        "✏️ Iltimos, ism va familiyangizni yozing:",
        reply_markup=remove_kb(),
    )
    await state.set_state(DriverStates.full_name)


# ── Step 1: full_name ─────────────────────────────────────────────────────────

@router.message(DriverStates.full_name)
async def get_full_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("Ism bo'sh bo'lmasligi kerak. Qayta yozing:")
        return
    await state.update_data(full_name=name)
    await message.answer(
        "📞 Iltimos, telefon raqamingizni jo'nating (knopka orqali):",
        reply_markup=phone_request_kb(),
    )
    await state.set_state(DriverStates.phone)


# ── Step 2: phone (contact) ───────────────────────────────────────────────────

@router.message(DriverStates.phone, F.contact)
async def get_phone_contact(message: Message, state: FSMContext) -> None:
    phone = message.contact.phone_number  # type: ignore[union-attr]
    await state.update_data(phone=phone)
    await message.answer(WARNING_TEXT, reply_markup=continue_kb(), parse_mode="HTML")
    await state.set_state(DriverStates.warning_ack)


@router.message(DriverStates.phone)
async def get_phone_fallback(message: Message) -> None:
    await message.answer(
        "Iltimos, telefon raqamingizni <b>knopka</b> orqali jo'nating:",
        reply_markup=phone_request_kb(),
        parse_mode="HTML",
    )


# ── Step 3: warning acknowledgement ──────────────────────────────────────────

@router.message(DriverStates.warning_ack, F.text == "✅ Davom etish")
async def warning_acked(message: Message, state: FSMContext) -> None:
    await _send_photo_prompt(
        message,
        "passport_front.png",
        "1/12 — <b>Passport (old tarafi)</b> rasmini jo'nating:",
        reply_markup=remove_kb(),
    )
    await state.set_state(DriverStates.passport_front)


@router.message(DriverStates.warning_ack)
async def warning_not_acked(message: Message) -> None:
    await message.answer("Iltimos, pastdagi tugmani bosing.", reply_markup=continue_kb())


# ── Photo helper ──────────────────────────────────────────────────────────────

def _file_id(message: Message) -> str | None:
    if message.photo:
        return message.photo[-1].file_id
    return None


async def _expect_photo(message: Message, next_prompt: str) -> str | None:
    fid = _file_id(message)
    if not fid:
        await message.answer(next_prompt)
        return None
    return fid


async def _send_photo_prompt(
    message: Message,
    image_name: str,
    caption: str,
    *,
    reply_markup=None,
) -> None:
    image_path = IMAGES_DIR / image_name
    cached_file_id = await get_prompt_image_file_id(image_name)
    if cached_file_id:
        try:
            await message.answer_photo(
                cached_file_id,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
            return
        except TelegramBadRequest as exc:
            logger.warning("Cached prompt image %s failed: %s", image_name, exc)

    if image_path.exists():
        sent_message = await message.answer_photo(
            FSInputFile(image_path),
            caption=caption,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
        if sent_message.photo:
            await save_prompt_image_file_id(image_name, sent_message.photo[-1].file_id)
        return

    await message.answer(caption, reply_markup=reply_markup, parse_mode="HTML")


# ── Step 4–6: individual document photos ─────────────────────────────────────

# PHOTO_STEPS = [
#     ("passport_front",    DriverStates.passport_front,    "passport_back.png",          "2/12 — <b>Passport (orqa tarafi)</b> rasmini jo'nating:",                 DriverStates.passport_back),
#     ("passport_back",     DriverStates.passport_back,     "guvohnoma_old.png",          "3/12 — <b>Haydovchilik guvohnomasi (old tarafi)</b> rasmini jo'nating:",    DriverStates.license_front),
#     ("license_front",     DriverStates.license_front,     "guvohnoma_orqa.png",         "4/12 — <b>Haydovchilik guvohnomasi (orqa tarafi)</b> rasmini jo'nating:",   DriverStates.license_back),
#     ("license_back",      DriverStates.license_back,      "texnik_passport_old.png",    "5/12 — <b>Texnik passport (old tarafi)</b> rasmini jo'nating:",             DriverStates.texpassport_front),
#     ("texpassport_front", DriverStates.texpassport_front, "texnik_passport_orqa.png",   "6/12 — <b>Texnik passport (orqa tarafi)</b> rasmini jo'nating:",            DriverStates.texpassport_back),
#     ("texpassport_back",  DriverStates.texpassport_back,  "selfi.png",                  "7/12 — <b>Selfie</b> rasmingizni jo'nating:",                              DriverStates.selfie),
#     ("selfie",            DriverStates.selfie,            "litsenziga.png",             "8/12 — <b>Litsenziya</b> rasmini jo'nating:",                              DriverStates.license_card),
# ]

PHOTO_STEPS = [
    (
        "passport_front",
        DriverStates.passport_front,
        "passport_back.png",
        "2/6 — <b>Passport (orqa tarafi)</b> rasmini jo'nating:",
        DriverStates.passport_back,
    ),
    (
        "passport_back",
        DriverStates.passport_back,
        "guvohnoma_old.png",
        "3/6 — <b>Haydovchilik guvohnomasi (old tarafi)</b> rasmini jo'nating:",
        DriverStates.license_front,
    ),
    (
        "license_front",
        DriverStates.license_front,
        "guvohnoma_orqa.png",
        "4/6 — <b>Haydovchilik guvohnomasi (orqa tarafi)</b> rasmini jo'nating:",
        DriverStates.license_back,
    ),
    (
        "license_back",
        DriverStates.license_back,
        "texnik_passport_old.png",
        "5/6 — <b>Texnik passport (old tarafi)</b> rasmini jo'nating:",
        DriverStates.texpassport_front,
    ),
    (
        "texpassport_front",
        DriverStates.texpassport_front,
        "texnik_passport_orqa.png",
        "6/6 — <b>Texnik passport (orqa tarafi)</b> rasmini jo'nating:",
        DriverStates.texpassport_back,
    ),
]

def _make_photo_handler(field: str, current_state, next_image: str, next_prompt: str, next_state):
    """Factory to avoid closure issues inside a loop."""

    @router.message(StateFilter(current_state), F.photo)
    async def _handler(message: Message, state: FSMContext) -> None:
        fid = message.photo[-1].file_id  # type: ignore[index]
        await state.update_data(**{field: fid})
        await _send_photo_prompt(message, next_image, next_prompt)
        await state.set_state(next_state)

    @router.message(StateFilter(current_state))
    async def _bad(message: Message) -> None:
        await message.answer("Iltimos, rasm jo'nating (foto shaklida).")

    return _handler, _bad


for _field, _cur, _next_image, _next_prompt, _next_state in PHOTO_STEPS:
    _make_photo_handler(_field, _cur, _next_image, _next_prompt, _next_state)


# ── Step 13: car_photos (4 photos) ───────────────────────────────────────────

# CAR_LABELS = ["old", "orqa", "chap", "o'ng"]


# @router.message(DriverStates.car_photos, F.photo)
# async def collect_car_photos(message: Message, state: FSMContext) -> None:
#     data = await state.get_data()
#     photos: list = data.get("car_photos", [])
#     photos.append(message.photo[-1].file_id)  # type: ignore[index]
#     await state.update_data(car_photos=photos)

#     received = len(photos)
#     remaining = 4 - received

#     if remaining > 0:
#         await message.answer(
#             f"✅ <b>{received}/4</b> ta rasm qabul qilindi. Yana <b>{remaining}</b> ta rasm jo'nating.",
#             parse_mode="HTML",
#         )
#     else:
#         # All 4 received → move to plate_number
#         await message.answer(
#             "🔢 Endi mashinangizning <b>davlat raqamini</b> yozing (masalan: 01A123BC):",
#             parse_mode="HTML",
#         )
#         await state.set_state(DriverStates.plate_number)


# @router.message(DriverStates.car_photos)
# async def car_photos_bad(message: Message, state: FSMContext) -> None:
#     data = await state.get_data()
#     received = len(data.get("car_photos", []))
#     remaining = 4 - received
#     await message.answer(
#         f"Iltimos, rasm jo'nating. Hali <b>{remaining}</b> ta rasm kerak.",
#         parse_mode="HTML",
#     )


# ── Step 14: plate_number → save → notify ────────────────────────────────────

# @router.message(DriverStates.plate_number)
# async def get_plate_number(message: Message, state: FSMContext, bot: Bot) -> None:
#     plate = (message.text or "").strip().upper()
#     if not plate:
#         await message.answer("Davlat raqami bo'sh bo'lmasligi kerak. Qayta yozing:")
#         return

#     await state.update_data(plate_number=plate)
#     data = await state.get_data()

#     # ── Persist to DB ──────────────────────────────────────────────────────────
#     session: AsyncSession = get_session()
#     try:
#         from sqlalchemy import select

#         result = await session.execute(
#             select(User).where(User.telegram_id == message.from_user.id)  # type: ignore[union-attr]
#         )
#         user = result.scalar_one_or_none()
#         if user is None:
#             user = User(
#                 telegram_id=message.from_user.id,  # type: ignore[union-attr]
#                 username=message.from_user.username,  # type: ignore[union-attr]
#             )
#             session.add(user)
#             await session.flush()

#         car_photos: list = data.get("car_photos", [])
#         app = Application(
#             user_id=user.id,
#             full_name=data["full_name"],
#             phone=data["phone"],
#             promocode=data.get("promocode"),
#             passport_front_id=data["passport_front"],
#             passport_back_id=data["passport_back"],
#             license_front_id=data["license_front"],
#             license_back_id=data["license_back"],
#             texpassport_front_id=data["texpassport_front"],
#             texpassport_back_id=data["texpassport_back"],
#             selfie_id=data["selfie"],
#             license_card_id=data["license_card"],
#             car_photo_1_id=car_photos[0],
#             car_photo_2_id=car_photos[1],
#             car_photo_3_id=car_photos[2],
#             car_photo_4_id=car_photos[3],
#             plate_number=plate,
#             status="new",
#         )
#         session.add(app)
#         await session.flush()
#         application_id = app.id
#         await session.commit()
#     except Exception:
#         await session.rollback()
#         raise
#     finally:
#         await session.close()

#     await state.clear()

#     # ── Notify admin ───────────────────────────────────────────────────────────
#     await _notify_admin(bot, application_id, data, plate)

#     # ── Success message ────────────────────────────────────────────────────────
#     await message.answer(
#         "🎉 <b>Tabriklaymiz!</b>\n\n"
#         "Arizangiz qabul qilindi. Tez orada operatorlarimiz tomonidan "
#         "ko'rib chiqilib, qayta javob yozib yuboriladi.",
#         parse_mode="HTML",
#         reply_markup=main_menu_kb(),
#     )


# # ── Admin notification ────────────────────────────────────────────────────────

# async def _notify_admin(bot: Bot, application_id: int, data: dict, plate: str) -> None:
#     promo_line = f"🎟 Promocode: <code>{data.get('promocode')}</code>" if data.get("promocode") else "🎟 Promocode: yo'q"

#     summary = (
#         "📋 <b>Yangi haydovchi arizasi!</b>\n\n"
#         f"👤 F.I.O: {data['full_name']}\n"
#         f"📞 Telefon: {data['phone']}\n"
#         f"🚘 Davlat raqami: <code>{plate}</code>\n"
#         f"{promo_line}"
#     )
#     car_photos: list = data.get("car_photos", [])
#     all_photos = [
#         data["passport_front"],
#         data["passport_back"],
#         data["license_front"],
#         data["license_back"],
#         data["texpassport_front"],
#         data["texpassport_back"],
#         data["selfie"],
#         data["license_card"],
#         *car_photos,
#     ]

#     captions = [
#         "Passport (old)",
#         "Passport (orqa)",
#         "Guvohnoma (old)",
#         "Guvohnoma (orqa)",
#         "Tex. passport (old)",
#         "Tex. passport (orqa)",
#         "Selfie",
#         "Litsenziya",
#         "Mashina — old",
#         "Mashina — orqa",
#         "Mashina — chap",
#         "Mashina — o'ng",
#     ]

#     for chat_id in await get_notification_chat_ids():
#         try:
#             summary_message = await bot.send_message(chat_id, summary, parse_mode="HTML")
#             await add_application_notification(
#                 "driver",
#                 application_id,
#                 chat_id,
#                 summary_message.message_id,
#             )

#             for fid, caption in zip(all_photos, captions):
#                 await bot.send_photo(chat_id, fid, caption=caption)
#         except (TelegramBadRequest, TelegramForbiddenError) as exc:
#             logger.warning("Failed to notify chat %s: %s", chat_id, exc)

@router.message(DriverStates.texpassport_back, F.photo)
async def finish_application(
    message: Message,
    state: FSMContext,
    bot: Bot,
) -> None:
    await state.update_data(
        texpassport_back=message.photo[-1].file_id
    )

    data = await state.get_data()

    session: AsyncSession = get_session()

    try:
        from sqlalchemy import select

        result = await session.execute(
            select(User).where(
                User.telegram_id == message.from_user.id
            )
        )

        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
            )
            session.add(user)
            await session.flush()

        app = Application(
            user_id=user.id,
            full_name=data["full_name"],
            phone=data["phone"],
            promocode=data.get("promocode"),

            passport_front_id=data["passport_front"],
            passport_back_id=data["passport_back"],

            license_front_id=data["license_front"],
            license_back_id=data["license_back"],

            texpassport_front_id=data["texpassport_front"],
            texpassport_back_id=data["texpassport_back"],

            status="new",
        )

        session.add(app)

        await session.flush()

        application_id = app.id

        await session.commit()

    except Exception:
        await session.rollback()
        raise

    finally:
        await session.close()

    await state.clear()

    await message.answer(
        "🎉 <b>Tabriklaymiz!</b>\n\n"
        "Arizangiz qabul qilindi. Janob Taxi admini tez orada aloqaga chiqadi.",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )

    await _notify_admin(
        bot,
        application_id,
        data,
    )
    schedule_google_sheets_sync(f"driver:{application_id}")


@router.message(DriverStates.texpassport_back)
async def texpassport_back_bad(message: Message) -> None:
    await message.answer(
        "Iltimos, rasm jo'nating."
    )


async def _notify_admin(
    bot: Bot,
    application_id: int,
    data: dict,
) -> None:

    promo_line = (
        f"🎟 Promocode: <code>{data.get('promocode')}</code>"
        if data.get("promocode")
        else "🎟 Promocode: yo'q"
    )

    summary = (
        "📋 <b>Yangi haydovchi arizasi!</b>\n\n"
        f"👤 F.I.O: {data['full_name']}\n"
        f"📞 Telefon: {data['phone']}\n"
        f"{promo_line}"
    )

    all_photos = [
        data["passport_front"],
        data["passport_back"],
        data["license_front"],
        data["license_back"],
        data["texpassport_front"],
        data["texpassport_back"],
    ]

    captions = [
        "Passport (old)",
        "Passport (orqa)",
        "Guvohnoma (old)",
        "Guvohnoma (orqa)",
        "Tex. passport (old)",
        "Tex. passport (orqa)",
    ]

    for chat_id in await get_notification_chat_ids():
        try:
            summary_message = await bot.send_message(
                chat_id,
                summary,
                parse_mode="HTML",
            )

            await add_application_notification(
                "driver",
                application_id,
                chat_id,
                summary_message.message_id,
            )

            for fid, caption in zip(all_photos, captions):
                await bot.send_photo(
                    chat_id,
                    fid,
                    caption=caption,
                )

        except (
            TelegramBadRequest,
            TelegramForbiddenError,
        ) as exc:
            logger.warning(
                "Failed to notify chat %s: %s",
                chat_id,
                exc,
            )
