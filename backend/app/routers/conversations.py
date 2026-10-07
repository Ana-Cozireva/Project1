from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_user
from app.models import Artwork, Conversation, Message, User
from app.schemas.social import (
    ArtworkMini,
    ConversationCreate,
    ConversationDetail,
    ConversationOut,
    MessageIn,
    MessageOut,
)
from app.services import get_artwork_or_404, user_short

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def _mini(artwork: Artwork) -> ArtworkMini:
    return ArtworkMini(
        id=artwork.id,
        title=artwork.title,
        cover_url=artwork.photos[0].url if artwork.photos else None,
        status=artwork.status.value,
    )


def _build(conv: Conversation, user: User, last: Message | None, unread: int) -> dict:
    return dict(
        id=conv.id,
        artwork=_mini(conv.artwork),
        buyer=user_short(conv.buyer),
        seller=user_short(conv.artwork.seller),
        created_at=conv.created_at,
        last_message=MessageOut.model_validate(last) if last else None,
        unread_count=unread,
    )


def _unread(db: Session, conv_ids: list[int], user: User) -> dict[int, int]:
    if not conv_ids:
        return {}
    rows = db.execute(
        select(Message.conversation_id, func.count())
        .where(
            Message.conversation_id.in_(conv_ids),
            Message.sender_id != user.id,
            Message.is_read.is_(False),
        )
        .group_by(Message.conversation_id)
    )
    return {cid: n for cid, n in rows}


def _participant_conversation(db: Session, conv_id: int, user: User) -> Conversation:
    conv = db.scalars(select(Conversation).where(Conversation.id == conv_id)).unique().first()
    if conv is None:
        raise HTTPException(404, "Диалог не найден")
    if user.id not in (conv.buyer_id, conv.artwork.seller_id):
        raise HTTPException(403, "Нет доступа к этому диалогу")
    return conv


@router.get("", response_model=list[ConversationOut])
def list_conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    convs = db.scalars(
        select(Conversation)
        .join(Artwork, Artwork.id == Conversation.artwork_id)
        .where(or_(Conversation.buyer_id == user.id, Artwork.seller_id == user.id))
    ).unique().all()
    ids = [c.id for c in convs]
    last_ids = select(func.max(Message.id)).where(Message.conversation_id.in_(ids)).group_by(Message.conversation_id)
    last_by_conv = {m.conversation_id: m for m in db.scalars(select(Message).where(Message.id.in_(last_ids)))} if ids else {}
    unread = _unread(db, ids, user)
    result = [_build(c, user, last_by_conv.get(c.id), unread.get(c.id, 0)) for c in convs]
    result.sort(key=lambda r: r["last_message"].id if r["last_message"] else 0, reverse=True)
    return result


@router.get("/unread-count")
def unread_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    total = db.scalar(
        select(func.count(Message.id))
        .join(Conversation, Conversation.id == Message.conversation_id)
        .join(Artwork, Artwork.id == Conversation.artwork_id)
        .where(
            or_(Conversation.buyer_id == user.id, Artwork.seller_id == user.id),
            Message.sender_id != user.id,
            Message.is_read.is_(False),
        )
    )
    return {"unread": total or 0}


@router.post("", response_model=ConversationDetail, status_code=201, summary="Написать продавцу по объявлению")
def start_conversation(
    data: ConversationCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    artwork = get_artwork_or_404(db, data.artwork_id)
    if artwork.seller_id == user.id:
        raise HTTPException(400, "Нельзя написать самому себе по собственному объявлению")
    conv = db.scalars(
        select(Conversation).where(
            Conversation.artwork_id == artwork.id, Conversation.buyer_id == user.id
        )
    ).unique().first()
    if conv is None:
        conv = Conversation(artwork_id=artwork.id, buyer_id=user.id)
        db.add(conv)
        db.flush()
    db.add(Message(conversation_id=conv.id, sender_id=user.id, content=data.content))
    db.commit()
    return get_conversation(conv.id, user, db)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    db.expire_all()
    conv = _participant_conversation(db, conversation_id, user)
    messages = list(db.scalars(
        select(Message).where(Message.conversation_id == conv.id).order_by(Message.id)
    ))
    changed = False
    for m in messages:
        if m.sender_id != user.id and not m.is_read:
            m.is_read = True
            changed = True
    if changed:
        db.commit()
    payload = _build(conv, user, messages[-1] if messages else None, 0)
    payload["messages"] = [MessageOut.model_validate(m) for m in messages]
    return payload


@router.post("/{conversation_id}/messages", response_model=MessageOut, status_code=201)
def send_message(
    conversation_id: int,
    data: MessageIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = _participant_conversation(db, conversation_id, user)
    message = Message(conversation_id=conv.id, sender_id=user.id, content=data.content)
    db.add(message)
    db.commit()
    return message
