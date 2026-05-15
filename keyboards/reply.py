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


def admin_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Admin qo'shish"), KeyboardButton(text="➖ Admin o'chirish")],
            [KeyboardButton(text="➕ Guruh qo'shish"), KeyboardButton(text="➖ Guruh o'chirish")],
            [KeyboardButton(text="📊 Promocode export"), KeyboardButton(text="🔄 Google Sheets sync")],
            [KeyboardButton(text="🔎 User qidirish"), KeyboardButton(text="🔗 Ariza xabari")],
            [KeyboardButton(text="📋 Ro'yxatlar"), KeyboardButton(text="📣 Hammaga xabar")],
            [KeyboardButton(text="🏠 Asosiy menyu")],
        ],
        resize_keyboard=True,
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
