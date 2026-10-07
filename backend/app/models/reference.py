from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import SmallInt


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(SmallInt, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class Artist(Base):
    __tablename__ = "artists"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)


class Style(Base):
    __tablename__ = "styles"

    id: Mapped[int] = mapped_column(SmallInt, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)


class Technique(Base):
    __tablename__ = "techniques"

    id: Mapped[int] = mapped_column(SmallInt, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
