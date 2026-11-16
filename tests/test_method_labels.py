"""联系方式标签：多标签、编辑保留、校验、旧库迁移与 Excel 标签表。"""
import io
import sqlite3

from openpyxl import load_workbook

from addressbook import create_app
from addressbook.excel import LABEL_HEADERS, LABEL_SHEET
from tests.support import upload, workbook_stream

LEGACY_SCHEMA = """
CREATE TABLE contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    favorite INTEGER NOT NULL DEFAULT 0 CHECK (favorite IN (0, 1)),
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE contact_methods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    value TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);
"""


def labels_of(contact):
    return [item["label"] for item in contact["methods"]]


def test_create_multiple_independent_labels(client, contact_payload):
    contact = client.post("/api/contacts", json=contact_payload).get_json()
    assert labels_of(contact) == ["工作", "个人", "", ""]
    assert [item["value"] for item in contact["methods"]] == [
        "13800000000", "13900000000", "xiaoman@example.com", "福建省福州市"]


def test_edit_changes_one_label_and_preserves_others(client, contact_payload):
    contact = client.post("/api/contacts", json=contact_payload).get_json()
    payload = {
        "name": contact["name"],
        "favorite": contact["favorite"],
        "notes": contact["notes"],
        "methods": [
            {"kind": "mobile", "value": "13800000000", "label": "新工作"},
            {"kind": "mobile", "value": "13900000000", "label": "个人"},
            {"kind": "email", "value": "xiaoman@example.com", "label": ""},
            {"kind": "address", "value": "福建省福州市", "label": ""},
        ],
    }
    for _ in range(2):  # 连续保存两次也不能丢标签
        response = client.put(f"/api/contacts/{contact['id']}", json=payload)
        assert response.status_code == 200
        assert labels_of(response.get_json()) == ["新工作", "个人", "", ""]


def test_optional_and_blank_labels(client):
    payload = {
        "name": "周予川",
        "methods": [
            {"kind": "mobile", "value": "13700000000", "label": "   "},
            {"kind": "mobile", "value": "", "label": "空行标签"},
            {"kind": "email", "value": "zy@example.com"},
        ],
    }
    contact = client.post("/api/contacts", json=payload).get_json()
    assert labels_of(contact) == ["", ""]
    assert [item["kind"] for item in contact["methods"]] == ["mobile", "email"]


def test_label_validation_does_not_change_original(client, contact_payload):
    contact = client.post("/api/contacts", json=contact_payload).get_json()
    payload = {
        "name": contact["name"],
        "favorite": contact["favorite"],
        "notes": "",
        "methods": [
            {"kind": "mobile", "value": "13800000000", "label": "标" * 31},
            {"kind": "mobile", "value": "13900000000", "label": "个人"},
        ],
    }
    response = client.put(f"/api/contacts/{contact['id']}", json=payload)
    assert response.status_code == 400
    assert "30" in response.get_json()["error"]
    contact = client.get(f"/api/contacts/{contact['id']}").get_json()
    assert labels_of(contact) == ["工作", "个人", "", ""]


def test_preexisting_row_without_explicit_label(client, db):
    cursor = db.execute("INSERT INTO contacts (name, favorite, notes) VALUES ('老数据', 0, '')")
    contact_id = cursor.lastrowid
    db.execute(
        "INSERT INTO contact_methods (contact_id, kind, value, sort_order) VALUES (?, 'mobile', '13500000000', 0)",
        (contact_id,),
    )
    db.commit()

    contact = client.get(f"/api/contacts/{contact_id}").get_json()
    assert labels_of(contact) == [""]

    response = client.put(f"/api/contacts/{contact_id}", json={
        "name": "老数据",
        "favorite": False,
        "notes": "",
        "methods": [{"kind": "mobile", "value": "13500000000", "label": "个人"}],
    })
    assert response.status_code == 200
    assert labels_of(response.get_json()) == ["个人"]


def test_database_without_label_column_is_migrated(tmp_path):
    database = tmp_path / "legacy.db"
    connection = sqlite3.connect(database)
    connection.executescript(LEGACY_SCHEMA)
    cursor = connection.execute("INSERT INTO contacts (name, favorite, notes) VALUES ('旧版联系人', 1, '迁移')")
    contact_id = cursor.lastrowid
    connection.execute(
        "INSERT INTO contact_methods (contact_id, kind, value, sort_order) VALUES (?, 'mobile', '13500000001', 0)",
        (contact_id,),
    )
    connection.commit()
    connection.close()

    app = create_app({"TESTING": True, "DATABASE": str(database)})
    client = app.test_client()

    contact = client.get(f"/api/contacts/{contact_id}").get_json()
    assert labels_of(contact) == [""]
    assert contact["favorite"] is True

    response = client.put(f"/api/contacts/{contact_id}", json={
        "name": "旧版联系人",
        "favorite": True,
        "notes": "迁移",
        "methods": [{"kind": "mobile", "value": "13500000001", "label": "个人"}],
    })
    assert labels_of(response.get_json()) == ["个人"]
    assert client.get("/api/contacts").get_json()["stats"]["total"] == 1


def test_excel_round_trip_preserves_labels_and_original_columns(client, contact_payload):
    client.post("/api/contacts", json=contact_payload)
    exported = client.get("/api/contacts/export").data

    book = load_workbook(io.BytesIO(exported))
    assert [cell.value for cell in book[LABEL_SHEET][1]] == LABEL_HEADERS
    assert book["通讯录"]["C2"].value == "13800000000；13900000000"

    ids = [item["id"] for item in client.get("/api/contacts").get_json()["contacts"]]
    client.post("/api/contacts/bulk", json={"action": "delete", "ids": ids})
    client.post("/api/contacts/bulk", json={"action": "purge", "ids": ids})

    assert upload(client, io.BytesIO(exported)).status_code == 200
    contact = client.get("/api/contacts").get_json()["contacts"][0]
    assert labels_of(contact) == ["工作", "个人", "", ""]


def test_excel_old_template_without_label_sheet_still_imports(client):
    stream = workbook_stream([["无标签模板", "否", "13800000009", "", "", "", "", "", "", "", "备注"]])
    result = upload(client, stream).get_json()
    assert result["imported"] == 1
    contact = client.get("/api/contacts").get_json()["contacts"][0]
    assert labels_of(contact) == [""]


def test_excel_rejects_stale_label_mapping_without_partial_import(client, contact_payload):
    client.post("/api/contacts", json=contact_payload)
    exported = client.get("/api/contacts/export").data

    book = load_workbook(io.BytesIO(exported))
    book["通讯录"]["C2"] = "13000000000"  # 改了手机号，但标签表还指向旧号码
    stream = io.BytesIO()
    book.save(stream)
    stream.seek(0)

    response = upload(client, stream)
    assert response.status_code == 400
    body = response.get_json()
    assert "不匹配" in body["details"][0]
    assert client.get("/api/contacts").get_json()["stats"]["total"] == 1
