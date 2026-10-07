from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import SmallInt, pg_enum, utcnow
from app.models.enums import ArtworkCondition, ArtworkStatus
from app.models.reference import Artist, City, Style, Technique
from app.models.user import User


class Artwork(Base):
    __tablename__ = "artworks"
    __table_args__ = (
        CheckConstraint("price > 0", name="ck_artworks_price_positive"),
        Index("ix_artworks_status", "status"),
        Index("ix_artworks_price", "price"),
        Index("ix_artworks_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    seller_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    artist_id: Mapped[int] = mapped_column(
        ForeignKey("artists.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    style_id: Mapped[int | None] = mapped_column(
        SmallInt, ForeignKey("styles.id", ondelete="SET NULL"), index=True
    )
    technique_id: Mapped[int | None] = mapped_column(
        SmallInt, ForeignKey("techniques.id", ondelete="SET NULL"), index=True
    )
    city_id: Mapped[int | None] = mapped_column(
        SmallInt, ForeignKey("cities.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    year_created: Mapped[int | None] = mapped_column(SmallInteger)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    condition: Mapped[ArtworkCondition | None] = mapped_column(
        pg_enum(ArtworkCondition, "artwork_condition")
    )
    status: Mapped[ArtworkStatus] = mapped_column(
        pg_enum(ArtworkStatus, "artwork_status"),
        nullable=False,
        default=ArtworkStatus.available,
    )
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(default=None, onupdate=utcnow)

    seller: Mapped[User] = relationship(back_populates="artworks", lazy="joined")
    artist: Mapped[Artist] = relationship(lazy="joined")
    style: Mapped[Style | None] = relationship(lazy="joined")
    technique: Mapped[Technique | None] = relationship(lazy="joined")
    city: Mapped[City | None] = relationship(lazy="joined")
    details: Mapped["ArtworkDetail | None"] = relationship(
        back_populates="artwork", uselist=False, cascade="all, delete-orphan", lazy="joined"
    )
    photos: Mapped[list["ArtworkPhoto"]] = relationship(
        back_populates="artwork",
        cascade="all, delete-orphan",
        order_by="ArtworkPhoto.position, ArtworkPhoto.id",
        lazy="selectin",
    )


class ArtworkDetail(Base):
    __tablename__ = "artwork_details"

    artwork_id: Mapped[int] = mapped_column(
        ForeignKey("artworks.id", ondelete="CASCADE"), primary_key=True
    )
    width_cm: Mapped[Decimal | None] = mapped_column(Numeric(6, 1))
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(6, 1))
    depth_cm: Mapped[Decimal | None] = mapped_column(Numeric(6, 1))
    description: Mapped[str | None] = mapped_column(String(4000))

    artwork: Mapped[Artwork] = relationship(back_populates="details")


class ArtworkPhoto(Base):
    __tablename__ = "artwork_photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    artwork_id: Mapped[int] = mapped_column(
        ForeignKey("artworks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    position: Mapped[int] = mapped_column(SmallInt, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow)

    artwork: Mapped[Artwork] = relationship(back_populates="photos")
