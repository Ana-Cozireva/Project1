from pydantic import Field, field_validator

from app.schemas.common import ORMModel


class _NameIn(ORMModel):
    name: str = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("Название не может быть пустым")
        return v


class CityIn(_NameIn):
    name: str = Field(min_length=1, max_length=100)


class ArtistIn(_NameIn):
    name: str = Field(min_length=1, max_length=150)


class StyleIn(_NameIn):
    name: str = Field(min_length=1, max_length=80)


class TechniqueIn(_NameIn):
    name: str = Field(min_length=1, max_length=80)


class RefOut(ORMModel):
    id: int
    name: str
