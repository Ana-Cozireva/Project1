import enum


class UserRole(str, enum.Enum):
    buyer = "buyer"
    seller = "seller"
    admin = "admin"


class ArtworkCondition(str, enum.Enum):
    excellent = "excellent"
    good = "good"
    fair = "fair"
    restored = "restored"


class ArtworkStatus(str, enum.Enum):
    available = "available"
    reserved = "reserved"
    sold = "sold"


class ReservationStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
