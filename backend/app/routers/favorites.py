from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user
from app.models import Favorite, User
from app.schemas.social import FavoriteOut
from app.services import get_artwork_or_404, to_card

router = APIRouter(prefix="/api/favorites", tags=["favorites"])


@router.get("", response_model=list[FavoriteOut])
def list_favorites(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Favorite).where(Favorite.user_id == user.id).order_by(Favorite.created_at.desc())
    ).unique().all()
    ids = {row.artwork_id for row in rows}
    return [FavoriteOut(artwork=to_card(row.artwork, ids), created_at=row.created_at) for row in rows]


@router.put("/{artwork_id}", status_code=204, summary="Добавить в избранное (идемпотентно)")
def add_favorite(artwork_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_artwork_or_404(db, artwork_id)
    if db.get(Favorite, (user.id, artwork_id)) is None:
        db.add(Favorite(user_id=user.id, artwork_id=artwork_id))
        db.commit()
    return Response(status_code=204)


@router.delete("/{artwork_id}", status_code=204, summary="Убрать из избранного (идемпотентно)")
def remove_favorite(artwork_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    favorite = db.get(Favorite, (user.id, artwork_id))
    if favorite is not None:
        db.delete(favorite)
        db.commit()
    return Response(status_code=204)
