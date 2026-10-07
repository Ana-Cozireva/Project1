from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import BigInteger, Enum, Integer, SmallInteger


def utcnow() -> datetime:
    """Naive UTC — соответствует типу `timestamp` из схемы БД."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# smallint / bigint автоинкремент работает в PostgreSQL (smallserial/bigserial);
# для SQLite (тесты) подменяем на INTEGER, иначе rowid-алиас не создаётся.
SmallInt = SmallInteger().with_variant(Integer(), "sqlite")
BigInt = BigInteger().with_variant(Integer(), "sqlite")


def pg_enum(enum_cls: type[PyEnum], name: str) -> Enum:
    return Enum(
        enum_cls,
        name=name,
        values_callable=lambda e: [m.value for m in e],
        native_enum=True,
        validate_strings=True,
    )
