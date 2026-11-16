"""Excel 导入导出：表头、行式布局、标签工作表、原子导入与转义。"""
import io

from openpyxl import load_workbook

from addressbook.excel import LABEL_HEADERS, LABEL_SHEET
from tests.support import HEADERS, export_rows, exported_workbook, upload, workbook_stream


def purge_all(client):
    payload = client.get("/api/contacts").get_json()
    ids = [item["id"] for item in payload["contacts"]]
    if ids:
        client.post("/api/contacts/bulk", json={"action": "delete", "ids": ids})
        client.post("/api/contacts/bulk", json={"action": "purge", "ids": ids})


def test_export_has_one_row_per_contact_and_labeled_columns(client, contact_payload, make_contact):
    client.post("/api/contacts", json=contact_payload)
    make_contact("周予川", notes="摄影社社长", methods=[{"kind": "wechat", "value": "zyc"}])

    book = exported_workbook(client)
    sheet = book["通讯录"]
    assert sheet.max_row == 3
    assert [cell.value for cell in sheet[1]] == HEADERS
    assert sheet.freeze_panes == "A2"

    first = [cell.value for cell in sheet[2]]
    assert first[0] == "林小满"
    assert first[1] == "是"
    assert first[2] == "13800000000；13900000000"
    assert first[4] == "xiaoman@example.com"
    assert first[8] == "福建省福州市"
    assert first[10] == "项目组同学"

    label_sheet = book[LABEL_SHEET]
    label_rows = [list(row) for row in label_sheet.iter_rows(min_row=2, values_only=True)]
    assert [cell.value for cell in label_sheet[1]] == LABEL_HEADERS
    assert label_rows == [
        [2, "手机", 1, "13800000000", "工作"],
        [2, "手机", 2, "13900000000", "个人"],
    ]


def test_export_without_labels_has_no_label_sheet(client, make_contact):
    make_contact("无标签", methods=[{"kind": "mobile", "value": "13900000001"}])
    book = exported_workbook(client)
    assert LABEL_SHEET not in book.sheetnames


def test_template_download_is_valid(client):
    response = client.get("/api/contacts/template")
    assert response.status_code == 200
    book = load_workbook(io.BytesIO(response.data))
    sheet = book["通讯录"]
    assert sheet.max_row == 2
    assert [cell.value for cell in sheet[1]] == HEADERS
    assert "示例" in sheet.cell(row=2, column=1).value
    assert sheet.freeze_panes == "A2"


def test_import_multiple_methods_and_duplicate_names(client, contact_payload):
    client.post("/api/contacts", json=contact_payload)
    stream = workbook_stream([
        ["林小满", "是", "13800000000", "", "", "", "", "", "", "", ""],
        ["新同事", "否", "13700000000", "", "new@example.com", "", "", "", "", "", ""],
        ["新同事", "否", "13600000000", "", "", "", "", "", "", "", ""],
    ])
    response = upload(client, stream)
    assert response.status_code == 200, response.get_data(as_text=True)
    result = response.get_json()
    assert result["imported"] == 1
    assert result["updated"] == 0
    assert sorted(result["skipped"]) == ["新同事", "林小满"]
    assert result["stats"]["total"] == 2
    assert result["stats"]["methods"] == 6


def test_import_skips_existing_name_case_insensitively(client, make_contact):
    make_contact("Alice", notes="原始备注")
    stream = workbook_stream([["alice", "否", "13900000000", "", "", "", "", "", "", "", ""]])
    result = upload(client, stream).get_json()
    assert result["imported"] == 0
    assert result["skipped"] == ["alice"]
    contact = client.get("/api/contacts").get_json()["contacts"][0]
    assert contact["name"] == "Alice"
    assert contact["notes"] == "原始备注"


def test_import_rejects_bad_row_atomically(client):
    stream = workbook_stream([
        ["第一位", "否", "13800000000", "", "", "", "", "", "", "", ""],
        ["第二位", "否", "13900000000", "", "", "", "", "", "", "", ""],
        ["", "否", "13700000000", "", "", "", "", "", "", "", ""],
    ])
    response = upload(client, stream)
    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "导入已取消，未写入任何数据"
    assert "第 4 行" in body["details"][0]
    assert client.get("/api/contacts").get_json()["stats"]["total"] == 0


def test_import_rejects_wrong_headers_and_file_type(client):
    wrong = workbook_stream([["某人", "否"]], headers=["名字", "收藏", "手机", "电话", "邮箱", "微信", "QQ", "微博", "地址", "其他联系方式", "备注"])
    response = upload(client, wrong)
    assert response.status_code == 400
    assert "表头" in response.get_json()["error"]

    csv_like = io.BytesIO("姓名,收藏\n某人,否\n".encode("utf-8"))
    response = upload(client, csv_like, filename="contacts.csv")
    assert response.status_code == 400
    assert ".xlsx" in response.get_json()["error"]

    response = client.post("/api/contacts/import", data={}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert "Excel" in response.get_json()["error"]


def test_import_rejects_invalid_favorite_and_empty_workbook(client):
    bad = workbook_stream([["某人", "也许", "", "", "", "", "", "", "", "", ""]])
    response = upload(client, bad)
    assert response.status_code == 400
    assert "收藏" in response.get_json()["details"][0]

    empty = workbook_stream([])
    response = upload(client, empty)
    assert response.status_code == 400
    assert "没有可导入" in response.get_json()["error"]


def test_export_import_round_trip_preserves_supported_fields(client, contact_payload):
    created = client.post("/api/contacts", json=contact_payload).get_json()
    exported = client.get("/api/contacts/export")
    assert exported.status_code == 200
    assert exported.headers["Content-Type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    purge_all(client)
    assert client.get("/api/contacts").get_json()["total"] == 0

    result = upload(client, io.BytesIO(exported.data)).get_json()
    assert result["imported"] == 1
    contact = client.get("/api/contacts").get_json()["contacts"][0]
    assert contact["id"] != created["id"]
    assert contact["name"] == contact_payload["name"]
    assert contact["favorite"] is True
    assert contact["notes"] == contact_payload["notes"]
    assert [(m["kind"], m["value"], m["label"]) for m in contact["methods"]] == [
        (m["kind"], m["value"], m["label"]) for m in contact_payload["methods"]
    ]


def test_export_escapes_formula_injection_and_round_trips(client):
    contact = client.post("/api/contacts", json={
        "name": "=1+1",
        "favorite": False,
        "notes": "@SUM(A1)",
        "methods": [{"kind": "other", "value": "+86 100", "label": "-work"}],
    }).get_json()

    book = exported_workbook(client)
    row = [cell.value for cell in book["通讯录"][2]]
    assert row[0] == "'=1+1"
    assert row[10] == "'@SUM(A1)"
    label_row = [cell.value for cell in book[LABEL_SHEET][2]]
    assert label_row[3] == "'+86 100"
    assert label_row[4] == "'-work"

    exported = client.get("/api/contacts/export").data
    purge_all(client)
    assert contact["name"] == "=1+1"
    upload(client, io.BytesIO(exported))
    contacts = client.get("/api/contacts").get_json()["contacts"]
    assert len(contacts) == 1
    restored = contacts[0]
    assert restored["name"] == "=1+1"
    assert restored["notes"] == "@SUM(A1)"
    assert restored["methods"][0]["value"] == "+86 100"
    assert restored["methods"][0]["label"] == "-work"


def test_import_reports_row_limit(client):
    rows = [["联系人%d" % index, "否", "1380000%04d" % index] for index in range(2005)]
    response = upload(client, workbook_stream(rows))
    assert response.status_code == 400
    details = response.get_json()["details"]
    assert any("2000" in item for item in details)
    assert client.get("/api/contacts").get_json()["stats"]["total"] == 0


def test_export_respects_filters(client, make_contact):
    make_contact("收藏的人", favorite=True, methods=[{"kind": "mobile", "value": "13800000001"}])
    make_contact("普通的人", methods=[{"kind": "mobile", "value": "13800000002"}])

    favorite_rows = export_rows(client, {"favorite": 1})
    assert [row[0] for row in favorite_rows] == ["收藏的人"]

    query_rows = export_rows(client, {"query": "普通"})
    assert [row[0] for row in query_rows] == ["普通的人"]
