"""统一错误响应、安全响应头与健康检查。"""
import io

from tests.support import export_rows


def test_unknown_api_returns_json_404(client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.is_json
    assert response.get_json()["error"]


def test_method_not_allowed_returns_json(client):
    response = client.delete("/api/contacts")
    assert response.status_code == 405
    assert response.is_json
    assert response.get_json()["error"]


def test_page_404_keeps_html(client):
    response = client.get("/missing-page")
    assert response.status_code == 404
    assert not response.is_json


def test_upload_too_large_is_reported(client):
    big = io.BytesIO(b"x" * (6 * 1024 * 1024))
    response = client.post(
        "/api/contacts/import",
        data={"file": (big, "big.xlsx")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 413
    assert response.is_json
    assert "5 MiB" in response.get_json()["error"]


def test_security_headers(client):
    response = client.get("/api/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cache-Control"] == "no-store"

    page = client.get("/")
    assert page.headers["X-Content-Type-Options"] == "nosniff"


def test_health_stats_follow_data(client, make_contact):
    make_contact("甲", favorite=True, methods=[{"kind": "mobile", "value": "13800000000"}])
    removed = make_contact("乙")
    client.delete(f"/api/contacts/{removed['id']}")

    stats = client.get("/api/health").get_json()["stats"]
    assert stats == {"total": 1, "favorites": 1, "methods": 1, "trash": 1}


def test_export_can_include_trash(client, make_contact):
    contact = make_contact("待删除的人", methods=[{"kind": "mobile", "value": "13800000003"}])
    make_contact("正常的人")
    client.delete(f"/api/contacts/{contact['id']}")

    normal_rows = export_rows(client)
    assert [row[0] for row in normal_rows] == ["正常的人"]

    trash_rows = export_rows(client, {"trash": 1})
    assert [row[0] for row in trash_rows] == ["待删除的人"]


def test_update_rejects_trashed_contact(client, make_contact, contact_payload):
    contact = make_contact("被删除的人")
    client.delete(f"/api/contacts/{contact['id']}")
    payload = {**contact_payload, "name": "被删除的人"}
    assert client.put(f"/api/contacts/{contact['id']}", json=payload).status_code == 404
    assert client.post(f"/api/contacts/{contact['id']}/restore").status_code == 200
    assert client.put(f"/api/contacts/{contact['id']}", json=payload).status_code == 200
