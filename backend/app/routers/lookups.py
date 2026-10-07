"""Справочники: города, художники, стили, техники. Публичное чтение, создание — продавец/админ."""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import require_admin, require_seller
from app.models import Artist, City, Style, Technique
from app.schemas.reference import ArtistIn, CityIn, RefOut, StyleIn, TechniqueIn

router = APIRouter(prefix="/api", tags=["lookups"])


def _register(path: str, model, schema_in, label: str, label_gen: str) -> None:
    @router.get(f"/{path}", response_model=list[RefOut], name=f"list_{path}")
    def list_items(db: Session = Depends(get_db)):
        return db.scalars(select(model).order_by(model.name)).all()

    @router.post(
        f"/{path}",
        response_model=RefOut,
        status_code=201,
        name=f"create_{path}",
        dependencies=[Depends(require_seller)],
    )
    def create_item(data: schema_in, db: Session = Depends(get_db)):  # type: ignore[valid-type]
        existing = db.scalars(
            select(model).where(func.lower(model.name) == data.name.lower())
        ).first()
        if existing:
            return existing  # идемпотентно: «найти или создать»
        item = model(name=data.name)
        db.add(item)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, f"{label} с таким названием уже существует")
        return item

    @router.put(
        f"/{path}/{{item_id}}",
        response_model=RefOut,
        name=f"update_{path}",
        dependencies=[Depends(require_admin)],
    )
    def update_item(item_id: int, data: schema_in, db: Session = Depends(get_db)):  # type: ignore[valid-type]
        item = db.get(model, item_id)
        if item is None:
            raise HTTPException(404, f"{label} не найден(а)")
        item.name = data.name
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, f"{label} с таким названием уже существует")
        return item

    @router.delete(
        f"/{path}/{{item_id}}",
        status_code=204,
        name=f"delete_{path}",
        dependencies=[Depends(require_admin)],
    )
    def delete_item(item_id: int, db: Session = Depends(get_db)):
        item = db.get(model, item_id)
        if item is None:
            raise HTTPException(404, f"{label} не найден(а)")
        db.delete(item)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, f"{label} используется в объявлениях и не может быть удалён(а)")
        return Response(status_code=204)


_register("cities", City, CityIn, "Город", "города")
_register("artists", Artist, ArtistIn, "Художник", "художника")
_register("styles", Style, StyleIn, "Стиль", "стиля")
_register("techniques", Technique, TechniqueIn, "Техника", "техники")
