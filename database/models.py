from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    promocode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    promocode_asked: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    applications: Mapped[list["Application"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class NotificationChat(Base):
    __tablename__ = "notification_chats"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ApplicationNotification(Base):
    __tablename__ = "application_notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_type: Mapped[str] = mapped_column(String(16), nullable=False)
    application_id: Mapped[int] = mapped_column(Integer, nullable=False)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    summary_message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PromptImage(Base):
    __tablename__ = "prompt_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    image_name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    file_id: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
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
    # selfie_id: Mapped[str] = mapped_column(String(256), nullable=False)
    # license_card_id: Mapped[str] = mapped_column(String(256), nullable=False)

    # car_photo_1_id: Mapped[str] = mapped_column(String(256), nullable=False)
    # car_photo_2_id: Mapped[str] = mapped_column(String(256), nullable=False)
    # car_photo_3_id: Mapped[str] = mapped_column(String(256), nullable=False)
    # car_photo_4_id: Mapped[str] = mapped_column(String(256), nullable=False)

    plate_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
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
