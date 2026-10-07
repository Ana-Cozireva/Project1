"""Транзакционный процесс бронирования: резервирование → подтверждение / отмена.

Все переходы состояния берут блокировку строки произведения (SELECT ... FOR UPDATE)
в одном и том же порядке (сначала artworks), поэтому два покупателя не могут забронировать
одно произведение одновременно, а взаимоблокировки исключены. Дополнительно в БД есть
частичный уникальный индекс: не более одной pending/confirmed брони на произведение.
"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user
from app.models import Artwork, ArtworkStatus, Reservation, ReservationStatus, User, UserRole
from app.models.base import utcnow
from app.schemas.common import Page
from app.schemas.social import ReservationCreate, ReservationOut
from app.services import get_artwork_or_404, paginate, to_card, user_short

router = APIRouter(prefix="/api/reservations", tags=["reservations"])


def _out(r: Reservation) -> ReservationOut:
    return ReservationOut(
        id=r.id,
        status=r.status,
        created_at=r.created_at,
        confirmed_at=r.confirmed_at,
        cancelled_at=r.cancelled_at,
        artwork=to_card(r.artwork),
        buyer=user_short(r.buyer),
        seller=user_short(r.artwork.seller),
    )


def _load_locked(db: Session, reservation_id: int) -> tuple[Reservation, Artwork]:
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        raise HTTPException(404, "Бронь не найдена")
    artwork = get_artwork_or_404(db, reservation.artwork_id, lock=True)  # блокировка
    db.refresh(reservation)  # перечитываем статус уже под блокировкой
    return reservation, artwork


@router.post("", response_model=ReservationOut, status_code=201, summary="Забронировать произведение")
def create_reservation(
    data: ReservationCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    artwork = get_artwork_or_404(db, data.artwork_id, lock=True)
    if artwork.seller_id == user.id:
        raise HTTPException(400, "Нельзя бронировать собственное произведение")
    if artwork.status != ArtworkStatus.available:
        raise HTTPException(409, "Произведение уже забронировано или продано")

    reservation = Reservation(artwork_id=artwork.id, buyer_id=user.id, status=ReservationStatus.pending)
    artwork.status = ArtworkStatus.reserved
    db.add(reservation)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Произведение уже забронировано другим покупателем")
    db.expire_all()
    return _out(db.get(Reservation, reservation.id))


@router.get("", response_model=Page[ReservationOut])
def list_reservations(
    as_: Literal["buyer", "seller", "all"] = Query("buyer", alias="as", description="buyer — мои брони, seller — брони на мои объявления, all — все (админ)"),
    status: ReservationStatus | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Reservation).join(Artwork, Artwork.id == Reservation.artwork_id)
    if as_ == "buyer":
        stmt = stmt.where(Reservation.buyer_id == user.id)
    elif as_ == "seller":
        stmt = stmt.where(Artwork.seller_id == user.id)
    elif user.role != UserRole.admin:
        raise HTTPException(403, "Только администратор может просматривать все брони")
    if status:
        stmt = stmt.where(Reservation.status == status)
    stmt = stmt.order_by(Reservation.created_at.desc(), Reservation.id.desc())
    items, total, pages = paginate(db, stmt, page, page_size)
    return Page(items=[_out(r) for r in items], total=total, page=page, page_size=page_size, pages=pages)


@router.post("/{reservation_id}/confirm", response_model=ReservationOut, summary="Подтвердить бронь (продавец)")
def confirm_reservation(
    reservation_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    reservation, artwork = _load_locked(db, reservation_id)
    if user.role != UserRole.admin and artwork.seller_id != user.id:
        raise HTTPException(403, "Подтвердить бронь может только продавец произведения")
    if reservation.status != ReservationStatus.pending:
        raise HTTPException(409, "Подтвердить можно только бронь в статусе «ожидает»")
    reservation.status = ReservationStatus.confirmed
    reservation.confirmed_at = utcnow()
    artwork.status = ArtworkStatus.sold
    db.commit()
    db.expire_all()
    return _out(db.get(Reservation, reservation_id))


@router.post("/{reservation_id}/cancel", response_model=ReservationOut, summary="Отменить бронь (покупатель или продавец)")
def cancel_reservation(
    reservation_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    reservation, artwork = _load_locked(db, reservation_id)
    allowed = user.role == UserRole.admin or user.id in (reservation.buyer_id, artwork.seller_id)
    if not allowed:
        raise HTTPException(403, "Нет доступа к этой брони")
    if reservation.status != ReservationStatus.pending:
        raise HTTPException(409, "Отменить можно только бронь в статусе «ожидает»")
    reservation.status = ReservationStatus.cancelled
    reservation.cancelled_at = utcnow()
    artwork.status = ArtworkStatus.available
    db.commit()
    db.expire_all()
    return _out(db.get(Reservation, reservation_id))
