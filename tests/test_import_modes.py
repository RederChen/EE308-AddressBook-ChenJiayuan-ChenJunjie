"""导入预检与重复策略：skip / overwrite、预检不写库。"""
import io

from tests.support import upload, workbook_stream

ROWS = [
    ["林小满", "是", "13800000000", "", "", "", "", "", "", "", "导入备注"],
    ["新同事", "否", "13700000000", "", "new@example.com", "", "", "", "", "", ""],
]


def test_preview_counts_without_writing(client, contact_payload):
    client.post("/api/contacts", json=contact_payload)
    response = upload(client, workbook_stream(ROWS), endpoint="/api/contacts/import/preview")
    assert response.status_code == 200, response.get_data(as_text=True)
    preview = response.get_json()
    assert preview["mode"] == "skip"
    assert preview["total"] == 2
    assert preview["create"] == 1
    assert preview["update"] == 0
    assert preview["skip"] == 1
    assert preview["created_names"] == ["新同事"]
    assert preview["skipped_names"] == ["林小满"]
    assert preview["errors"] == []
    assert client.get("/api/contacts").get_json()["stats"]["total"] == 1


def test_preview_overwrite_matches_actual_counts(client, contact_payload):
    client.post("/api/contacts", json=contact_payload)
    preview = upload(client, workbook_stream(ROWS), mode="overwrite",
                     endpoint="/api/contacts/import/preview").get_json()
    assert (preview["create"], preview["update"], preview["skip"]) == (1, 1, 0)
    result = upload(client, workbook_stream(ROWS), mode="overwrite").get_json()
    assert (result["imported"], result["updated"], result["skipped_count"]) == (1, 1, 0)


def test_preview_duplicate_rows_match_both_modes(client):
    rows = [
        ["同名人", "否", "13800000000"],
        ["同名人", "否", "13900000000"],
    ]
    for mode, counts in [("skip", (1, 0, 1)), ("overwrite", (1, 1, 0))]:
        preview = upload(client, workbook_stream(rows), mode=mode,
                         endpoint="/api/contacts/import/preview").get_json()
        assert (preview["create"], preview["update"], preview["skip"]) == counts
        assert client.get("/api/contacts").get_json()["total"] == 0


def test_preview_rejects_invalid_mode(client):
    response = upload(client, workbook_stream(ROWS), mode="invalid",
                      endpoint="/api/contacts/import/preview")
    assert response.status_code == 400


def test_preview_reports_row_errors(client):
    rows = [["缺名字的人", "否"], ["", "否", "13800000000"]]
    response = upload(client, workbook_stream(rows), endpoint="/api/contacts/import/preview")
    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "文件存在错误，请修正后再导入"
    assert any("第 3 行" in item for item in body["details"])


def test_preview_rejects_empty_workbook(client):
    response = upload(client, workbook_stream([]), endpoint="/api/contacts/import/preview")
    assert response.status_code == 400
    assert "没有可导入" in response.get_json()["error"]


def test_default_mode_skips_existing_contacts(client, contact_payload):
    created = client.post("/api/contacts", json=contact_payload).get_json()
    result = upload(client, workbook_stream(ROWS)).get_json()
    assert result["imported"] == 1
    assert result["updated"] == 0
    assert result["skipped"] == ["林小满"]
    assert result["skipped_count"] == 1

    contact = client.get(f"/api/contacts/{created['id']}").get_json()
    assert contact["notes"] == "项目组同学"
    assert len(contact["methods"]) == 4


def test_overwrite_mode_replaces_existing_contact(client, contact_payload):
    created = client.post("/api/contacts", json=contact_payload).get_json()
    result = upload(client, workbook_stream(ROWS), mode="overwrite").get_json()
    assert result["imported"] == 1
    assert result["updated"] == 1
    assert result["skipped"] == []

    contact = client.get(f"/api/contacts/{created['id']}").get_json()
    assert contact["name"] == "林小满"
    assert contact["notes"] == "导入备注"
    assert contact["favorite"] is True
    assert [(item["kind"], item["value"]) for item in contact["methods"]] == [("mobile", "13800000000")]
    assert client.get("/api/contacts").get_json()["stats"]["total"] == 2


def test_overwrite_mode_applies_last_duplicate_row(client):
    rows = [
        ["同名人", "否", "13800000000", "", "", "", "", "", "", "", "第一行"],
        ["同名人", "否", "13900000000", "", "", "", "", "", "", "", "第二行"],
    ]
    result = upload(client, workbook_stream(rows), mode="overwrite").get_json()
    assert result["imported"] == 1
    assert result["updated"] == 1
    contact = client.get("/api/contacts").get_json()["contacts"][0]
    assert contact["notes"] == "第二行"
    assert contact["methods"][0]["value"] == "13900000000"


def test_invalid_mode_is_rejected(client):
    response = upload(client, workbook_stream(ROWS), mode="explode")
    assert response.status_code == 400
    assert "重复处理方式" in response.get_json()["error"]
    assert client.get("/api/contacts").get_json()["stats"]["total"] == 0


def test_import_still_atomic_when_row_invalid(client):
    rows = [["好数据", "否", "13800000000"], ["坏数据", "也许"]]
    response = upload(client, workbook_stream(rows))
    assert response.status_code == 400
    assert client.get("/api/contacts").get_json()["stats"]["total"] == 0


def test_imported_contact_appears_in_trash_flow(client):
    upload(client, workbook_stream([["可删除", "否", "13800000000"]]))
    contact = client.get("/api/contacts").get_json()["contacts"][0]
    client.delete(f"/api/contacts/{contact['id']}")
    assert client.get("/api/contacts").get_json()["total"] == 0
    client.post(f"/api/contacts/{contact['id']}/restore")
    assert client.get("/api/contacts").get_json()["total"] == 1
