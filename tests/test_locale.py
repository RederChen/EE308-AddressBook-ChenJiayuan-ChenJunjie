"""当前项目采用中文界面；替代 V1.0 已失效的全英文界面测试。"""
from pathlib import Path

from addressbook import create_app


ROOT = Path(__file__).resolve().parents[1]


def test_chinese_brand_and_version_are_consistent(client):
    page = client.get("/")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "拾光通讯录 · v1.3.0" in html
    assert "XP 地址簿" not in html
    health = client.get("/api/health").get_json()
    assert health["application"] == "拾光通讯录"
    assert health["version"] == "1.3.0"


def test_import_requires_preview_in_browser():
    html = (ROOT / "addressbook/templates/index.html").read_text(encoding="utf-8")
    script = (ROOT / "addressbook/static/app.js").read_text(encoding="utf-8")
    assert 'id="confirm-import-button" type="submit" disabled' in html
    assert 'form.append("mode", mode)' in script
    assert 'file !== previewFile || selectedMode() !== previewMode' in script
    assert 'clearImportPreview();' in script


def test_database_location_can_be_configured_for_persistent_disk(monkeypatch, tmp_path):
    database = tmp_path / "storage" / "contacts.db"
    monkeypatch.setenv("ADDRESS_BOOK_DATABASE", str(database))
    app = create_app({"TESTING": True})
    assert app.config["DATABASE"] == str(database)
    assert database.is_file()
