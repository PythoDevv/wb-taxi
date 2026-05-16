from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database.users import get_or_create_user, set_user_promocode
from keyboards.reply import main_menu_kb, promo_question_kb
from states.forms import PromoStates

router = Router()

WELCOME_TEXT = (
    "🚕 <b>Janob Taxi</b> botiga xush kelibsiz!\n\n"
    "Quyidagi menyulardan birini tanlang:\n"
    "📝 <b>Ulanish uchun Ariza</b> — Haydovchilik uchun ariza"
    # "🎁 <b>Brend Ariza</b> — Mashinangizni brendlash uchun ariza"
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = await get_or_create_user(
        message.from_user.id,  # type: ignore[union-attr]
        message.from_user.username,  # type: ignore[union-attr]
    )
    if user.promocode_asked:
        await state.update_data(promocode=user.promocode)
        await _show_main_menu(message, state)
        return

    await message.answer(
        "🎟 Sizda <b>promocode</b> bormi?",
        reply_markup=promo_question_kb(),
        parse_mode="HTML",
    )
    await state.set_state(PromoStates.asking_promo)


@router.message(PromoStates.asking_promo)
async def promo_choice(message: Message, state: FSMContext) -> None:
    text = message.text or ""

    if text == "✅ Ha":
        await message.answer(
            "✏️ Iltimos, promocodeni yozing:",
            reply_markup=None,
        )
        await state.set_state(PromoStates.entering_promo)

    elif text == "🚫 Yo'q":
        await set_user_promocode(
            message.from_user.id,  # type: ignore[union-attr]
            message.from_user.username,  # type: ignore[union-attr]
            None,
        )
        await state.update_data(promocode=None)
        await _show_main_menu(message, state)

    else:
        await message.answer(
            "Iltimos, quyidagi tugmalardan birini tanlang.",
            reply_markup=promo_question_kb(),
        )


@router.message(PromoStates.entering_promo)
async def promo_entered(message: Message, state: FSMContext) -> None:
    code = (message.text or "").strip()
    if not code:
        await message.answer("Promocode bo'sh bo'lmasligi kerak. Qayta yozing:")
        return

    await set_user_promocode(
        message.from_user.id,  # type: ignore[union-attr]
        message.from_user.username,  # type: ignore[union-attr]
        code,
    )
    await state.update_data(promocode=code)
    await message.answer(f"✅ Promocode qabul qilindi: <code>{code}</code>", parse_mode="HTML")
    await _show_main_menu(message, state)


async def _show_main_menu(message: Message, state: FSMContext) -> None:
    await state.set_state(None)
    await message.answer(
        WELCOME_TEXT,
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )
