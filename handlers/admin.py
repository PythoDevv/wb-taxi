import asyncio
from io import BytesIO

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message

from database.admin import (
    add_admin,
    add_notification_chat,
    is_admin,
    list_admins,
    list_notification_chats,
    list_user_chat_ids,
    remove_admin,
    remove_notification_chat,
)
from database.reports import (
    APPLICATION_HEADERS,
    ReportRow,
    get_application_notifications,
    get_application_report_rows,
    get_user_details,
)
from keyboards.reply import admin_menu_kb, cancel_kb, main_menu_kb
from services.google_sheets import sync_reports_to_google_sheets
from states.forms import AdminStates

router = Router()


def _parse_telegram_id(text: str | None) -> int | None:
    value = (text or "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _parse_application_ref(text: str | None) -> tuple[str, int] | None:
    value = (text or "").strip().lower()
    if ":" not in value:
        return None
    app_type, app_id_text = value.split(":", 1)
    if app_type not in {"driver", "brand"}:
        return None
    try:
        return app_type, int(app_id_text.strip())
    except ValueError:
        return None


def _format_dt(value) -> str:
    if value is None:
        return ""
    return value.isoformat(sep=" ", timespec="seconds")


def _report_row_to_csv_row(row: ReportRow) -> list[str | int]:
    return [
        row.application_type,
        row.application_id,
        row.telegram_id,
        row.username or "",
        _format_dt(row.user_created_at),
        row.full_name,
        row.phone,
        row.promocode or "",
        row.plate_number or "",
        row.status,
        _format_dt(row.created_at),
        row.car_model or "",
        row.car_year or "",
        row.car_color or "",
    ]


def _build_excel_file(rows: list[ReportRow], filename: str) -> BufferedInputFile:
    from openpyxl import Workbook

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Applications"
    worksheet.append(APPLICATION_HEADERS)
    for row in rows:
        worksheet.append(_report_row_to_csv_row(row))

    for column_cells in worksheet.columns:
        max_length = max(len(str(cell.value or "")) for cell in column_cells)
        worksheet.column_dimensions[column_cells[0].column_letter].width = min(
            max(max_length + 2, 12),
            40,
        )

    buffer = BytesIO()
    workbook.save(buffer)
    return BufferedInputFile(
        buffer.getvalue(),
        filename=filename,
    )


def _telegram_message_link(chat_id: int, message_id: int) -> str | None:
    chat_id_text = str(chat_id)
    if chat_id_text.startswith("-100"):
        return f"https://t.me/c/{chat_id_text[4:]}/{message_id}"
    return None


async def _is_current_user_admin(message: Message) -> bool:
    if message.from_user is None:
        return False
    return await is_admin(message.from_user.id)


async def _deny_if_not_admin(message: Message) -> bool:
    if await _is_current_user_admin(message):
        return False
    await message.answer("Bu bo'lim faqat adminlar uchun.")
    return True


@router.message(Command("admin"))
async def admin_start(message: Message, state: FSMContext) -> None:
    if await _deny_if_not_admin(message):
        return
    await state.clear()
    await message.answer("Admin bo'lim:", reply_markup=admin_menu_kb())


@router.message(F.text == "🏠 Asosiy menyu")
async def back_to_main_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Asosiy menyu:", reply_markup=main_menu_kb())


@router.message(StateFilter(*AdminStates.__all_states__), F.text == "❌ Bekor qilish")
async def cancel_admin_action(message: Message, state: FSMContext) -> None:
    if await _deny_if_not_admin(message):
        return
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=admin_menu_kb())


@router.message(F.text == "➕ Admin qo'shish")
async def add_admin_start(message: Message, state: FSMContext) -> None:
    if await _deny_if_not_admin(message):
        return
    await message.answer("Qo'shiladigan admin Telegram ID sini yuboring:", reply_markup=cancel_kb())
    await state.set_state(AdminStates.adding_admin)


@router.message(AdminStates.adding_admin)
async def add_admin_finish(message: Message, state: FSMContext) -> None:
    if await _deny_if_not_admin(message):
        return
    telegram_id = _parse_telegram_id(message.text)
    if telegram_id is None:
        await message.answer("Telegram ID faqat raqam bo'lishi kerak. Qayta yuboring:")
        return

    created = await add_admin(telegram_id)
    text = "Admin qo'shildi." if created else "Bu admin allaqachon mavjud."
    await state.clear()
    await message.answer(text, reply_markup=admin_menu_kb())


@router.message(F.text == "➖ Admin o'chirish")
async def remove_admin_start(message: Message, state: FSMContext) -> None:
    if await _deny_if_not_admin(message):
        return
    await message.answer("O'chiriladigan admin Telegram ID sini yuboring:", reply_markup=cancel_kb())
    await state.set_state(AdminStates.removing_admin)


@router.message(AdminStates.removing_admin)
async def remove_admin_finish(message: Message, state: FSMContext) -> None:
    if await _deny_if_not_admin(message):
        return
    telegram_id = _parse_telegram_id(message.text)
    if telegram_id is None:
        await message.answer("Telegram ID faqat raqam bo'lishi kerak. Qayta yuboring:")
        return

    removed = await remove_admin(telegram_id)
    text = (
        "Admin o'chirildi."
        if removed
        else "Admin topilmadi yoki oxirgi adminni o'chirib bo'lmaydi."
    )
    await state.clear()
    await message.answer(text, reply_markup=admin_menu_kb())


@router.message(F.text == "➕ Guruh qo'shish")
async def add_group_start(message: Message, state: FSMContext) -> None:
    if await _deny_if_not_admin(message):
        return
    await message.answer(
        "Arizalar yuboriladigan guruh chat ID sini yuboring.\n"
        "Masalan: <code>-1001234567890</code>",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.adding_notification_chat)


@router.message(AdminStates.adding_notification_chat)
async def add_group_finish(message: Message, state: FSMContext) -> None:
    if await _deny_if_not_admin(message):
        return
    chat_id = _parse_telegram_id(message.text)
    if chat_id is None:
        await message.answer("Chat ID faqat raqam bo'lishi kerak. Qayta yuboring:")
        return
    if chat_id >= 0:
        await message.answer(
            "Bu yerga faqat guruh ID qo'shiladi. Guruh ID odatda <code>-100...</code> "
            "ko'rinishida bo'ladi.",
            parse_mode="HTML",
        )
        return

    title = None
    if message.chat.type in {"group", "supergroup"}:
        title = message.chat.title

    created = await add_notification_chat(chat_id, title=title)
    text = "Guruh qo'shildi." if created else "Bu guruh allaqachon mavjud."
    await state.clear()
    await message.answer(text, reply_markup=admin_menu_kb())


@router.message(F.text == "➖ Guruh o'chirish")
async def remove_group_start(message: Message, state: FSMContext) -> None:
    if await _deny_if_not_admin(message):
        return
    await message.answer("O'chiriladigan guruh chat ID sini yuboring:", reply_markup=cancel_kb())
    await state.set_state(AdminStates.removing_notification_chat)


@router.message(AdminStates.removing_notification_chat)
async def remove_group_finish(message: Message, state: FSMContext) -> None:
    if await _deny_if_not_admin(message):
        return
    chat_id = _parse_telegram_id(message.text)
    if chat_id is None:
        await message.answer("Chat ID faqat raqam bo'lishi kerak. Qayta yuboring:")
        return

    removed = await remove_notification_chat(chat_id)
    text = "Guruh o'chirildi." if removed else "Guruh topilmadi."
    await state.clear()
    await message.answer(text, reply_markup=admin_menu_kb())


@router.message(F.text == "📋 Ro'yxatlar")
async def show_lists(message: Message) -> None:
    if await _deny_if_not_admin(message):
        return

    admins = await list_admins()
    chats = await list_notification_chats()

    admin_lines = "\n".join(f"- <code>{telegram_id}</code>" for telegram_id in admins)
    if not admin_lines:
        admin_lines = "- yo'q"

    chat_lines = "\n".join(
        f"- <code>{chat.chat_id}</code>{f' — {chat.title}' if chat.title else ''}"
        for chat in chats
    )
    if not chat_lines:
        chat_lines = "- yo'q"

    await message.answer(
        "<b>Adminlar:</b>\n"
        f"{admin_lines}\n\n"
        "<b>Ariza guruhlari:</b>\n"
        f"{chat_lines}",
        parse_mode="HTML",
        reply_markup=admin_menu_kb(),
    )


@router.message(F.text == "📣 Hammaga xabar")
async def broadcast_start(message: Message, state: FSMContext) -> None:
    if await _deny_if_not_admin(message):
        return
    await message.answer(
        "Yuboriladigan tayyor postni tashlang. Bot uni userlarga copy qilib yuboradi.",
        reply_markup=cancel_kb(),
    )
    await state.set_state(AdminStates.waiting_broadcast_post)


@router.message(F.text == "📊 Promocode export")
async def promocode_export_start(message: Message, state: FSMContext) -> None:
    if await _deny_if_not_admin(message):
        return
    await message.answer("Export qilinadigan promocodeni yuboring:", reply_markup=cancel_kb())
    await state.set_state(AdminStates.exporting_promocode)


@router.message(AdminStates.exporting_promocode)
async def promocode_export_finish(message: Message, state: FSMContext) -> None:
    if await _deny_if_not_admin(message):
        return

    promocode = (message.text or "").strip()
    if not promocode:
        await message.answer("Promocode bo'sh bo'lmasligi kerak. Qayta yuboring:")
        return

    rows = await get_application_report_rows(promocode)
    await state.clear()
    if not rows:
        await message.answer("Bu promocode bo'yicha ariza topilmadi.", reply_markup=admin_menu_kb())
        return

    safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in promocode)
    excel_file = _build_excel_file(rows, f"promocode_{safe_name}.xlsx")
    await message.answer_document(
        excel_file,
        caption=f"Promocode: {promocode}\nArizalar soni: {len(rows)}",
        reply_markup=admin_menu_kb(),
    )


@router.message(F.text == "🔎 User qidirish")
async def user_lookup_start(message: Message, state: FSMContext) -> None:
    if await _deny_if_not_admin(message):
        return
    await message.answer("User Telegram ID sini yuboring:", reply_markup=cancel_kb())
    await state.set_state(AdminStates.searching_user)


@router.message(AdminStates.searching_user)
async def user_lookup_finish(message: Message, state: FSMContext) -> None:
    if await _deny_if_not_admin(message):
        return

    telegram_id = _parse_telegram_id(message.text)
    if telegram_id is None:
        await message.answer("Telegram ID faqat raqam bo'lishi kerak. Qayta yuboring:")
        return

    user, rows = await get_user_details(telegram_id)
    await state.clear()
    if user is None:
        await message.answer("User topilmadi.", reply_markup=admin_menu_kb())
        return

    lines = [
        "<b>User ma'lumotlari</b>",
        f"Telegram ID: <code>{user.telegram_id}</code>",
        f"Username: @{user.username}" if user.username else "Username: yo'q",
        f"Ro'yxatga olingan: {_format_dt(user.created_at)}",
        "",
        "<b>Arizalar:</b>",
    ]
    if rows:
        for row in rows[:20]:
            lines.append(
                f"- {row.application_type}:{row.application_id} | "
                f"{row.full_name} | {row.phone} | promo: {row.promocode or 'yoq'} | "
                f"raqam: {row.plate_number or 'yoq'}"
            )
        if len(rows) > 20:
            lines.append(f"... yana {len(rows) - 20} ta ariza bor")
    else:
        lines.append("- ariza yo'q")

    await message.answer(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=admin_menu_kb(),
    )


@router.message(F.text == "🔗 Ariza xabari")
async def application_message_lookup_start(message: Message, state: FSMContext) -> None:
    if await _deny_if_not_admin(message):
        return
    await message.answer(
        "Ariza turini va ID sini yuboring.\nMasalan: <code>driver:12</code> yoki <code>brand:5</code>",
        reply_markup=cancel_kb(),
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.searching_application_message)


@router.message(AdminStates.searching_application_message)
async def application_message_lookup_finish(message: Message, state: FSMContext) -> None:
    if await _deny_if_not_admin(message):
        return

    app_ref = _parse_application_ref(message.text)
    if app_ref is None:
        await message.answer("Format noto'g'ri. Masalan: driver:12 yoki brand:5")
        return

    app_type, app_id = app_ref
    notifications = await get_application_notifications(app_type, app_id)
    await state.clear()
    if not notifications:
        await message.answer(
            "Bu ariza bo'yicha saqlangan guruh xabari topilmadi. "
            "Eski arizalarda message_id saqlanmagan bo'lishi mumkin.",
            reply_markup=admin_menu_kb(),
        )
        return

    lines = [f"<b>{app_type}:{app_id}</b> guruh xabarlari:"]
    for item in notifications:
        link = _telegram_message_link(item.chat_id, item.summary_message_id)
        if link:
            lines.append(
                f"- chat: <code>{item.chat_id}</code>, message: <code>{item.summary_message_id}</code>, "
                f"<a href=\"{link}\">ochish</a>"
            )
        else:
            lines.append(
                f"- chat: <code>{item.chat_id}</code>, message: <code>{item.summary_message_id}</code>"
            )

    await message.answer(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=admin_menu_kb(),
        disable_web_page_preview=True,
    )


@router.message(F.text == "🔄 Google Sheets sync")
async def google_sheets_sync(message: Message) -> None:
    if await _deny_if_not_admin(message):
        return

    progress_message = await message.answer("Google Sheets sync boshlandi...")
    result = await sync_reports_to_google_sheets()
    if result.ok:
        await progress_message.edit_text(
            f"{result.message}\nWorksheetlar: {result.worksheet_count}"
        )
    else:
        await progress_message.edit_text(result.message)


@router.message(AdminStates.waiting_broadcast_post)
async def broadcast_finish(message: Message, state: FSMContext, bot: Bot) -> None:
    if await _deny_if_not_admin(message):
        return

    user_ids = await list_user_chat_ids()
    sent = 0
    failed = 0

    progress_message = await message.answer(
        f"Broadcast boshlandi. Userlar soni: {len(user_ids)}"
    )

    for chat_id in user_ids:
        try:
            await bot.copy_message(
                chat_id=chat_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
            )
            sent += 1
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            try:
                await bot.copy_message(
                    chat_id=chat_id,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id,
                )
                sent += 1
            except (TelegramBadRequest, TelegramForbiddenError):
                failed += 1
        except (TelegramBadRequest, TelegramForbiddenError):
            failed += 1

        await asyncio.sleep(0.03)

    await state.clear()
    await progress_message.edit_text(
        f"Broadcast tugadi.\nYuborildi: {sent}\nXato: {failed}"
    )
    await message.answer("Admin bo'lim:", reply_markup=admin_menu_kb())
