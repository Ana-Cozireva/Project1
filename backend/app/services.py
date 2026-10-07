"""Общие функции: сериализация карточек, пагинация, доступ к произведениям."""
import math

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Artwork, Favorite, User
from app.schemas.artwork import ArtworkCard, ArtworkOut
from app.schemas.user import UserShort


def like_pattern(term: str) -> str:
    """Экранирует спецсимволы LIKE (% и _) в пользовательском поиске. Использовать с escape="\\"."""
    escaped = term.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def user_short(user: User) -> UserShort:
    profile = user.profile
    return UserShort(
        id=user.id,
        full_name=(profile.full_name if profile and profile.full_name else user.email.split("@")[0]),
        city=profile.city if profile else None,
    )


def favorite_ids(db: Session, user: User | None, artwork_ids: list[int]) -> set[int]:
    if user is None or not artwork_ids:
        return set()
    rows = db.scalars(
        select(Favorite.artwork_id).where(
            Favorite.user_id == user.id, Favorite.artwork_id.in_(artwork_ids)
        )
    )
    return set(rows)


def to_card(artwork: Artwork, fav: set[int] | None = None) -> ArtworkCard:
    return ArtworkCard(
        id=artwork.id,
        title=artwork.title,
        year_created=artwork.year_created,
        price=artwork.price,
        condition=artwork.condition,
        status=artwork.status,
        created_at=artwork.created_at,
        artist=artwork.artist,
        style=artwork.style,
        technique=artwork.technique,
        city=artwork.city,
        cover_url=artwork.photos[0].url if artwork.photos else None,
        is_favorite=bool(fav and artwork.id in fav),
    )


def to_full(artwork: Artwork, fav: set[int] | None = None) -> ArtworkOut:
    return ArtworkOut(
        id=artwork.id,
        title=artwork.title,
        year_created=artwork.year_created,
        price=artwork.price,
        condition=artwork.condition,
        status=artwork.status,
        created_at=artwork.created_at,
        updated_at=artwork.updated_at,
        artist=artwork.artist,
        style=artwork.style,
        technique=artwork.technique,
        city=artwork.city,
        seller_id=artwork.seller_id,
        seller=user_short(artwork.seller),
        details=artwork.details,
        photos=artwork.photos,
        is_favorite=bool(fav and artwork.id in fav),
    )


def paginate(db: Session, query, page: int, page_size: int) -> tuple[list, int, int]:
    """Возвращает (элементы, total, pages). Использует отдельный COUNT по подзапросу."""
    total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0
    pages = max(1, math.ceil(total / page_size))
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).unique().all()
    return list(items), total, pages


def get_artwork_or_404(db: Session, artwork_id: int, *, lock: bool = False) -> Artwork:
    """Загрузка произведения. lock=True — SELECT ... FOR UPDATE по строке artworks.

    Блокировка берётся отдельным запросом по первичному ключу: так PostgreSQL не
    ругается на FOR UPDATE для nullable-стороны LEFT JOIN при eager-загрузке связей.
    """
    stmt = select(Artwork).where(Artwork.id == artwork_id)
    if lock:
        locked = db.execute(
            select(Artwork.id).where(Artwork.id == artwork_id).with_for_update()
        ).first()
        if locked is None:
            raise HTTPException(404, "Произведение не найдено")
        stmt = stmt.execution_options(populate_existing=True)
    artwork = db.scalars(stmt).unique().first()
    if artwork is None:
        raise HTTPException(404, "Произведение не найдено")
    return artwork
