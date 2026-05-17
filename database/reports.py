from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select

from database.db import get_session
from database.models import (
    Application,
    ApplicationNotification,
    BrandApplication,
    User,
)

APPLICATION_HEADERS = [
    "application_type",
    "application_id",
    "telegram_id",
    "username",
    "user_created_at",
    "full_name",
    "phone",
    "promocode",
    "plate_number",
    "passport_front",
    "passport_back",
    "license_front",
    "license_back",
    "texpassport_front",
    "texpassport_back",
    "status",
    "created_at",
    "car_model",
    "car_year",
    "car_color",
]


@dataclass(slots=True)
class ReportRow:
    application_type: str
    application_id: int
    telegram_id: int
    username: str | None
    user_created_at: datetime | None
    full_name: str
    phone: str
    promocode: str | None
    plate_number: str | None
    status: str
    created_at: datetime | None
    passport_front: bool = False
    passport_back: bool = False
    license_front: bool = False
    license_back: bool = False
    texpassport_front: bool = False
    texpassport_back: bool = False
    car_model: str | None = None
    car_year: str | None = None
    car_color: str | None = None


@dataclass(slots=True)
class UserReportRow:
    telegram_id: int
    username: str | None
    created_at: datetime | None
    driver_applications: int
    brand_applications: int
    names: str
    phones: str
    promocodes: str


async def get_application_report_rows(promocode: str | None = None) -> list[ReportRow]:
    session = get_session()
    try:
        driver_stmt = (
            select(Application, User)
            .join(User, Application.user_id == User.id)
            .order_by(Application.created_at.desc(), Application.id.desc())
        )
        brand_stmt = (
            select(BrandApplication, User)
            .join(User, BrandApplication.user_id == User.id)
            .order_by(BrandApplication.created_at.desc(), BrandApplication.id.desc())
        )

        if promocode is not None:
            driver_stmt = driver_stmt.where(Application.promocode == promocode)
            brand_stmt = brand_stmt.where(BrandApplication.promocode == promocode)

        rows: list[ReportRow] = []
        driver_result = await session.execute(driver_stmt)
        for app, user in driver_result.all():
            rows.append(
                ReportRow(
                    application_type="driver",
                    application_id=app.id,
                    telegram_id=user.telegram_id,
                    username=user.username,
                    user_created_at=user.created_at,
                    full_name=app.full_name,
                    phone=app.phone,
                    promocode=app.promocode,
                    plate_number=app.plate_number,
                    passport_front=bool(app.passport_front_id),
                    passport_back=bool(app.passport_back_id),
                    license_front=bool(app.license_front_id),
                    license_back=bool(app.license_back_id),
                    texpassport_front=bool(app.texpassport_front_id),
                    texpassport_back=bool(app.texpassport_back_id),
                    status=app.status,
                    created_at=app.created_at,
                )
            )

        brand_result = await session.execute(brand_stmt)
        for app, user in brand_result.all():
            rows.append(
                ReportRow(
                    application_type="brand",
                    application_id=app.id,
                    telegram_id=user.telegram_id,
                    username=user.username,
                    user_created_at=user.created_at,
                    full_name=app.full_name,
                    phone=app.phone,
                    promocode=app.promocode,
                    plate_number=app.plate_number,
                    status=app.status,
                    created_at=app.created_at,
                    car_model=app.car_model,
                    car_year=app.car_year,
                    car_color=app.car_color,
                )
            )

        rows.sort(
            key=lambda row: (
                row.created_at.timestamp() if row.created_at else 0,
                row.application_id,
            ),
            reverse=True,
        )
        return rows
    finally:
        await session.close()


async def get_user_report_rows() -> list[UserReportRow]:
    session = get_session()
    try:
        users_result = await session.execute(select(User).order_by(User.id))
        users = list(users_result.scalars().all())
        rows: list[UserReportRow] = []

        for user in users:
            driver_result = await session.execute(
                select(Application).where(Application.user_id == user.id)
            )
            brand_result = await session.execute(
                select(BrandApplication).where(BrandApplication.user_id == user.id)
            )
            driver_apps = list(driver_result.scalars().all())
            brand_apps = list(brand_result.scalars().all())
            all_apps = [*driver_apps, *brand_apps]

            rows.append(
                UserReportRow(
                    telegram_id=user.telegram_id,
                    username=user.username,
                    created_at=user.created_at,
                    driver_applications=len(driver_apps),
                    brand_applications=len(brand_apps),
                    names=", ".join(sorted({app.full_name for app in all_apps})),
                    phones=", ".join(sorted({app.phone for app in all_apps})),
                    promocodes=", ".join(
                        sorted({app.promocode for app in all_apps if app.promocode})
                    ),
                )
            )

        return rows
    finally:
        await session.close()


async def get_user_details(telegram_id: int) -> tuple[User | None, list[ReportRow]]:
    session = get_session()
    try:
        user_result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = user_result.scalar_one_or_none()
        if user is None:
            return None, []
    finally:
        await session.close()

    rows = [
        row
        for row in await get_application_report_rows()
        if row.telegram_id == telegram_id
    ]
    return user, rows


async def get_promocodes() -> list[str]:
    session = get_session()
    try:
        driver_result = await session.execute(
            select(Application.promocode)
            .where(Application.promocode.is_not(None))
            .where(Application.promocode != "")
        )
        brand_result = await session.execute(
            select(BrandApplication.promocode)
            .where(BrandApplication.promocode.is_not(None))
            .where(BrandApplication.promocode != "")
        )
        promocodes = {*driver_result.scalars().all(), *brand_result.scalars().all()}
        return sorted(promocodes)
    finally:
        await session.close()


async def get_statistics_rows() -> list[list[str | int]]:
    session = get_session()
    try:
        driver_result = await session.execute(
            select(Application.promocode, func.count(Application.id))
            .where(Application.promocode.is_not(None))
            .where(Application.promocode != "")
            .group_by(Application.promocode)
        )
        brand_result = await session.execute(
            select(BrandApplication.promocode, func.count(BrandApplication.id))
            .where(BrandApplication.promocode.is_not(None))
            .where(BrandApplication.promocode != "")
            .group_by(BrandApplication.promocode)
        )
        stats: dict[str, dict[str, int]] = {}
        for promocode, count in driver_result.all():
            stats.setdefault(promocode, {"driver": 0, "brand": 0})["driver"] = count
        for promocode, count in brand_result.all():
            stats.setdefault(promocode, {"driver": 0, "brand": 0})["brand"] = count

        rows: list[list[str | int]] = []
        for promocode in sorted(stats):
            driver_count = stats[promocode]["driver"]
            brand_count = stats[promocode]["brand"]
            rows.append([promocode, driver_count, brand_count, driver_count + brand_count])
        return rows
    finally:
        await session.close()


async def add_application_notification(
    application_type: str,
    application_id: int,
    chat_id: int,
    summary_message_id: int,
) -> None:
    session = get_session()
    try:
        session.add(
            ApplicationNotification(
                application_type=application_type,
                application_id=application_id,
                chat_id=chat_id,
                summary_message_id=summary_message_id,
            )
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_application_notifications(
    application_type: str,
    application_id: int,
) -> list[ApplicationNotification]:
    session = get_session()
    try:
        result = await session.execute(
            select(ApplicationNotification)
            .where(ApplicationNotification.application_type == application_type)
            .where(ApplicationNotification.application_id == application_id)
            .order_by(ApplicationNotification.id)
        )
        return list(result.scalars().all())
    finally:
        await session.close()
