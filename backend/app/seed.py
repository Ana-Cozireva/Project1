"""Начальные данные: администратор (всегда) и демо-каталог (если БД пуста)."""
import logging
import random
import uuid
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from PIL import Image, ImageDraw
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import (
    Artist,
    Artwork,
    ArtworkCondition as C,
    ArtworkDetail,
    ArtworkPhoto,
    ArtworkStatus as S,
    City,
    Conversation,
    Favorite,
    Message,
    Reservation,
    ReservationStatus as RS,
    Style,
    Technique,
    User,
    UserProfile,
    UserRole,
)
from app.models.base import utcnow

settings = get_settings()
log = logging.getLogger(__name__)

CITIES = ["Кишинёв", "Бельцы", "Кагул", "Орхей", "Сорока", "Комрат", "Унгены"]
STYLES = ["Импрессионизм", "Реализм", "Абстракционизм", "Экспрессионизм", "Минимализм", "Сюрреализм", "Народное искусство"]
TECHNIQUES = ["Масло, холст", "Акрил, холст", "Акварель, бумага", "Гуашь, бумага", "Уголь, бумага", "Тушь, перо", "Бронза", "Керамика", "Фотография, архивная печать"]
ARTISTS = [
    "Елена Русу", "Андрей Чебан", "Мария Попеску", "Виктор Лунгу", "Ирина Мунтян",
    "Дмитрий Сава", "Анна Гуцу", "Сергей Бодруг", "Лилия Ботнару", "Николай Кожокару",
]

PALETTES = [
    [(236, 196, 120), (190, 96, 62), (60, 74, 110), (244, 236, 220)],
    [(30, 58, 95), (84, 130, 160), (214, 226, 230), (230, 180, 90)],
    [(46, 74, 58), (120, 150, 96), (222, 214, 170), (160, 70, 60)],
    [(24, 24, 28), (200, 40, 48), (240, 238, 232), (120, 120, 126)],
    [(104, 52, 96), (228, 130, 120), (250, 214, 160), (50, 40, 80)],
    [(196, 176, 148), (136, 112, 90), (236, 228, 214), (74, 66, 60)],
]


def _make_image(seed: int, kind: str, landscape: bool, root: Path) -> str:
    """Генерирует абстрактную «картину» для демо-каталога (без внешних ресурсов)."""
    rnd = random.Random(seed)
    w, h = (1000, 760) if landscape else (760, 1000)
    pal = PALETTES[seed % len(PALETTES)]
    img = Image.new("RGB", (w, h), pal[-1] if kind != "dark" else pal[0])
    d = ImageDraw.Draw(img, "RGBA")

    if kind == "landscape":
        for y in range(h):  # небо
            t = y / h
            c = tuple(int(pal[2][i] * (1 - t) + pal[3][i] * t) for i in range(3))
            d.line([(0, y), (w, y)], fill=c)
        d.ellipse([w * 0.62, h * 0.14, w * 0.62 + 130, h * 0.14 + 130], fill=(*pal[3], 235))
        for layer in range(4):
            base = h * (0.46 + layer * 0.13)
            pts = [(0, h)]
            for x in range(0, w + 40, 40):
                pts.append((x, base + rnd.randint(-38, 38)))
            pts.append((w, h))
            d.polygon(pts, fill=(*pal[layer % 3], 255 - layer * 22))
    elif kind == "minimal":
        d.rectangle([0, 0, w, h], fill=pal[2])
        for i in range(rnd.randint(2, 4)):
            x0 = rnd.randint(40, w // 2)
            d.rectangle([x0, h * 0.2 + i * 90, x0 + rnd.randint(160, 420), h * 0.2 + i * 90 + rnd.randint(30, 140)], fill=(*pal[i % 3], 240))
        d.line([(60, h - 120), (w - 60, h - 120)], fill=(*pal[0], 255), width=6)
    elif kind == "dark":
        for _ in range(26):
            x, y = rnd.randint(-100, w), rnd.randint(-100, h)
            r = rnd.randint(60, 340)
            d.ellipse([x, y, x + r, y + r], fill=(*rnd.choice(pal[1:]), rnd.randint(60, 170)))
        for _ in range(7):
            d.line([(rnd.randint(0, w), rnd.randint(0, h)), (rnd.randint(0, w), rnd.randint(0, h))], fill=(*pal[2], 200), width=rnd.randint(3, 12))
    else:  # abstract
        for _ in range(18):
            x, y = rnd.randint(-60, w), rnd.randint(-60, h)
            sw, sh = rnd.randint(80, 420), rnd.randint(80, 420)
            shape = rnd.choice(("rect", "ellipse"))
            fill = (*rnd.choice(pal[:3]), rnd.randint(110, 230))
            (d.rectangle if shape == "rect" else d.ellipse)([x, y, x + sw, y + sh], fill=fill)
        for _ in range(5):
            d.line([(rnd.randint(0, w), 0), (rnd.randint(0, w), h)], fill=(*pal[3], 160), width=rnd.randint(2, 8))

    root.mkdir(parents=True, exist_ok=True)
    name = f"seed-{uuid.uuid4().hex[:12]}.jpg"
    img.save(root / name, "JPEG", quality=84)
    return f"/uploads/{name}"


def ensure_admin(db: Session) -> None:
    email = settings.admin_email.lower()
    if db.scalars(select(User).where(User.email == email)).first():
        return
    admin = User(email=email, password_hash=hash_password(settings.admin_password), role=UserRole.admin)
    admin.profile = UserProfile(full_name="Администратор")
    db.add(admin)
    db.commit()
    log.info("Admin user created: %s", email)


def _user(db, email, password, role, name, city_id, phone):
    user = User(email=email, password_hash=hash_password(password), role=role)
    user.profile = UserProfile(full_name=name, city_id=city_id, phone=phone)
    db.add(user)
    db.flush()
    return user


# (title, artist, style, technique, city, year, price, condition, w, h, d, kind, landscape, seller_idx, description)
WORKS = [
    ("Рассвет над Днестром", 0, 0, 0, 0, 2019, 1450, C.excellent, 80, 60, None, "landscape", True, 0, "Утренний туман над рекой, мягкий свет сквозь деревья. Работа написана на пленэре у Сороки."),
    ("Виноградники в октябре", 0, 0, 0, 3, 2021, 1280, C.excellent, 70, 50, None, "landscape", True, 0, "Осенние ряды лозы в окрестностях Орхея. Тёплая охристая гамма."),
    ("Старый Орхей", 1, 1, 0, 3, 2015, 980, C.good, 60, 45, None, "landscape", True, 0, "Вид на монастырский комплекс. Лёгкая сетка кракелюров, холст дублирован."),
    ("Тишина № 3", 2, 4, 1, 0, 2023, 760, C.excellent, 100, 100, None, "minimal", True, 1, "Из серии «Тишина»: три цветовых поля и одна линия горизонта."),
    ("Красная линия", 3, 2, 1, 0, 2022, 1900, C.excellent, 120, 90, None, "dark", True, 1, "Крупноформатная абстракция в графитовой гамме с красным акцентом."),
    ("Женщина с корзиной", 4, 1, 0, 1, 2008, 2400, C.good, 55, 75, None, "abstract", False, 0, "Жанровая сцена на рынке в Бельцах. Рама ручной работы входит в стоимость."),
    ("Рынок в Бельцах", 4, 0, 3, 1, 2012, 540, C.good, 40, 30, None, "abstract", True, 1, "Гуашь на плотной бумаге, паспарту в комплекте."),
    ("Зимний Кишинёв", 5, 1, 2, 0, 2020, 430, C.excellent, 42, 30, None, "landscape", True, 0, "Акварель: Центральный парк после снегопада."),
    ("Синий кувшин", 6, 0, 0, 0, 2017, 690, C.excellent, 45, 60, None, "dark", False, 1, "Натюрморт в холодной гамме, написан за один сеанс."),
    ("Бронзовая птица", 7, 4, 6, 0, 2018, 3100, C.excellent, 28, 46, 18, "minimal", False, 0, "Скульптура из бронзы, патина. Высота 46 см, на мраморном основании."),
    ("Дорога к крепости", 1, 1, 0, 4, 2014, 1150, C.good, 90, 60, None, "landscape", True, 0, "Вид на Сорокскую крепость с юга. Холст, масло, без рамы."),
    ("Композиция в охре", 2, 2, 1, 5, 2024, 880, C.excellent, 80, 80, None, "abstract", True, 1, "Свободная геометрия, плотные слои акрила."),
    ("Лето в Кагуле", 8, 0, 0, 2, 2016, 1020, C.good, 70, 55, None, "landscape", True, 1, "Цветущий сад у дома, яркий полдень."),
    ("Портрет с зелёным шарфом", 8, 3, 0, 0, 2011, 2650, C.restored, 60, 80, None, "dark", False, 0, "Экспрессивный портрет. Реставрация 2020 года, документы в наличии."),
    ("Городской ритм", 3, 2, 1, 0, 2025, 1350, C.excellent, 100, 70, None, "abstract", True, 1, "Динамичная композиция по мотивам вечернего движения на бульваре."),
    ("Тени Комрата", 5, 4, 4, 5, 2022, 320, C.excellent, 50, 35, None, "minimal", True, 0, "Графика углём: тени от домов на площади."),
    ("Ваза с гранатами", 6, 0, 3, 2, 2019, 470, C.good, 38, 48, None, "abstract", False, 1, "Гуашь, насыщенные красные и бирюзовые тона."),
    ("Ритуал", 9, 5, 5, 0, 2021, 590, C.excellent, 30, 40, None, "dark", False, 0, "Графика тушью, сюрреалистичная сцена в духе народных обрядов."),
    ("Керамический лес", 7, 6, 7, 3, 2023, 740, C.excellent, 25, 32, 25, "abstract", False, 1, "Объект из шамотной глины, обжиг и глазурь. Ручная работа."),
    ("Вечер на Прут", 9, 1, 0, 6, 2013, 1240, C.good, 75, 55, None, "landscape", True, 0, "Спокойный вечерний пейзаж у границы."),
    ("Пустой дом", 5, 4, 8, 4, 2022, 260, C.excellent, 60, 40, None, "minimal", True, 1, "Архивная печать, серия 2/10, подпись автора на обороте."),
    ("Осенний ветер", 1, 3, 1, 1, 2018, 1560, C.excellent, 100, 80, None, "dark", True, 0, "Экспрессионистский пейзаж, мощный мазок."),
    ("Зелёный квадрат", 2, 4, 1, 0, 2020, 810, C.excellent, 70, 70, None, "minimal", True, 1, "Минималистичная работа в зелёно-охристой гамме."),
    ("Колодец", 0, 6, 2, 3, 2010, 360, C.fair, 34, 48, None, "abstract", False, 0, "Народный мотив, акварель, лёгкие следы времени на полях."),
]


def seed_demo_data(db: Session) -> None:
    if db.scalars(select(Artwork.id).limit(1)).first() is not None:
        return
    log.info("Seeding demo data…")
    rnd = random.Random(42)

    cities = [City(name=n) for n in CITIES]
    styles = [Style(name=n) for n in STYLES]
    techniques = [Technique(name=n) for n in TECHNIQUES]
    artists = [Artist(name=n) for n in ARTISTS]
    for group in (cities, styles, techniques, artists):
        for item in group:
            if not db.scalars(select(type(item)).where(type(item).name == item.name)).first():
                db.add(item)
    db.flush()
    cities = list(db.scalars(select(City).order_by(City.id)))
    styles = list(db.scalars(select(Style).order_by(Style.id)))
    techniques = list(db.scalars(select(Technique).order_by(Technique.id)))
    artists = list(db.scalars(select(Artist).order_by(Artist.id)))

    sellers = [
        _user(db, "gallery@artgallery.md", "seller12345", UserRole.seller, "Галерея «Nistru»", cities[0].id, "+37369000001"),
        _user(db, "studio@artgallery.md", "seller12345", UserRole.seller, "Мастерская Е. Русу", cities[1].id, "+37369000002"),
    ]
    buyers = [
        _user(db, "buyer@artgallery.md", "buyer12345", UserRole.buyer, "Анна Попа", cities[0].id, "+37369000003"),
        _user(db, "buyer2@artgallery.md", "buyer12345", UserRole.buyer, "Иван Ротару", cities[1].id, None),
    ]

    upload_root = Path(settings.upload_dir)
    created: list[Artwork] = []
    for i, w in enumerate(WORKS):
        (title, a, s, t, c, year, price, cond, width, height, depth, kind, landscape, seller_idx, desc) = w
        age_days = int(300 - i * 12 + rnd.randint(-5, 5))
        artwork = Artwork(
            title=title, seller_id=sellers[seller_idx].id, artist_id=artists[a].id,
            style_id=styles[s].id, technique_id=techniques[t].id, city_id=cities[c].id,
            year_created=year, price=Decimal(price), condition=cond, status=S.available,
            created_at=utcnow() - timedelta(days=max(age_days, 2)),
        )
        artwork.details = ArtworkDetail(
            width_cm=Decimal(width), height_cm=Decimal(height),
            depth_cm=Decimal(depth) if depth else None, description=desc,
        )
        db.add(artwork)
        db.flush()
        for pos in range(2 if i % 3 == 0 else 1):
            url = _make_image(i * 10 + pos + 1, kind, landscape if pos == 0 else not landscape, upload_root)
            db.add(ArtworkPhoto(artwork_id=artwork.id, url=url, position=pos))
        created.append(artwork)

    # Бронирования: проданные, ожидающие и отменённая
    def reserve(art_idx, buyer, status, days_ago):
        art = created[art_idx]
        r = Reservation(artwork_id=art.id, buyer_id=buyer.id, status=status, created_at=utcnow() - timedelta(days=days_ago))
        if status == RS.confirmed:
            r.confirmed_at = r.created_at + timedelta(days=1)
            art.status = S.sold
        elif status == RS.cancelled:
            r.cancelled_at = r.created_at + timedelta(days=2)
        else:
            art.status = S.reserved
        db.add(r)

    reserve(7, buyers[0], RS.confirmed, 120)
    reserve(15, buyers[1], RS.confirmed, 75)
    reserve(3, buyers[1], RS.confirmed, 40)
    reserve(10, buyers[0], RS.confirmed, 12)
    reserve(0, buyers[1], RS.pending, 2)
    reserve(9, buyers[0], RS.pending, 1)
    reserve(4, buyers[0], RS.cancelled, 20)

    for art_idx in (0, 4, 9, 13):
        db.add(Favorite(user_id=buyers[0].id, artwork_id=created[art_idx].id))
    db.add(Favorite(user_id=buyers[1].id, artwork_id=created[3].id))

    conv = Conversation(artwork_id=created[1].id, buyer_id=buyers[0].id)
    db.add(conv)
    db.flush()
    db.add_all([
        Message(conversation_id=conv.id, sender_id=buyers[0].id, content="Здравствуйте! Подскажите, возможна ли доставка в Кишинёв и есть ли сертификат подлинности?", is_read=True),
        Message(conversation_id=conv.id, sender_id=sellers[0].id, content="Добрый день! Да, сертификат прилагается, доставку по Молдове организуем за свой счёт.", is_read=False),
    ])
    db.commit()
    log.info("Demo data ready: %s artworks", len(created))
