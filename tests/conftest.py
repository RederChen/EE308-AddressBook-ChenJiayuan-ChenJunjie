import pytest

from addressbook import create_app


@pytest.fixture()
def app(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db")})
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def contact_payload():
    return {
        "name": "Alice Morgan",
        "favorite": True,
        "notes": "Project team member",
        "methods": [
            {"kind": "mobile", "value": "13800000000", "label": "Work"},
            {"kind": "mobile", "value": "13900000000", "label": "Personal"},
            {"kind": "email", "value": "alice@example.com", "label": ""},
            {"kind": "address", "value": "Fuzhou, Fujian, China", "label": ""},
        ],
    }
