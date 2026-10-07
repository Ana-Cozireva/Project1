"""Аналитические (агрегирующие) эндпоинты для администратора (ToR, п. 4.1)."""
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, extract, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import require_admin
from app.models import (
    Artist,
    Artwork,
    ArtworkStatus,
    City,
    Conversation,
    Reservation,
    ReservationStatus,
    Style,
    Technique,
    User,
)
from app.models.base import utcnow
from app.schemas.analytics import GroupStat, MonthStat, Overview

router = APIRouter(
    prefix="/api/analytics", tags=["analytics"], dependencies=[Depends(require_admin)]
)

CENT = Decimal("0.01")


def _money(value) -> Decimal:
    return Decimal(value or 0).quantize(CENT)


def _group_stats(db: Session, model, fk_column, limit: int) -> list[GroupStat]:
    sold = Artwork.status == ArtworkStatus.sold
    count = func.count(Artwork.id)
    stmt = (
        select(
            model.id,
            model.name,
            count,
            func.coalesce(func.sum(case((sold, 1), else_=0)), 0),
            func.coalesce(func.avg(Artwork.price), 0),
            func.coalesce(func.sum(Artwork.price), 0),
            func.coalesce(func.sum(case((sold, Artwork.price), else_=0)), 0),
        )
        .select_from(model)
        .outerjoin(Artwork, fk_column == model.id)
        .group_by(model.id, model.name)
        .order_by(count.desc(), model.name)
        .limit(limit)
    )
    return [
        GroupStat(
            id=row[0], name=row[1], artworks_count=row[2], sold_count=int(row[3]),
            avg_price=_money(row[4]), total_value=_money(row[5]), sold_value=_money(row[6]),
        )
        for row in db.execute(stmt)
    ]


@router.get("/overview", response_model=Overview)
def overview(db: Session = Depends(get_db)):
    users_by_role = {r.value: n for r, n in db.execute(select(User.role, func.count()).group_by(User.role))}
    art_by_status = {s.value: n for s, n in db.execute(select(Artwork.status, func.count()).group_by(Artwork.status))}
    res_by_status = {s.value: n for s, n in db.execute(select(Reservation.status, func.count()).group_by(Reservation.status))}
    sold_value = db.scalar(select(func.sum(Artwork.price)).where(Artwork.status == ArtworkStatus.sold))
    avg_price = db.scalar(select(func.avg(Artwork.price)))
    return Overview(
        users_total=sum(users_by_role.values()),
        users_by_role={k: users_by_role.get(k, 0) for k in ("buyer", "seller", "admin")},
        artworks_total=sum(art_by_status.values()),
        artworks_by_status={k: art_by_status.get(k, 0) for k in ("available", "reserved", "sold")},
        reservations_by_status={k: res_by_status.get(k, 0) for k in ("pending", "confirmed", "cancelled")},
        conversations_total=db.scalar(select(func.count(Conversation.id))) or 0,
        sold_value=_money(sold_value),
        avg_price=_money(avg_price),
    )


@router.get("/by-artist", response_model=list[GroupStat])
def by_artist(limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    return _group_stats(db, Artist, Artwork.artist_id, limit)


@router.get("/by-style", response_model=list[GroupStat])
def by_style(limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    return _group_stats(db, Style, Artwork.style_id, limit)


@router.get("/by-technique", response_model=list[GroupStat])
def by_technique(limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    return _group_stats(db, Technique, Artwork.technique_id, limit)


@router.get("/by-city", response_model=list[GroupStat])
def by_city(limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    return _group_stats(db, City, Artwork.city_id, limit)


@router.get("/by-month", response_model=list[MonthStat])
def by_month(months: int = Query(12, ge=1, le=60), db: Session = Depends(get_db)):
    now = utcnow()
    keys: list[str] = []
    year, month = now.year, now.month
    for _ in range(months):
        keys.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    keys.reverse()
    stats = {k: dict(listed=0, reservations=0, sold=0, value=Decimal(0)) for k in keys}

    def key(y, m) -> str:
        return f"{int(y):04d}-{int(m):02d}"

    def ym(column):
        return extract("year", column).label("y"), extract("month", column).label("m")

    y, m = ym(Artwork.created_at)
    for yy, mm, n in db.execute(select(y, m, func.count()).group_by(y, m)):
        if key(yy, mm) in stats:
            stats[key(yy, mm)]["listed"] = n

    y, m = ym(Reservation.created_at)
    for yy, mm, n in db.execute(select(y, m, func.count()).group_by(y, m)):
        if key(yy, mm) in stats:
            stats[key(yy, mm)]["reservations"] = n

    y, m = ym(Reservation.confirmed_at)
    sold_rows = db.execute(
        select(y, m, func.count(), func.coalesce(func.sum(Artwork.price), 0))
        .join(Artwork, Artwork.id == Reservation.artwork_id)
        .where(Reservation.status == ReservationStatus.confirmed)
        .group_by(y, m)
    )
    for yy, mm, n, value in sold_rows:
        if key(yy, mm) in stats:
            stats[key(yy, mm)]["sold"] = n
            stats[key(yy, mm)]["value"] = _money(value)

    return [
        MonthStat(
            month=k, listed_count=v["listed"], reservations_count=v["reservations"],
            sold_count=v["sold"], sold_value=_money(v["value"]),
        )
        for k, v in stats.items()
    ]
