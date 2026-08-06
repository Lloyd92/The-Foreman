from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Person(Base):
    __tablename__ = "people"
    __table_args__ = (
        CheckConstraint(
            "length(trim(display_name)) > 0",
            name="ck_people_display_name_not_blank",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    display_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        index=True,
    )
    given_name: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        default="",
        server_default="",
    )
    family_name: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        default="",
        server_default="",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default="",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
