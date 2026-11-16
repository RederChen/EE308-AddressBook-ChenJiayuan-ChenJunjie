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
