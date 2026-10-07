from datetime import datetime

from sqlalchemy import CHAR, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import SmallInt, pg_enum, utcnow
from app.models.enums import UserRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(CHAR(60), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        pg_enum(UserRole, "user_role"), nullable=False, default=UserRole.buyer
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow)

    profile: Mapped["UserProfile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan", lazy="joined"
    )
    artworks: Mapped[list["Artwork"]] = relationship(  # noqa: F821
        back_populates="seller", cascade="all, delete-orphan", passive_deletes=True
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    full_name: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(20))
    city_id: Mapped[int | None] = mapped_column(
        SmallInt, ForeignKey("cities.id", ondelete="SET NULL")
    )

    user: Mapped[User] = relationship(back_populates="profile")
    city: Mapped["City | None"] = relationship(lazy="joined")  # noqa: F821
