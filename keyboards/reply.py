from aiogram.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

# ── Main menu ────────────────────────────────────────────────────────────────

def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Ulanish uchun Ariza")],
            [KeyboardButton(text="🎁 Brend Ariza")],
        ],
        resize_keyboard=True,
    )


# ── Promo step ───────────────────────────────────────────────────────────────

def promo_question_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="✅ Ha, bor"),
                KeyboardButton(text="➡️ Davom etish"),
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


# ── Driver flow ──────────────────────────────────────────────────────────────

def phone_request_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Raqamni ulashish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def continue_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Davom etish")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
