from io import BytesIO

from openpyxl import Workbook, load_workbook

from addressbook.excel import HEADERS


def workbook_stream(rows, headers=None):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers or HEADERS)
    for row in rows:
        sheet.append(row)
    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return stream


def test_export_has_one_row_per_contact_and_labeled_columns(client, contact_payload):
    client.post("/api/contacts", json=contact_payload)
    contact_payload["name"] = "第二位联系人"
    contact_payload["methods"] = [{"kind": "email", "value": "second@example.com"}]
    client.post("/api/contacts", json=contact_payload)
    response = client.get("/api/contacts/export")
    assert response.status_code == 200
    assert response.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    workbook = load_workbook(BytesIO(response.data))
    sheet = workbook.active
    assert [cell.value for cell in sheet[1]] == HEADERS
    assert sheet.max_row == 3
    rows = list(sheet.iter_rows(min_row=2, values_only=True))
    first = next(row for row in rows if row[0] == "林小满")
    assert first[1] == "是"
    assert first[2] == "13800000000；13900000000"
    assert first[4] == "xiaoman@example.com"
    assert sheet.freeze_panes == "A2"


def test_template_download_is_valid(client):
    response = client.get("/api/contacts/template")
    workbook = load_workbook(BytesIO(response.data))
    assert [cell.value for cell in workbook.active[1]] == HEADERS
    assert workbook.active.max_row == 2


def test_import_multiple_methods_and_duplicate_names(client):
    rows = [
        ["林小满", "是", "13800000000；13900000000", "", "xiaoman@example.com", "xm", "", "", "福州", "", "同学"],
        ["陈以安", "否", "", "0591-1000000", "an@example.com;an2@example.com", "", "123456", "", "", "", ""],
        ["林小满", "否", "13700000000", "", "", "", "", "", "", "", "文件内重复"],
    ]
    response = client.post(
        "/api/contacts/import",
        data={"file": (workbook_stream(rows), "contacts.xlsx")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    result = response.get_json()
    assert result["imported"] == 2
    assert result["skipped"] == ["林小满"]
    contacts = client.get("/api/contacts").get_json()["contacts"]
    assert len(contacts) == 2
    xiaoman = next(contact for contact in contacts if contact["name"] == "林小满")
    assert len(xiaoman["methods"]) == 5
    assert xiaoman["favorite"] is True


def test_import_skips_existing_name_case_insensitively(client, contact_payload):
    client.post("/api/contacts", json=contact_payload)
    rows = [["林小满", "是", "13800000000", "", "", "", "", "", "", "", "不会覆盖"]]
    response = client.post(
        "/api/contacts/import", data={"file": (workbook_stream(rows), "contacts.xlsx")}, content_type="multipart/form-data"
    )
    assert response.get_json()["imported"] == 0
    assert response.get_json()["skipped"] == ["林小满"]
    assert client.get(f"/api/contacts/1").get_json()["notes"] == "项目组同学"


def test_import_rejects_bad_row_atomically(client):
    rows = [
        ["有效联系人", "是", "13800000000", "", "", "", "", "", "", "", ""],
        ["", "否", "13900000000", "", "", "", "", "", "", "", "缺少姓名"],
    ]
    response = client.post(
        "/api/contacts/import", data={"file": (workbook_stream(rows), "bad.xlsx")}, content_type="multipart/form-data"
    )
    assert response.status_code == 400
    assert "第 3 行" in response.get_json()["details"][0]
    assert client.get("/api/contacts").get_json()["stats"]["total"] == 0


def test_import_rejects_wrong_headers_and_file_type(client):
    response = client.post(
        "/api/contacts/import",
        data={"file": (workbook_stream([["张三"]], headers=["错误表头"]), "bad.xlsx")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "表头" in response.get_json()["error"]
    response = client.post(
        "/api/contacts/import", data={"file": (BytesIO(b"csv"), "contacts.csv")}, content_type="multipart/form-data"
    )
    assert response.status_code == 400
    assert ".xlsx" in response.get_json()["error"]


def test_import_rejects_invalid_favorite_and_empty_workbook(client):
    rows = [["张三", "也许", "", "", "", "", "", "", "", "", ""]]
    response = client.post(
        "/api/contacts/import", data={"file": (workbook_stream(rows), "bad.xlsx")}, content_type="multipart/form-data"
    )
    assert response.status_code == 400
    response = client.post(
        "/api/contacts/import", data={"file": (workbook_stream([]), "empty.xlsx")}, content_type="multipart/form-data"
    )
    assert response.status_code == 400
    assert "没有可导入" in response.get_json()["error"]


def test_export_import_round_trip_preserves_supported_fields(client, contact_payload):
    client.post("/api/contacts", json=contact_payload)
    exported = client.get("/api/contacts/export").data
    client.delete("/api/contacts/1")
    response = client.post(
        "/api/contacts/import", data={"file": (BytesIO(exported), "roundtrip.xlsx")}, content_type="multipart/form-data"
    )
    assert response.get_json()["imported"] == 1
    restored = client.get("/api/contacts").get_json()["contacts"][0]
    assert restored["name"] == contact_payload["name"]
    assert restored["favorite"] == contact_payload["favorite"]
    assert restored["notes"] == contact_payload["notes"]
    assert [method["value"] for method in restored["methods"]] == [method["value"] for method in contact_payload["methods"]]
