from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import BigInt, pg_enum, utcnow
from app.models.enums import ReservationStatus
from app.models.artwork import Artwork
from app.models.user import User


class Favorite(Base):
    __tablename__ = "favorites"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    artwork_id: Mapped[int] = mapped_column(
        ForeignKey("artworks.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow)

    artwork: Mapped[Artwork] = relationship(lazy="joined")


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("artwork_id", "buyer_id", name="uq_conversation_artwork_buyer"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    artwork_id: Mapped[int] = mapped_column(
        ForeignKey("artworks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    buyer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow)

    artwork: Mapped[Artwork] = relationship(lazy="joined")
    buyer: Mapped[User] = relationship(lazy="joined")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.id",
        lazy="select",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(String(2000), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        # Не более одной «живой» (pending/confirmed) брони на произведение —
        # дополнительная защита от гонок на уровне БД.
        Index(
            "uq_reservations_active_artwork",
            "artwork_id",
            unique=True,
            postgresql_where=text("status IN ('pending', 'confirmed')"),
            sqlite_where=text("status IN ('pending', 'confirmed')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    artwork_id: Mapped[int] = mapped_column(
        ForeignKey("artworks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    buyer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ReservationStatus] = mapped_column(
        pg_enum(ReservationStatus, "reservation_status"),
        nullable=False,
        default=ReservationStatus.pending,
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow)
    confirmed_at: Mapped[datetime | None] = mapped_column(default=None)
    cancelled_at: Mapped[datetime | None] = mapped_column(default=None)

    artwork: Mapped[Artwork] = relationship(lazy="joined")
    buyer: Mapped[User] = relationship(lazy="joined")
