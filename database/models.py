from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    applications: Mapped[list["Application"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    promocode: Mapped[str | None] = mapped_column(String(64), nullable=True)

    passport_front_id: Mapped[str] = mapped_column(String(256), nullable=False)
    passport_back_id: Mapped[str] = mapped_column(String(256), nullable=False)
    license_front_id: Mapped[str] = mapped_column(String(256), nullable=False)
    license_back_id: Mapped[str] = mapped_column(String(256), nullable=False)
    texpassport_front_id: Mapped[str] = mapped_column(String(256), nullable=False)
    texpassport_back_id: Mapped[str] = mapped_column(String(256), nullable=False)
    selfie_id: Mapped[str] = mapped_column(String(256), nullable=False)
    license_card_id: Mapped[str] = mapped_column(String(256), nullable=False)

    car_photo_1_id: Mapped[str] = mapped_column(String(256), nullable=False)
    car_photo_2_id: Mapped[str] = mapped_column(String(256), nullable=False)
    car_photo_3_id: Mapped[str] = mapped_column(String(256), nullable=False)
    car_photo_4_id: Mapped[str] = mapped_column(String(256), nullable=False)

    plate_number: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="new", server_default="new")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="applications")


class BrandApplication(Base):
    __tablename__ = "brand_applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    promocode: Mapped[str | None] = mapped_column(String(64), nullable=True)

    car_model: Mapped[str] = mapped_column(String(128), nullable=False)
    car_year: Mapped[str] = mapped_column(String(16), nullable=False)
    car_color: Mapped[str] = mapped_column(String(64), nullable=False)
    plate_number: Mapped[str] = mapped_column(String(32), nullable=False)

    status: Mapped[str] = mapped_column(String(32), default="new", server_default="new")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
