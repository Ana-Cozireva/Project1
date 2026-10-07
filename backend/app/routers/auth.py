from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.deps import get_current_user
from app.models import User, UserProfile, UserRole
from app.schemas.user import LoginIn, RegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _token_response(user: User) -> TokenOut:
    return TokenOut(
        access_token=create_access_token(user.id, user.role.value),
        user=UserOut.model_validate(user),
    )


def _authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalars(select(User).where(User.email == email.lower())).first()
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if data.role == UserRole.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Нельзя зарегистрироваться как администратор")
    email = data.email.lower()
    if db.scalars(select(User.id).where(User.email == email)).first() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Пользователь с таким email уже существует")
    user = User(email=email, password_hash=hash_password(data.password), role=data.role)
    user.profile = UserProfile(full_name=data.full_name.strip() if data.full_name else None)
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token_response(user)


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    return _token_response(_authenticate(db, data.email, data.password))


@router.post("/token", include_in_schema=True, summary="OAuth2 form login (для кнопки Authorize в Swagger)")
def token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = _authenticate(db, form.username, form.password)
    return {"access_token": create_access_token(user.id, user.role.value), "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
