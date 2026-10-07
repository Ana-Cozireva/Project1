def _status(client, art_id):
    return client.get(f"/api/artworks/{art_id}").json()["status"]


def test_reserve_confirm_flow(client, register, make_artwork):
    s, _ = register("s@t.md", "seller")
    b, _ = register("b@t.md")
    art = make_artwork(s)

    r = client.post("/api/reservations", json={"artwork_id": art["id"]}, headers=b)
    assert r.status_code == 201 and r.json()["status"] == "pending"
    assert _status(client, art["id"]) == "reserved"
    rid = r.json()["id"]

    # покупатель не может подтвердить сам
    assert client.post(f"/api/reservations/{rid}/confirm", headers=b).status_code == 403

    assert len(client.get("/api/reservations", headers=b).json()["items"]) == 1
    incoming = client.get("/api/reservations", params={"as": "seller"}, headers=s).json()
    assert incoming["total"] == 1 and incoming["items"][0]["buyer"]["full_name"]

    r = client.post(f"/api/reservations/{rid}/confirm", headers=s)
    assert r.status_code == 200 and r.json()["status"] == "confirmed" and r.json()["confirmed_at"]
    assert _status(client, art["id"]) == "sold"

    # после подтверждения менять нельзя
    assert client.post(f"/api/reservations/{rid}/cancel", headers=b).status_code == 409
    assert client.post(f"/api/reservations/{rid}/confirm", headers=s).status_code == 409
    assert client.put(f"/api/artworks/{art['id']}", json={"title": "x"}, headers=s).status_code == 409


def test_cancel_returns_artwork_to_sale(client, register, make_artwork):
    s, _ = register("s@t.md", "seller")
    b, _ = register("b@t.md")
    art = make_artwork(s)
    rid = client.post("/api/reservations", json={"artwork_id": art["id"]}, headers=b).json()["id"]

    r = client.post(f"/api/reservations/{rid}/cancel", headers=b)
    assert r.status_code == 200 and r.json()["status"] == "cancelled" and r.json()["cancelled_at"]
    assert _status(client, art["id"]) == "available"
    # и его можно снова забронировать
    assert client.post("/api/reservations", json={"artwork_id": art["id"]}, headers=b).status_code == 201


def test_seller_can_cancel_and_stranger_cannot(client, register, make_artwork):
    s, _ = register("s@t.md", "seller")
    b, _ = register("b@t.md")
    x, _ = register("x@t.md")
    art = make_artwork(s)
    rid = client.post("/api/reservations", json={"artwork_id": art["id"]}, headers=b).json()["id"]
    assert client.post(f"/api/reservations/{rid}/cancel", headers=x).status_code == 403
    assert client.post(f"/api/reservations/{rid}/cancel", headers=s).status_code == 200


def test_no_double_booking(client, register, make_artwork):
    s, _ = register("s@t.md", "seller")
    b1, _ = register("b1@t.md")
    b2, _ = register("b2@t.md")
    art = make_artwork(s)
    assert client.post("/api/reservations", json={"artwork_id": art["id"]}, headers=b1).status_code == 201
    assert client.post("/api/reservations", json={"artwork_id": art["id"]}, headers=b2).status_code == 409
    assert client.post("/api/reservations", json={"artwork_id": art["id"]}, headers=b1).status_code == 409


def test_cannot_reserve_own_or_missing(client, register, make_artwork):
    s, _ = register("s@t.md", "seller")
    art = make_artwork(s)
    assert client.post("/api/reservations", json={"artwork_id": art["id"]}, headers=s).status_code == 400
    assert client.post("/api/reservations", json={"artwork_id": 12345}, headers=s).status_code == 404
    assert client.post("/api/reservations", json={"artwork_id": art["id"]}).status_code == 401


def test_cannot_delete_reserved_artwork(client, register, make_artwork):
    s, _ = register("s@t.md", "seller")
    b, _ = register("b@t.md")
    art = make_artwork(s)
    client.post("/api/reservations", json={"artwork_id": art["id"]}, headers=b)
    assert client.delete(f"/api/artworks/{art['id']}", headers=s).status_code == 409
