from pydantic import EmailStr, Field

from app.models.enums import UserRole
from app.schemas.common import ORMModel, UTCDatetime
from app.schemas.reference import RefOut

from pydantic import BaseModel


class ProfileOut(ORMModel):
    full_name: str | None = None
    phone: str | None = None
    city: RefOut | None = None


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=20, pattern=r"^[0-9+()\-\s]*$")
    city_id: int | None = None


class UserOut(ORMModel):
    id: int
    email: EmailStr
    role: UserRole
    created_at: UTCDatetime
    profile: ProfileOut | None = None


class UserShort(ORMModel):
    """Публичная карточка пользователя (продавец / покупатель)."""

    id: int
    full_name: str | None = None
    city: RefOut | None = None


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str | None = Field(default=None, max_length=100)
    role: UserRole = UserRole.buyer


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class RoleUpdate(BaseModel):
    role: UserRole
