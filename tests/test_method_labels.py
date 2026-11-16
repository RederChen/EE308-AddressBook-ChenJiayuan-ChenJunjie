"""V1.1 contact method label and compatibility regression tests."""

import sqlite3
from io import BytesIO

from openpyxl import Workbook, load_workbook

from addressbook import create_app
from addressbook.excel import HEADERS, LABEL_HEADERS, LABEL_SHEET


def test_create_multiple_independent_labels(client):
    methods = [
        {"kind": "mobile", "value": "13800000000", "label": "工作"},
        {"kind": "mobile", "value": "13900000000", "label": "个人"},
        {"kind": "email", "value": "a@example.com", "label": "学校"},
        {"kind": "wechat", "value": "wx_a", "label": "家庭"},
        {"kind": "qq", "value": "123456", "label": "社团"},
        {"kind": "weibo", "value": "weibo_a", "label": "公开"},
    ]
    response = client.post("/api/contacts", json={"name": "王同学", "methods": methods})
    assert response.status_code == 201
    contact_id = response.get_json()["id"]
    assert [(m["kind"], m["label"]) for m in response.get_json()["methods"]] == [
        (m["kind"], m["label"]) for m in methods
    ]
    assert [m["label"] for m in client.get(f"/api/contacts/{contact_id}").get_json()["methods"]] == [
        m["label"] for m in methods
    ]


def test_edit_changes_one_label_and_preserves_others(client, contact_payload):
    created = client.post("/api/contacts", json=contact_payload).get_json()
    contact_payload["methods"][0]["label"] = "新工作"
    response = client.put(f"/api/contacts/{created['id']}", json=contact_payload)
    assert response.status_code == 200
    assert [m["label"] for m in response.get_json()["methods"]] == ["新工作", "个人", "", ""]
    # Reopening and saving an unchanged editor payload must not erase labels.
    unchanged = response.get_json()
    response = client.put(f"/api/contacts/{created['id']}", json=unchanged)
    assert [m["label"] for m in response.get_json()["methods"]] == ["新工作", "个人", "", ""]


def test_optional_and_blank_labels(client):
    payload = {"name": "无标签", "methods": [
        {"kind": "phone", "value": "0591-123456"},
        {"kind": "email", "value": "x@example.com", "label": "  "},
        {"kind": "qq", "value": "  ", "label": "忽略空行"},
    ]}
    contact = client.post("/api/contacts", json=payload).get_json()
    assert [m["label"] for m in contact["methods"]] == ["", ""]
    assert len(contact["methods"]) == 2


def test_label_validation_does_not_change_original(client, contact_payload):
    created = client.post("/api/contacts", json=contact_payload).get_json()
    contact_payload["methods"][0]["label"] = "x" * 31
    response = client.put(f"/api/contacts/{created['id']}", json=contact_payload)
    assert response.status_code == 400
    assert client.get(f"/api/contacts/{created['id']}").get_json()["methods"][0]["label"] == "工作"


def test_preexisting_row_without_explicit_label(app, client):
    with app.app_context():
        from addressbook.db import get_db

        db = get_db()
        db.execute("INSERT INTO contacts (name) VALUES (?)", ("旧联系人",))
        db.execute(
            "INSERT INTO contact_methods (contact_id, kind, value) VALUES (1, 'mobile', '13800000000')"
        )
        db.commit()
    old = client.get("/api/contacts/1").get_json()
    assert old["methods"][0]["label"] == ""
    updated = client.put("/api/contacts/1", json={"name": "旧联系人", "methods": old["methods"]})
    assert updated.status_code == 200
    assert updated.get_json()["methods"][0]["label"] == ""


def test_database_without_label_column_is_migrated(tmp_path):
    database = tmp_path / "legacy.db"
    with sqlite3.connect(database) as db:
        db.executescript("""
            CREATE TABLE contacts (id INTEGER PRIMARY KEY, name TEXT NOT NULL,
                favorite INTEGER NOT NULL DEFAULT 0, notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE contact_methods (id INTEGER PRIMARY KEY, contact_id INTEGER NOT NULL,
                kind TEXT NOT NULL, value TEXT NOT NULL, sort_order INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE);
            INSERT INTO contacts (id, name) VALUES (1, '旧数据库');
            INSERT INTO contact_methods (contact_id, kind, value) VALUES (1, 'wechat', 'old_wx');
        """)
    app = create_app({"TESTING": True, "DATABASE": str(database)})
    client = app.test_client()
    contact = client.get("/api/contacts/1").get_json()
    assert contact["methods"][0]["label"] == ""
    assert client.put("/api/contacts/1", json={
        "name": "旧数据库", "methods": [{"kind": "wechat", "value": "old_wx", "label": "个人"}]
    }).get_json()["methods"][0]["label"] == "个人"


def test_excel_round_trip_preserves_labels_and_original_columns(client, contact_payload):
    client.post("/api/contacts", json=contact_payload)
    data = client.get("/api/contacts/export").data
    book = load_workbook(BytesIO(data))
    assert [cell.value for cell in book.active[1]] == HEADERS
    assert LABEL_SHEET in book.sheetnames
    assert [cell.value for cell in book[LABEL_SHEET][1]] == LABEL_HEADERS
    client.delete("/api/contacts/1")
    imported = client.post("/api/contacts/import", data={"file": (BytesIO(data), "roundtrip.xlsx")})
    assert imported.status_code == 200
    assert [m["label"] for m in client.get("/api/contacts").get_json()["contacts"][0]["methods"]] == [
        "工作", "个人", "", ""
    ]


def test_excel_old_template_without_label_sheet_still_imports(client):
    book = Workbook()
    book.active.append(HEADERS)
    book.active.append(["旧表格", "否", "13800000000", "", "", "", "", "", "", "", ""])
    stream = BytesIO()
    book.save(stream)
    stream.seek(0)
    response = client.post("/api/contacts/import", data={"file": (stream, "old.xlsx")})
    assert response.status_code == 200
    assert client.get("/api/contacts").get_json()["contacts"][0]["methods"][0]["label"] == ""


def test_excel_rejects_stale_label_mapping_without_partial_import(client, contact_payload):
    client.post("/api/contacts", json=contact_payload)
    book = load_workbook(BytesIO(client.get("/api/contacts/export").data))
    book.active["C2"] = "changed-number"
    stream = BytesIO()
    book.save(stream)
    stream.seek(0)
    response = client.post("/api/contacts/import", data={"file": (stream, "stale.xlsx")})
    assert response.status_code == 400
    assert "不匹配" in response.get_json()["details"][0]
    assert client.get("/api/contacts").get_json()["stats"]["total"] == 1
