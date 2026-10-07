from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import ArtworkCondition, ArtworkStatus
from app.schemas.common import ORMModel, UTCDatetime
from app.schemas.reference import RefOut
from app.schemas.user import UserShort


class DetailsIn(BaseModel):
    width_cm: Decimal | None = Field(default=None, gt=0, lt=10000, decimal_places=1)
    height_cm: Decimal | None = Field(default=None, gt=0, lt=10000, decimal_places=1)
    depth_cm: Decimal | None = Field(default=None, gt=0, lt=10000, decimal_places=1)
    description: str | None = Field(default=None, max_length=4000)


class DetailsOut(ORMModel):
    width_cm: Decimal | None = None
    height_cm: Decimal | None = None
    depth_cm: Decimal | None = None
    description: str | None = None


class PhotoOut(ORMModel):
    id: int
    url: str
    position: int


class ArtworkBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    artist_id: int
    style_id: int | None = None
    technique_id: int | None = None
    city_id: int | None = None
    year_created: int | None = Field(default=None, ge=1000, le=datetime.now().year)
    price: Decimal = Field(gt=0, lt=Decimal("1000000000"), decimal_places=2)
    condition: ArtworkCondition | None = None
    details: DetailsIn | None = None

    @field_validator("title")
    @classmethod
    def _strip_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Название не может быть пустым")
        return v


class ArtworkCreate(ArtworkBase):
    pass


class ArtworkUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    artist_id: int | None = None
    style_id: int | None = None
    technique_id: int | None = None
    city_id: int | None = None
    year_created: int | None = Field(default=None, ge=1000, le=datetime.now().year)
    price: Decimal | None = Field(default=None, gt=0, lt=Decimal("1000000000"), decimal_places=2)
    condition: ArtworkCondition | None = None
    details: DetailsIn | None = None
    status: ArtworkStatus | None = None  # только администратор


class ArtworkCard(ORMModel):
    """Краткая карточка для каталога."""

    id: int
    title: str
    year_created: int | None = None
    price: Decimal
    condition: ArtworkCondition | None = None
    status: ArtworkStatus
    created_at: UTCDatetime
    artist: RefOut
    style: RefOut | None = None
    technique: RefOut | None = None
    city: RefOut | None = None
    cover_url: str | None = None
    is_favorite: bool = False


class ArtworkOut(ORMModel):
    id: int
    title: str
    year_created: int | None = None
    price: Decimal
    condition: ArtworkCondition | None = None
    status: ArtworkStatus
    created_at: UTCDatetime
    updated_at: UTCDatetime | None = None
    artist: RefOut
    style: RefOut | None = None
    technique: RefOut | None = None
    city: RefOut | None = None
    seller_id: int
    seller: UserShort | None = None
    details: DetailsOut | None = None
    photos: list[PhotoOut] = []
    is_favorite: bool = False
