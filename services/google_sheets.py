import asyncio
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from config import (
    GOOGLE_SERVICE_ACCOUNT_FILE,
    GOOGLE_SERVICE_ACCOUNT_JSON,
    GOOGLE_SHEETS_SPREADSHEET_ID,
)
from database.reports import (
    APPLICATION_HEADERS,
    ReportRow,
    UserReportRow,
    get_application_report_rows,
    get_promocodes,
    get_statistics_rows,
    get_user_report_rows,
)

INVALID_SHEET_TITLE_CHARS = re.compile(r"[\[\]\*\?/\\:]")
MAX_SHEET_TITLE_LENGTH = 100

USER_HEADERS = [
    "telegram_id",
    "username",
    "created_at",
    "driver_applications",
    "brand_applications",
    "names",
    "phones",
    "promocodes",
]

STATISTICS_HEADERS = ["promocode", "driver_count", "brand_count", "total_count"]


@dataclass(slots=True)
class SheetsSyncResult:
    ok: bool
    message: str
    worksheet_count: int = 0


def google_sheets_configured() -> bool:
    has_credentials = bool(GOOGLE_SERVICE_ACCOUNT_FILE or GOOGLE_SERVICE_ACCOUNT_JSON)
    return bool(GOOGLE_SHEETS_SPREADSHEET_ID and has_credentials)


def sanitize_sheet_title(title: str) -> str:
    safe_title = INVALID_SHEET_TITLE_CHARS.sub("_", title).strip()
    if not safe_title:
        safe_title = "empty"
    return safe_title[:MAX_SHEET_TITLE_LENGTH]


def _format_dt(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.isoformat(sep=" ", timespec="seconds")


def application_rows_to_values(rows: list[ReportRow]) -> list[list[Any]]:
    values: list[list[Any]] = [APPLICATION_HEADERS]
    for row in rows:
        values.append(
            [
                row.application_type,
                row.application_id,
                row.telegram_id,
                row.username or "",
                _format_dt(row.user_created_at),
                row.full_name,
                row.phone,
                row.promocode or "",
                "bor" if row.passport_front else "yoq",
                "bor" if row.passport_back else "yoq",
                "bor" if row.license_front else "yoq",
                "bor" if row.license_back else "yoq",
                "bor" if row.texpassport_front else "yoq",
                "bor" if row.texpassport_back else "yoq",
                row.status,
                _format_dt(row.created_at),
                row.car_model or "",
                row.car_year or "",
                row.car_color or "",
            ]
        )
    return values


def user_rows_to_values(rows: list[UserReportRow]) -> list[list[Any]]:
    values: list[list[Any]] = [USER_HEADERS]
    for row in rows:
        values.append(
            [
                row.telegram_id,
                row.username or "",
                _format_dt(row.created_at),
                row.driver_applications,
                row.brand_applications,
                row.names,
                row.phones,
                row.promocodes,
            ]
        )
    return values


def statistics_rows_to_values(rows: list[list[str | int]]) -> list[list[Any]]:
    return [STATISTICS_HEADERS, *rows]


def _build_client() -> Any:
    import gspread

    if GOOGLE_SERVICE_ACCOUNT_JSON:
        credentials = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        return gspread.service_account_from_dict(credentials)

    return gspread.service_account(filename=GOOGLE_SERVICE_ACCOUNT_FILE)


def _sync_worksheet(spreadsheet: Any, title: str, values: list[list[Any]]) -> None:
    try:
        worksheet = spreadsheet.worksheet(title)
    except Exception:
        worksheet = spreadsheet.add_worksheet(
            title=title,
            rows=max(len(values), 10),
            cols=max(len(values[0]) if values else 1, 10),
        )

    worksheet.clear()
    if values:
        worksheet.update(values, value_input_option="USER_ENTERED")


def _sync_all_to_google(
    application_rows: list[ReportRow],
    user_rows: list[UserReportRow],
    statistics_rows: list[list[str | int]],
    promocode_rows: dict[str, list[ReportRow]],
) -> SheetsSyncResult:
    if not google_sheets_configured():
        return SheetsSyncResult(
            ok=False,
            message=(
                "Google Sheets sozlanmagan. GOOGLE_SHEETS_SPREADSHEET_ID va "
                "GOOGLE_SERVICE_ACCOUNT_FILE yoki GOOGLE_SERVICE_ACCOUNT_JSON kerak."
            ),
        )

    client = _build_client()
    spreadsheet = client.open_by_key(GOOGLE_SHEETS_SPREADSHEET_ID)

    worksheet_count = 0
    _sync_worksheet(spreadsheet, "Statistics", statistics_rows_to_values(statistics_rows))
    worksheet_count += 1

    _sync_worksheet(spreadsheet, "Users", user_rows_to_values(user_rows))
    worksheet_count += 1

    _sync_worksheet(spreadsheet, "All Applications", application_rows_to_values(application_rows))
    worksheet_count += 1

    for promocode, rows in promocode_rows.items():
        title = sanitize_sheet_title(f"promo_{promocode}")
        _sync_worksheet(spreadsheet, title, application_rows_to_values(rows))
        worksheet_count += 1

    return SheetsSyncResult(
        ok=True,
        message="Google Sheets sync tugadi.",
        worksheet_count=worksheet_count,
    )


async def sync_reports_to_google_sheets() -> SheetsSyncResult:
    application_rows = await get_application_report_rows()
    user_rows = await get_user_report_rows()
    statistics_rows = await get_statistics_rows()
    promocodes = await get_promocodes()
    promocode_rows = {
        promocode: await get_application_report_rows(promocode)
        for promocode in promocodes
    }

    try:
        return await asyncio.to_thread(
            _sync_all_to_google,
            application_rows,
            user_rows,
            statistics_rows,
            promocode_rows,
        )
    except Exception as exc:
        return SheetsSyncResult(
            ok=False,
            message=f"Google Sheets sync xato berdi: {exc}",
        )
