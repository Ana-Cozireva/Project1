from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user, require_admin
from app.models import City, User, UserProfile
from app.schemas.common import Page
from app.schemas.user import ProfileUpdate, RoleUpdate, UserOut
from app.services import like_pattern, paginate

router = APIRouter(prefix="/api/users", tags=["users"])


@router.put("/me/profile", response_model=UserOut)
def update_my_profile(
    data: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if data.city_id is not None and db.get(City, data.city_id) is None:
        raise HTTPException(422, "Город не найден")
    if user.profile is None:
        user.profile = UserProfile()
    user.profile.full_name = data.full_name.strip() if data.full_name else None
    user.profile.phone = data.phone.strip() if data.phone else None
    user.profile.city_id = data.city_id
    db.commit()
    db.expire(user.profile, ["city"])
    db.refresh(user)
    return user


@router.get("", response_model=Page[UserOut], dependencies=[Depends(require_admin)])
def list_users(
    q: str | None = Query(None, description="Поиск по email"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(User).order_by(User.id)
    if q:
        stmt = stmt.where(User.email.ilike(like_pattern(q), escape="\\"))
    items, total, pages = paginate(db, stmt, page, page_size)
    return Page(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.patch("/{user_id}/role", response_model=UserOut)
def change_role(
    user_id: int,
    data: RoleUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "Пользователь не найден")
    if target.id == admin.id:
        raise HTTPException(400, "Нельзя изменить собственную роль")
    target.role = data.role
    db.commit()
    return target


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "Пользователь не найден")
    if target.id == admin.id:
        raise HTTPException(400, "Нельзя удалить собственную учётную запись")
    db.delete(target)
    db.commit()
