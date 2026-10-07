def test_register_login_me(client):
    r = client.post("/api/auth/register", json={"email": "Ana@Mail.md", "password": "password123", "full_name": "Ana"})
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["email"] == "ana@mail.md" and body["user"]["role"] == "buyer"
    assert "password" not in str(body)

    token = client.post("/api/auth/login", json={"email": "ana@mail.md", "password": "password123"}).json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["profile"]["full_name"] == "Ana"


def test_duplicate_email_and_bad_password(client):
    payload = {"email": "a@b.md", "password": "password123"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    assert client.post("/api/auth/register", json=payload).status_code == 409
    assert client.post("/api/auth/login", json={"email": "a@b.md", "password": "wrong-pass"}).status_code == 401
    assert client.post("/api/auth/register", json={"email": "c@d.md", "password": "short"}).status_code == 422


def test_cannot_self_register_admin(client):
    r = client.post("/api/auth/register", json={"email": "x@y.md", "password": "password123", "role": "admin"})
    assert r.status_code == 403


def test_password_is_hashed_with_bcrypt(client):
    from app.core.database import SessionLocal
    from app.models import User

    client.post("/api/auth/register", json={"email": "h@h.md", "password": "password123"})
    with SessionLocal() as db:
        user = db.query(User).filter_by(email="h@h.md").one()
        assert user.password_hash.startswith("$2") and len(user.password_hash) == 60


def test_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_swagger_form_login(client, admin):
    r = client.post("/api/auth/token", data={"username": "admin@test.md", "password": "adminpass1"})
    assert r.status_code == 200 and r.json()["token_type"] == "bearer"
