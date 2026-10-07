def test_admin_only_endpoints(client, register, admin):
    b, _ = register("b@t.md")
    s, _ = register("s@t.md", "seller")
    for path in ("/api/users", "/api/analytics/overview", "/api/analytics/by-artist", "/api/analytics/by-month"):
        assert client.get(path).status_code == 401
        assert client.get(path, headers=b).status_code == 403
        assert client.get(path, headers=s).status_code == 403
        assert client.get(path, headers=admin).status_code == 200
    assert client.get("/api/reservations", params={"as": "all"}, headers=b).status_code == 403
    assert client.get("/api/reservations", params={"as": "all"}, headers=admin).status_code == 200


def test_user_management(client, register, admin):
    _, user = register("u@t.md")
    users = client.get("/api/users", headers=admin).json()
    assert users["total"] == 2
    assert client.get("/api/users", params={"q": "u@t"}, headers=admin).json()["total"] == 1

    r = client.patch(f"/api/users/{user['id']}/role", json={"role": "seller"}, headers=admin)
    assert r.status_code == 200 and r.json()["role"] == "seller"

    me = client.get("/api/auth/me", headers=admin).json()
    assert client.patch(f"/api/users/{me['id']}/role", json={"role": "buyer"}, headers=admin).status_code == 400
    assert client.delete(f"/api/users/{me['id']}", headers=admin).status_code == 400
    assert client.delete(f"/api/users/{user['id']}", headers=admin).status_code == 204


def test_profile_update(client, register, refs):
    b, _ = register("b@t.md")
    r = client.put("/api/users/me/profile", json={"full_name": "Анна", "phone": "+373 69 000 000", "city_id": refs["city"]}, headers=b)
    assert r.status_code == 200
    assert r.json()["profile"]["city"]["name"] == "Кишинёв" and r.json()["profile"]["full_name"] == "Анна"
    assert client.put("/api/users/me/profile", json={"phone": "abc"}, headers=b).status_code == 422
    assert client.put("/api/users/me/profile", json={"city_id": 999}, headers=b).status_code == 422


def test_lookups_permissions(client, register, admin, refs):
    b, _ = register("b@t.md")
    s, _ = register("s@t.md", "seller")
    assert client.get("/api/artists").status_code == 200
    assert client.post("/api/artists", json={"name": "Novyi Master"}, headers=b).status_code == 403
    first = client.post("/api/artists", json={"name": "Novyi Master"}, headers=s)
    again = client.post("/api/artists", json={"name": "novyi master"}, headers=s)
    assert first.status_code == 201 and again.json()["id"] == first.json()["id"]
    assert client.put(f"/api/artists/{first.json()['id']}", json={"name": "Иной"}, headers=s).status_code == 403
    assert client.put(f"/api/artists/{first.json()['id']}", json={"name": "Иной"}, headers=admin).status_code == 200


def test_cannot_delete_used_lookup(client, register, make_artwork, refs, admin):
    s, _ = register("s@t.md", "seller")
    make_artwork(s)
    assert client.delete(f"/api/artists/{refs['artist']}", headers=admin).status_code == 409
    assert client.delete(f"/api/artists/{refs['artist2']}", headers=admin).status_code == 204


def test_analytics(client, register, make_artwork, refs, admin):
    s, _ = register("s@t.md", "seller")
    b, _ = register("b@t.md")
    a1 = make_artwork(s, price="1000")
    a2 = make_artwork(s, price="500", artist_id=refs["artist2"], style_id=refs["style2"])
    make_artwork(s, price="300")
    rid = client.post("/api/reservations", json={"artwork_id": a1["id"]}, headers=b).json()["id"]
    client.post(f"/api/reservations/{rid}/confirm", headers=s)
    client.post("/api/reservations", json={"artwork_id": a2["id"]}, headers=b)

    ov = client.get("/api/analytics/overview", headers=admin).json()
    assert ov["artworks_total"] == 3 and ov["artworks_by_status"] == {"available": 1, "reserved": 1, "sold": 1}
    assert ov["reservations_by_status"]["confirmed"] == 1 and ov["sold_value"] == "1000.00"
    assert ov["users_by_role"] == {"buyer": 1, "seller": 1, "admin": 1}

    by_artist = {r["name"]: r for r in client.get("/api/analytics/by-artist", headers=admin).json()}
    assert by_artist["Елена Русу"]["artworks_count"] == 2 and by_artist["Елена Русу"]["sold_count"] == 1
    assert by_artist["Елена Русу"]["total_value"] == "1300.00" and by_artist["Елена Русу"]["avg_price"] == "650.00"
    assert by_artist["Андрей Чебан"]["artworks_count"] == 1

    assert client.get("/api/analytics/by-style", headers=admin).status_code == 200
    by_city = client.get("/api/analytics/by-city", headers=admin).json()
    assert by_city[0]["name"] == "Кишинёв" and by_city[0]["artworks_count"] == 3

    months = client.get("/api/analytics/by-month", params={"months": 3}, headers=admin).json()
    assert len(months) == 3 and months[-1]["listed_count"] == 3
    assert months[-1]["sold_count"] == 1 and months[-1]["sold_value"] == "1000.00"
    assert months[-1]["reservations_count"] == 2
