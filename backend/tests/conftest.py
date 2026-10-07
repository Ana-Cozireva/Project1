import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="artgallery-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["SEED_DEMO_DATA"] = "false"
os.environ["ADMIN_EMAIL"] = "admin@test.md"
os.environ["ADMIN_PASSWORD"] = "adminpass1"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import ensure_admin  # noqa: E402


@pytest.fixture(autouse=True)
def db_reset():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        ensure_admin(db)
    yield


@pytest.fixture
def client():
    return TestClient(app)


def _auth(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def register(client):
    def _register(email, role="buyer", name=None):
        r = client.post(
            "/api/auth/register",
            json={"email": email, "password": "password123", "role": role, "full_name": name or email},
        )
        assert r.status_code == 201, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}, r.json()["user"]

    return _register


@pytest.fixture
def admin(client):
    return _auth(client, "admin@test.md", "adminpass1")


@pytest.fixture
def refs(client, admin):
    ids = {}
    for key, path, name in (
        ("artist", "artists", "Елена Русу"),
        ("artist2", "artists", "Андрей Чебан"),
        ("style", "styles", "Реализм"),
        ("style2", "styles", "Абстракционизм"),
        ("technique", "techniques", "Масло, холст"),
        ("city", "cities", "Кишинёв"),
    ):
        r = client.post(f"/api/{path}", json={"name": name}, headers=admin)
        assert r.status_code == 201, r.text
        ids[key] = r.json()["id"]
    return ids


@pytest.fixture
def make_artwork(client, refs):
    def _make(headers, **overrides):
        payload = {
            "title": "Рассвет",
            "artist_id": refs["artist"],
            "style_id": refs["style"],
            "technique_id": refs["technique"],
            "city_id": refs["city"],
            "year_created": 2020,
            "price": "1200.00",
            "condition": "excellent",
            "details": {"width_cm": "80", "height_cm": "60", "description": "Описание"},
        }
        payload.update(overrides)
        r = client.post("/api/artworks", json=payload, headers=headers)
        assert r.status_code == 201, r.text
        return r.json()

    return _make
