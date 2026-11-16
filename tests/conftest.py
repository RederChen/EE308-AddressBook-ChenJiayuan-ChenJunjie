import sqlite3

import pytest

from addressbook import create_app


@pytest.fixture()
def app(tmp_path):
    application = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db")})
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    connection = sqlite3.connect(app.config["DATABASE"])
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    yield connection
    connection.close()


@pytest.fixture()
def make_contact(client):
    def factory(name="林小满", **overrides):
        payload = {"name": name, "favorite": False, "notes": "", "methods": []}
        payload.update(overrides)
        response = client.post("/api/contacts", json=payload)
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    return factory


@pytest.fixture()
def contact_payload():
    return {
        "name": "林小满",
        "favorite": True,
        "notes": "项目组同学",
        "methods": [
            {"kind": "mobile", "value": "13800000000", "label": "工作"},
            {"kind": "mobile", "value": "13900000000", "label": "个人"},
            {"kind": "email", "value": "xiaoman@example.com", "label": ""},
            {"kind": "address", "value": "福建省福州市", "label": ""},
        ],
    }
