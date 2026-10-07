from pydantic import BaseModel, Field, field_validator

from app.models.enums import ReservationStatus
from app.schemas.artwork import ArtworkCard
from app.schemas.common import ORMModel, UTCDatetime
from app.schemas.user import UserShort


class MessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Сообщение не может быть пустым")
        return v


class ConversationCreate(MessageIn):
    artwork_id: int


class MessageOut(ORMModel):
    id: int
    conversation_id: int
    sender_id: int
    content: str
    is_read: bool
    created_at: UTCDatetime


class ArtworkMini(ORMModel):
    id: int
    title: str
    cover_url: str | None = None
    status: str


class ConversationOut(ORMModel):
    id: int
    artwork: ArtworkMini
    buyer: UserShort
    seller: UserShort
    created_at: UTCDatetime
    last_message: MessageOut | None = None
    unread_count: int = 0


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = []


class ReservationCreate(BaseModel):
    artwork_id: int


class ReservationOut(ORMModel):
    id: int
    status: ReservationStatus
    created_at: UTCDatetime
    confirmed_at: UTCDatetime | None = None
    cancelled_at: UTCDatetime | None = None
    artwork: ArtworkCard
    buyer: UserShort
    seller: UserShort


class FavoriteOut(ORMModel):
    artwork: ArtworkCard
    created_at: UTCDatetime
