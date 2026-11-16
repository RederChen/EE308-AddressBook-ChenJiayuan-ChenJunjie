from addressbook.db import get_db


def test_page_and_health(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "EverContact" in response.get_data(as_text=True)
    assert client.get("/api/health").get_json()["status"] == "ok"


def test_create_contact_with_multiple_methods(client, contact_payload):
    response = client.post("/api/contacts", json=contact_payload)
    assert response.status_code == 201
    contact = response.get_json()
    assert contact["name"] == "Alice Morgan"
    assert contact["favorite"] is True
    assert len(contact["methods"]) == 4
    assert [m["value"] for m in contact["methods"] if m["kind"] == "mobile"] == ["13800000000", "13900000000"]


def test_create_contact_rejects_empty_name_and_bad_kind(client, contact_payload):
    contact_payload["name"] = "  "
    response = client.post("/api/contacts", json=contact_payload)
    assert response.status_code == 400
    assert "Name" in response.get_json()["error"]
    contact_payload["name"] = "Valid Name"
    contact_payload["methods"] = [{"kind": "unknown", "value": "abc"}]
    assert client.post("/api/contacts", json=contact_payload).status_code == 400


def test_empty_method_rows_are_ignored(client, contact_payload):
    contact_payload["methods"].append({"kind": "email", "value": " "})
    contact = client.post("/api/contacts", json=contact_payload).get_json()
    assert len(contact["methods"]) == 4


def test_update_contact_replaces_methods_without_orphans(app, client, contact_payload):
    contact = client.post("/api/contacts", json=contact_payload).get_json()
    contact_payload["name"] = "Alice Morgan Updated"
    contact_payload["favorite"] = False
    contact_payload["methods"] = [{"kind": "wechat", "value": "alice_xp"}]
    response = client.put(f"/api/contacts/{contact['id']}", json=contact_payload)
    assert response.status_code == 200
    updated = response.get_json()
    assert updated["name"] == "Alice Morgan Updated"
    assert updated["favorite"] is False
    assert len(updated["methods"]) == 1
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM contact_methods").fetchone()[0] == 1


def test_favorite_toggle_and_filter(client, contact_payload):
    favorite = client.post("/api/contacts", json=contact_payload).get_json()
    contact_payload["name"] = "Regular Contact"
    contact_payload["favorite"] = False
    normal = client.post("/api/contacts", json=contact_payload).get_json()
    data = client.get("/api/contacts?favorite=1").get_json()
    assert data["stats"] == {"total": 2, "favorites": 1, "methods": 8}
    assert [item["id"] for item in data["contacts"]] == [favorite["id"]]
    toggled = client.patch(f"/api/contacts/{normal['id']}/favorite", json={}).get_json()
    assert toggled["favorite"] is True
    unchanged = client.patch(f"/api/contacts/{normal['id']}/favorite", json={"favorite": True}).get_json()
    assert unchanged["favorite"] is True
    assert client.patch("/api/contacts/999/favorite", json={}).status_code == 404


def test_search_matches_name_method_and_notes(client, contact_payload):
    client.post("/api/contacts", json=contact_payload)
    assert len(client.get("/api/contacts?query=Alice").get_json()["contacts"]) == 1
    assert len(client.get("/api/contacts?query=139000").get_json()["contacts"]) == 1
    assert len(client.get("/api/contacts?query=Project").get_json()["contacts"]) == 1
    assert len(client.get("/api/contacts?query=No Such Contact").get_json()["contacts"]) == 0


def test_delete_cascades_methods(app, client, contact_payload):
    contact = client.post("/api/contacts", json=contact_payload).get_json()
    assert client.delete(f"/api/contacts/{contact['id']}").status_code == 204
    assert client.get(f"/api/contacts/{contact['id']}").status_code == 404
    assert client.delete(f"/api/contacts/{contact['id']}").status_code == 404
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM contact_methods").fetchone()[0] == 0


def test_missing_and_invalid_requests(client):
    assert client.get("/api/contacts/999").status_code == 404
    assert client.put("/api/contacts/999", json={"name": "Missing Contact", "methods": []}).status_code == 404
    assert client.post("/api/contacts", data="not-json", content_type="application/json").status_code == 400
    assert client.patch("/api/contacts/1/favorite", json={"favorite": "yes"}).status_code == 400
