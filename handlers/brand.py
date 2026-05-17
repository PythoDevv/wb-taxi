"""Brend Ariza flow."""

import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.admin import get_notification_chat_ids
from database.db import get_session
from database.models import BrandApplication, User
from database.reports import add_application_notification
from database.users import get_or_create_user
from keyboards.reply import continue_kb, main_menu_kb, phone_request_kb, remove_kb
from states.forms import BrandStates

router = Router()
logger = logging.getLogger(__name__)

WARNING_TEXT = (
    "⚠️ <b>DIQQAT! BRENDLASH SHARTLARI:</b>\n\n"
    "❌ <b>SPARK</b> — brendlanmaydi\n"
    "❌ <b>NEXIA 3</b> — brendlanmaydi\n"
    "❌ <b>Yili 2015 va undan past mashinalar</b> — brendlanmaydi\n\n"
    "✅ Boshqa mashinalar (yili 2016 va undan yuqori) — brendlanadi\n\n"
    "<i>SPARK va NEXIA 3 yili nechi bo'lishidan qat'iy nazar BREND qilinmaydi. "
    "2016 dan past mashinalar ham brend qilinmaydi (2016 — qilinadi, 2015 — qilinmaydi).</i>\n\n"
    "Davom etish uchun pastdagi knopkani bosing."
)


@router.message(F.text == "🎁 Brend Ariza")
async def brand_start(message: Message, state: FSMContext) -> None:
    user = await get_or_create_user(
        message.from_user.id,  # type: ignore[union-attr]
        message.from_user.username,  # type: ignore[union-attr]
    )
    await state.clear()
    await state.update_data(promocode=user.promocode)

    await message.answer(WARNING_TEXT, reply_markup=continue_kb(), parse_mode="HTML")
    await state.set_state(BrandStates.warning_ack)


@router.message(BrandStates.warning_ack, F.text == "✅ Davom etish")
async def brand_warning_acked(message: Message, state: FSMContext) -> None:
    await message.answer(
        "🎨 <b>Brend Ariza</b>\n\n✏️ Iltimos, ism va familiyangizni yozing:",
        reply_markup=remove_kb(),
        parse_mode="HTML",
    )
    await state.set_state(BrandStates.full_name)


@router.message(BrandStates.warning_ack)
async def brand_warning_not_acked(message: Message) -> None:
    await message.answer("Iltimos, pastdagi tugmani bosing.", reply_markup=continue_kb())


@router.message(BrandStates.full_name)
async def brand_full_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("Ism bo'sh bo'lmasligi kerak. Qayta yozing:")
        return
    await state.update_data(full_name=name)
    await message.answer(
        "📞 Iltimos, telefon raqamingizni jo'nating:",
        reply_markup=phone_request_kb(),
    )
    await state.set_state(BrandStates.phone)


@router.message(BrandStates.phone, F.contact)
async def brand_phone(message: Message, state: FSMContext) -> None:
    phone = message.contact.phone_number  # type: ignore[union-attr]
    await state.update_data(phone=phone)
    await message.answer(
        "🚗 Mashinangizning <b>rusumini (modelini)</b> yozing (masalan: Cobalt, Lacetti):",
        reply_markup=remove_kb(),
        parse_mode="HTML",
    )
    await state.set_state(BrandStates.car_model)


@router.message(BrandStates.phone)
async def brand_phone_fallback(message: Message) -> None:
    await message.answer(
        "Iltimos, telefon raqamingizni <b>knopka</b> orqali jo'nating:",
        reply_markup=phone_request_kb(),
        parse_mode="HTML",
    )


@router.message(BrandStates.car_model)
async def brand_car_model(message: Message, state: FSMContext) -> None:
    model = (message.text or "").strip()
    if not model:
        await message.answer("Rusum bo'sh bo'lmasligi kerak. Qayta yozing:")
        return
    await state.update_data(car_model=model)
    await message.answer(
        "📅 Mashinangizning <b>yilini</b> yozing (masalan: 2018):",
        parse_mode="HTML",
    )
    await state.set_state(BrandStates.car_year)


@router.message(BrandStates.car_year)
async def brand_car_year(message: Message, state: FSMContext) -> None:
    year = (message.text or "").strip()
    if not year:
        await message.answer("Yil bo'sh bo'lmasligi kerak. Qayta yozing:")
        return
    await state.update_data(car_year=year)
    await message.answer(
        "🎨 Mashinangizning <b>rangini</b> yozing (masalan: Oq, Qora, Kumush):",
        parse_mode="HTML",
    )
    await state.set_state(BrandStates.car_color)


@router.message(BrandStates.car_color)
async def brand_car_color(message: Message, state: FSMContext) -> None:
    color = (message.text or "").strip()
    if not color:
        await message.answer("Rang bo'sh bo'lmasligi kerak. Qayta yozing:")
        return
    await state.update_data(car_color=color)
    await message.answer(
        "🔢 Mashinangizning <b>davlat raqamini</b> yozing (masalan: <code>01A123BC</code>):",
        parse_mode="HTML",
    )
    await state.set_state(BrandStates.plate_number)


@router.message(BrandStates.plate_number)
async def brand_plate(message: Message, state: FSMContext, bot: Bot) -> None:
    plate = (message.text or "").strip().upper()
    if not plate:
        await message.answer("Davlat raqami bo'sh bo'lmasligi kerak. Qayta yozing:")
        return

    await state.update_data(plate_number=plate)
    data = await state.get_data()

    session: AsyncSession = get_session()
    try:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)  # type: ignore[union-attr]
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                telegram_id=message.from_user.id,  # type: ignore[union-attr]
                username=message.from_user.username,  # type: ignore[union-attr]
            )
            session.add(user)
            await session.flush()

        app = BrandApplication(
            user_id=user.id,
            full_name=data["full_name"],
            phone=data["phone"],
            promocode=data.get("promocode"),
            car_model=data["car_model"],
            car_year=data["car_year"],
            car_color=data["car_color"],
            plate_number=plate,
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
        "Brend arizangiz qabul qilindi. Janob Taxi admini tez orada aloqaga chiqadi.",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )

    await _notify_admin(bot, application_id, data, plate)


async def _notify_admin(bot: Bot, application_id: int, data: dict, plate: str) -> None:
    promo_line = (
        f"🎟 Promocode: <code>{data.get('promocode')}</code>"
        if data.get("promocode")
        else "🎟 Promocode: yo'q"
    )
    text = (
        "🎨 <b>Yangi BREND arizasi!</b>\n\n"
        f"👤 F.I.O: {data['full_name']}\n"
        f"📞 Telefon: {data['phone']}\n"
        f"🚗 Rusum: {data['car_model']}\n"
        f"📅 Yili: {data['car_year']}\n"
        f"🎨 Rang: {data['car_color']}\n"
        f"🚘 Davlat raqami: <code>{plate}</code>\n"
        f"{promo_line}"
    )
    for chat_id in await get_notification_chat_ids():
        try:
            summary_message = await bot.send_message(chat_id, text, parse_mode="HTML")
            await add_application_notification(
                "brand",
                application_id,
                chat_id,
                summary_message.message_id,
            )
        except (TelegramBadRequest, TelegramForbiddenError) as exc:
            logger.warning("Failed to notify chat %s: %s", chat_id, exc)
