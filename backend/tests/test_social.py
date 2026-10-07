def test_favorites(client, register, make_artwork):
    s, _ = register("s@t.md", "seller")
    b, _ = register("b@t.md")
    art = make_artwork(s)

    assert client.get("/api/favorites").status_code == 401
    assert client.put(f"/api/favorites/{art['id']}", headers=b).status_code == 204
    assert client.put(f"/api/favorites/{art['id']}", headers=b).status_code == 204  # идемпотентно
    assert client.put("/api/favorites/9999", headers=b).status_code == 404

    favs = client.get("/api/favorites", headers=b).json()
    assert len(favs) == 1 and favs[0]["artwork"]["is_favorite"] is True

    assert client.get(f"/api/artworks/{art['id']}", headers=b).json()["is_favorite"] is True
    assert client.get(f"/api/artworks/{art['id']}").json()["is_favorite"] is False
    assert client.get("/api/artworks", headers=b).json()["items"][0]["is_favorite"] is True

    assert client.delete(f"/api/favorites/{art['id']}", headers=b).status_code == 204
    assert client.get("/api/favorites", headers=b).json() == []


def test_conversation_flow(client, register, make_artwork):
    s, seller = register("s@t.md", "seller", "Галерея")
    b, buyer = register("b@t.md", "buyer", "Покупатель")
    stranger, _ = register("x@t.md")
    art = make_artwork(s)

    # продавец не может писать сам себе
    assert client.post("/api/conversations", json={"artwork_id": art["id"], "content": "Привет"}, headers=s).status_code == 400

    r = client.post("/api/conversations", json={"artwork_id": art["id"], "content": "Есть ли сертификат?"}, headers=b)
    assert r.status_code == 201
    conv = r.json()
    assert conv["seller"]["id"] == seller["id"] and len(conv["messages"]) == 1

    # повторное обращение использует тот же диалог
    r2 = client.post("/api/conversations", json={"artwork_id": art["id"], "content": "И рама?"}, headers=b)
    assert r2.json()["id"] == conv["id"] and len(r2.json()["messages"]) == 2

    # продавец видит непрочитанные, затем читает
    assert client.get("/api/conversations/unread-count", headers=s).json() == {"unread": 2}
    lst = client.get("/api/conversations", headers=s).json()
    assert lst[0]["unread_count"] == 2 and lst[0]["last_message"]["content"] == "И рама?"
    detail = client.get(f"/api/conversations/{conv['id']}", headers=s)
    assert detail.status_code == 200
    assert client.get("/api/conversations/unread-count", headers=s).json() == {"unread": 0}

    assert client.post(f"/api/conversations/{conv['id']}/messages", json={"content": "Да, есть"}, headers=s).status_code == 201
    assert client.get("/api/conversations/unread-count", headers=b).json() == {"unread": 1}

    # посторонний не имеет доступа
    assert client.get(f"/api/conversations/{conv['id']}", headers=stranger).status_code == 403
    assert client.post(f"/api/conversations/{conv['id']}/messages", json={"content": "hi"}, headers=stranger).status_code == 403
    assert client.post(f"/api/conversations/{conv['id']}/messages", json={"content": "   "}, headers=b).status_code == 422
