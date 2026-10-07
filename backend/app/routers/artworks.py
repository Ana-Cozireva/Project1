import uuid
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.deps import get_current_user_optional, require_seller
from app.models import (
    Artist,
    Artwork,
    ArtworkCondition,
    ArtworkDetail,
    ArtworkPhoto,
    ArtworkStatus,
    City,
    Style,
    Technique,
    User,
    UserRole,
)
from app.schemas.artwork import (
    ArtworkCard,
    ArtworkCreate,
    ArtworkOut,
    ArtworkUpdate,
    PhotoOut,
)
from app.schemas.common import Page
from app.services import favorite_ids, get_artwork_or_404, like_pattern, paginate, to_card, to_full

settings = get_settings()
router = APIRouter(prefix="/api/artworks", tags=["artworks"])

SORTS = {
    "newest": (Artwork.created_at.desc(), Artwork.id.desc()),
    "oldest": (Artwork.created_at.asc(), Artwork.id.asc()),
    "price_asc": (Artwork.price.asc(), Artwork.id.asc()),
    "price_desc": (Artwork.price.desc(), Artwork.id.desc()),
    "title": (func.lower(Artwork.title).asc(), Artwork.id.asc()),
}
ALLOWED_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


# ---------- helpers ----------
def _check_refs(db: Session, data: dict) -> None:
    checks = (
        ("artist_id", Artist, "Художник"),
        ("style_id", Style, "Стиль"),
        ("technique_id", Technique, "Техника"),
        ("city_id", City, "Город"),
    )
    for field, model, label in checks:
        value = data.get(field)
        if value is not None and db.get(model, value) is None:
            raise HTTPException(422, f"{label} не найден(а)")


def _ensure_owner(artwork: Artwork, user: User) -> None:
    if user.role != UserRole.admin and artwork.seller_id != user.id:
        raise HTTPException(403, "Это объявление принадлежит другому продавцу")


def _reload(db: Session, artwork_id: int) -> Artwork:
    db.expire_all()
    return get_artwork_or_404(db, artwork_id)


def _filtered_query(
    *,
    q, artist_id, style_id, technique_id, city_id, seller_id, condition, status,
    price_min, price_max, width_min, width_max, height_min, height_max, sort,
):
    stmt = select(Artwork)
    if q:
        term = like_pattern(q)
        stmt = stmt.where(
            or_(
                Artwork.title.ilike(term, escape="\\"),
                Artwork.artist.has(Artist.name.ilike(term, escape="\\")),
            )
        )
    if artist_id:
        stmt = stmt.where(Artwork.artist_id == artist_id)
    if style_id:
        stmt = stmt.where(Artwork.style_id == style_id)
    if technique_id:
        stmt = stmt.where(Artwork.technique_id == technique_id)
    if city_id:
        stmt = stmt.where(Artwork.city_id == city_id)
    if seller_id:
        stmt = stmt.where(Artwork.seller_id == seller_id)
    if condition:
        stmt = stmt.where(Artwork.condition == condition)
    if status:
        stmt = stmt.where(Artwork.status == status)
    if price_min is not None:
        stmt = stmt.where(Artwork.price >= price_min)
    if price_max is not None:
        stmt = stmt.where(Artwork.price <= price_max)
    if any(v is not None for v in (width_min, width_max, height_min, height_max)):
        stmt = stmt.outerjoin(ArtworkDetail, ArtworkDetail.artwork_id == Artwork.id)
        if width_min is not None:
            stmt = stmt.where(ArtworkDetail.width_cm >= width_min)
        if width_max is not None:
            stmt = stmt.where(ArtworkDetail.width_cm <= width_max)
        if height_min is not None:
            stmt = stmt.where(ArtworkDetail.height_cm >= height_min)
        if height_max is not None:
            stmt = stmt.where(ArtworkDetail.height_cm <= height_max)
    return stmt.order_by(*SORTS[sort])


def _page_of_cards(db, stmt, page, page_size, user) -> Page[ArtworkCard]:
    items, total, pages = paginate(db, stmt, page, page_size)
    fav = favorite_ids(db, user, [a.id for a in items])
    return Page(
        items=[to_card(a, fav) for a in items],
        total=total, page=page, page_size=page_size, pages=pages,
    )


# ---------- catalog ----------
@router.get("", response_model=Page[ArtworkCard], summary="Каталог: поиск, фильтры, сортировка, пагинация")
def list_artworks(
    q: str | None = Query(None, max_length=100, description="Поиск по названию или художнику"),
    artist_id: int | None = None,
    style_id: int | None = None,
    technique_id: int | None = None,
    city_id: int | None = None,
    seller_id: int | None = None,
    condition: ArtworkCondition | None = None,
    status: ArtworkStatus | None = None,
    price_min: Decimal | None = Query(None, ge=0),
    price_max: Decimal | None = Query(None, ge=0),
    width_min: Decimal | None = Query(None, ge=0),
    width_max: Decimal | None = Query(None, ge=0),
    height_min: Decimal | None = Query(None, ge=0),
    height_max: Decimal | None = Query(None, ge=0),
    sort: str = Query("newest", pattern="^(newest|oldest|price_asc|price_desc|title)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=60),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    stmt = _filtered_query(
        q=q, artist_id=artist_id, style_id=style_id, technique_id=technique_id,
        city_id=city_id, seller_id=seller_id, condition=condition, status=status,
        price_min=price_min, price_max=price_max, width_min=width_min, width_max=width_max,
        height_min=height_min, height_max=height_max, sort=sort,
    )
    return _page_of_cards(db, stmt, page, page_size, user)


@router.get("/mine", response_model=Page[ArtworkCard], summary="Мои объявления (продавец)")
def my_artworks(
    status: ArtworkStatus | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_seller),
):
    stmt = select(Artwork).where(Artwork.seller_id == user.id).order_by(Artwork.created_at.desc(), Artwork.id.desc())
    if status:
        stmt = stmt.where(Artwork.status == status)
    return _page_of_cards(db, stmt, page, page_size, user)


@router.get("/{artwork_id}", response_model=ArtworkOut)
def get_artwork(
    artwork_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    artwork = get_artwork_or_404(db, artwork_id)
    return to_full(artwork, favorite_ids(db, user, [artwork.id]))


# ---------- CRUD ----------
@router.post("", response_model=ArtworkOut, status_code=201)
def create_artwork(
    data: ArtworkCreate, db: Session = Depends(get_db), user: User = Depends(require_seller)
):
    payload = data.model_dump(exclude={"details"})
    _check_refs(db, payload)
    artwork = Artwork(**payload, seller_id=user.id, status=ArtworkStatus.available)
    if data.details:
        artwork.details = ArtworkDetail(**data.details.model_dump())
    db.add(artwork)
    db.commit()
    return to_full(_reload(db, artwork.id))


@router.put("/{artwork_id}", response_model=ArtworkOut)
def update_artwork(
    artwork_id: int,
    data: ArtworkUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_seller),
):
    artwork = get_artwork_or_404(db, artwork_id)
    _ensure_owner(artwork, user)
    changes = data.model_dump(exclude_unset=True)
    details = changes.pop("details", None)

    if "status" in changes:
        if user.role != UserRole.admin:
            raise HTTPException(403, "Статус меняется через бронирование; вручную — только администратор")
    elif artwork.status == ArtworkStatus.sold and user.role != UserRole.admin:
        raise HTTPException(409, "Проданное произведение нельзя редактировать")
    for required in ("title", "artist_id", "price"):
        if required in changes and changes[required] is None:
            raise HTTPException(422, f"Поле {required} не может быть пустым")

    _check_refs(db, changes)
    for field, value in changes.items():
        setattr(artwork, field, value)
    if details is not None:
        if artwork.details is None:
            artwork.details = ArtworkDetail()
        for field, value in details.items():
            setattr(artwork.details, field, value)
    db.commit()
    return to_full(_reload(db, artwork_id))


@router.delete("/{artwork_id}", status_code=204)
def delete_artwork(
    artwork_id: int, db: Session = Depends(get_db), user: User = Depends(require_seller)
):
    artwork = get_artwork_or_404(db, artwork_id)
    _ensure_owner(artwork, user)
    if artwork.status != ArtworkStatus.available and user.role != UserRole.admin:
        raise HTTPException(409, "Нельзя удалить забронированное или проданное произведение. Сначала отмените бронь.")
    urls = [p.url for p in artwork.photos]
    db.delete(artwork)
    db.commit()
    for url in urls:
        _remove_file(url)


# ---------- photos ----------
def _upload_root() -> Path:
    root = Path(settings.upload_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _remove_file(url: str) -> None:
    if not url.startswith("/uploads/"):
        return
    path = _upload_root() / url.removeprefix("/uploads/")
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


@router.post("/{artwork_id}/photos", response_model=PhotoOut, status_code=201)
async def upload_photo(
    artwork_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_seller),
):
    artwork = get_artwork_or_404(db, artwork_id)
    _ensure_owner(artwork, user)
    if len(artwork.photos) >= settings.max_photos_per_artwork:
        raise HTTPException(409, f"Не более {settings.max_photos_per_artwork} фотографий на произведение")

    limit = settings.max_upload_mb * 1024 * 1024
    content = await file.read(limit + 1)
    if len(content) > limit:
        raise HTTPException(413, f"Файл больше {settings.max_upload_mb} МБ")
    try:
        with Image.open(BytesIO(content)) as img:
            fmt = img.format
            img.verify()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(415, "Файл не является изображением")
    if fmt not in ALLOWED_FORMATS:
        raise HTTPException(415, "Допустимые форматы: JPEG, PNG, WEBP")

    filename = f"{uuid.uuid4().hex}{ALLOWED_FORMATS[fmt]}"
    (_upload_root() / filename).write_bytes(content)

    next_pos = (max((p.position for p in artwork.photos), default=-1)) + 1
    photo = ArtworkPhoto(artwork_id=artwork.id, url=f"/uploads/{filename}", position=next_pos)
    db.add(photo)
    db.commit()
    return photo


@router.post("/{artwork_id}/photos/{photo_id}/cover", response_model=list[PhotoOut], summary="Сделать фото обложкой")
def make_cover(
    artwork_id: int, photo_id: int, db: Session = Depends(get_db), user: User = Depends(require_seller)
):
    artwork = get_artwork_or_404(db, artwork_id)
    _ensure_owner(artwork, user)
    photos = list(artwork.photos)
    chosen = next((p for p in photos if p.id == photo_id), None)
    if chosen is None:
        raise HTTPException(404, "Фотография не найдена")
    ordered = [chosen] + [p for p in photos if p.id != photo_id]
    for index, photo in enumerate(ordered):
        photo.position = index
    db.commit()
    return ordered


@router.delete("/{artwork_id}/photos/{photo_id}", status_code=204)
def delete_photo(
    artwork_id: int, photo_id: int, db: Session = Depends(get_db), user: User = Depends(require_seller)
):
    artwork = get_artwork_or_404(db, artwork_id)
    _ensure_owner(artwork, user)
    photo = next((p for p in artwork.photos if p.id == photo_id), None)
    if photo is None:
        raise HTTPException(404, "Фотография не найдена")
    url = photo.url
    db.delete(photo)
    db.commit()
    _remove_file(url)
