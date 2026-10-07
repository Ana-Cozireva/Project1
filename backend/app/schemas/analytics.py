from decimal import Decimal

from pydantic import BaseModel


class GroupStat(BaseModel):
    id: int | None
    name: str
    artworks_count: int
    sold_count: int
    avg_price: Decimal
    total_value: Decimal
    sold_value: Decimal


class MonthStat(BaseModel):
    month: str  # YYYY-MM
    listed_count: int
    reservations_count: int
    sold_count: int
    sold_value: Decimal


class Overview(BaseModel):
    users_total: int
    users_by_role: dict[str, int]
    artworks_total: int
    artworks_by_status: dict[str, int]
    reservations_by_status: dict[str, int]
    conversations_total: int
    sold_value: Decimal
    avg_price: Decimal
