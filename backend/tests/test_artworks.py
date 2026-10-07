def test_roles_for_create(client, register, refs):
    buyer, _ = register("b@t.md", "buyer")
    payload = {"title": "X", "artist_id": refs["artist"], "price": "10"}
    assert client.post("/api/artworks", json=payload).status_code == 401
    assert client.post("/api/artworks", json=payload, headers=buyer).status_code == 403


def test_crud_and_ownership(client, register, make_artwork, refs, admin):
    s1, _ = register("s1@t.md", "seller")
    s2, _ = register("s2@t.md", "seller")
    art = make_artwork(s1)
    assert art["status"] == "available" and art["details"]["width_cm"] == "80.0"

    # чужой продавец не может менять / удалять
    assert client.put(f"/api/artworks/{art['id']}", json={"title": "Хак"}, headers=s2).status_code == 403
    assert client.delete(f"/api/artworks/{art['id']}", headers=s2).status_code == 403

    r = client.put(f"/api/artworks/{art['id']}", json={"title": "Новое", "price": "999.5", "details": {"description": "Обн."}}, headers=s1)
    assert r.status_code == 200
    assert r.json()["title"] == "Новое" and r.json()["price"] == "999.50"
    assert r.json()["details"]["description"] == "Обн." and r.json()["details"]["width_cm"] == "80.0"

    # продавец не может менять статус вручную, админ — может
    assert client.put(f"/api/artworks/{art['id']}", json={"status": "sold"}, headers=s1).status_code == 403
    assert client.put(f"/api/artworks/{art['id']}", json={"status": "sold"}, headers=admin).status_code == 200

    assert client.delete(f"/api/artworks/{art['id']}", headers=admin).status_code == 204
    assert client.get(f"/api/artworks/{art['id']}").status_code == 404


def test_validation(client, register, refs):
    s, _ = register("s@t.md", "seller")
    base = {"title": "X", "artist_id": refs["artist"], "price": "10"}
    assert client.post("/api/artworks", json={**base, "price": "-5"}, headers=s).status_code == 422
    assert client.post("/api/artworks", json={**base, "artist_id": 9999}, headers=s).status_code == 422
    assert client.post("/api/artworks", json={**base, "year_created": 3000}, headers=s).status_code == 422
    assert client.post("/api/artworks", json={**base, "title": "   "}, headers=s).status_code == 422


def test_catalog_filters_sort_pagination(client, register, make_artwork, refs):
    s, _ = register("s@t.md", "seller")
    make_artwork(s, title="Альфа", price="100", year_created=2001)
    make_artwork(s, title="Бета", price="500", artist_id=refs["artist2"], style_id=refs["style2"], details={"width_cm": "200", "height_cm": "100"})
    make_artwork(s, title="Гамма", price="900")

    def get(**params):
        r = client.get("/api/artworks", params=params)
        assert r.status_code == 200, r.text
        return r.json()

    assert get()["total"] == 3
    assert [i["title"] for i in get(sort="price_desc")["items"]] == ["Гамма", "Бета", "Альфа"]
    assert [i["title"] for i in get(sort="price_asc")["items"]][0] == "Альфа"
    assert get(artist_id=refs["artist2"])["total"] == 1
    assert get(style_id=refs["style2"])["items"][0]["title"] == "Бета"
    assert get(price_min=200, price_max=600)["total"] == 1
    assert get(width_min=150)["total"] == 1
    assert get(q="Русу")["total"] == 2          # поиск по художнику
    assert get(q="Альф")["total"] == 1          # поиск по названию
    assert get(q="100%")["total"] == 0          # спецсимволы LIKE экранируются
    assert get(city_id=refs["city"])["total"] == 3
    assert get(technique_id=refs["technique"])["total"] == 3

    page = get(page=2, page_size=2, sort="price_asc")
    assert page["total"] == 3 and page["pages"] == 2 and len(page["items"]) == 1
    assert client.get("/api/artworks", params={"sort": "bogus"}).status_code == 422


def test_my_artworks(client, register, make_artwork):
    s1, _ = register("s1@t.md", "seller")
    s2, _ = register("s2@t.md", "seller")
    make_artwork(s1)
    make_artwork(s2)
    make_artwork(s2)
    assert client.get("/api/artworks/mine", headers=s2).json()["total"] == 2
    buyer, _ = register("b@t.md")
    assert client.get("/api/artworks/mine", headers=buyer).status_code == 403


def test_photo_upload_flow(client, register, make_artwork):
    import io
    from PIL import Image

    s, _ = register("s@t.md", "seller")
    other, _ = register("o@t.md", "seller")
    art = make_artwork(s)

    def png(color):
        buf = io.BytesIO()
        Image.new("RGB", (40, 30), color).save(buf, "PNG")
        return buf.getvalue()

    url = f"/api/artworks/{art['id']}/photos"
    p1 = client.post(url, files={"file": ("a.png", png("red"), "image/png")}, headers=s)
    p2 = client.post(url, files={"file": ("b.png", png("blue"), "image/png")}, headers=s)
    assert p1.status_code == 201 and p2.status_code == 201
    assert p1.json()["url"].startswith("/uploads/") and p2.json()["position"] == 1

    assert client.post(url, files={"file": ("a.png", png("red"), "image/png")}, headers=other).status_code == 403
    assert client.post(url, files={"file": ("x.txt", b"not an image", "text/plain")}, headers=s).status_code == 415

    # файл раздаётся статикой
    assert client.get(p1.json()["url"]).status_code == 200

    # обложка
    r = client.post(f"/api/artworks/{art['id']}/photos/{p2.json()['id']}/cover", headers=s)
    assert r.status_code == 200 and r.json()[0]["id"] == p2.json()["id"]
    assert client.get(f"/api/artworks/{art['id']}").json()["photos"][0]["id"] == p2.json()["id"]

    assert client.delete(f"/api/artworks/{art['id']}/photos/{p1.json()['id']}", headers=s).status_code == 204
    assert len(client.get(f"/api/artworks/{art['id']}").json()["photos"]) == 1
