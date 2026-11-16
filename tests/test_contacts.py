"""联系人核心能力：增删改查、收藏、搜索、排序分页、回收站与批量操作。"""
from tests.support import contact_rows


def names(client, **params):
    return sorted(item["name"] for item in contact_rows(client, **params)["contacts"])


def test_page_and_health(client):
    page = client.get("/")
    assert page.status_code == 200
    assert "拾光通讯录" in page.get_data(as_text=True)

    health = client.get("/api/health").get_json()
    assert health["status"] == "ok"
    assert health["application"] == "拾光通讯录"
    assert health["version"] == "1.3.0"
    assert health["stats"] == {"total": 0, "favorites": 0, "methods": 0, "trash": 0}


def test_create_contact_with_multiple_methods(client, contact_payload):
    response = client.post("/api/contacts", json=contact_payload)
    assert response.status_code == 201
    contact = response.get_json()
    assert contact["name"] == "林小满"
    assert contact["favorite"] is True
    assert contact["notes"] == "项目组同学"
    assert len(contact["methods"]) == 4
    assert [item["label"] for item in contact["methods"]] == ["工作", "个人", "", ""]
    assert [item["value"] for item in contact["methods"] if item["kind"] == "mobile"] == [
        "13800000000",
        "13900000000",
    ]


def test_validation_rejects_invalid_payloads(client, contact_payload):
    cases = [
        ({**contact_payload, "name": "   "}, "姓名"),
        ({**contact_payload, "methods": [{"kind": "unknown", "value": "x"}]}, "类型"),
        ({**contact_payload, "favorite": "yes"}, "布尔"),
        ({**contact_payload, "notes": "长" * 501}, "500"),
        ({**contact_payload, "methods": [{"kind": "mobile", "value": "x" * 201}]}, "200"),
        ({**contact_payload, "methods": [{"kind": "mobile", "value": "x", "label": "标签" * 20}]}, "30"),
        ({**contact_payload, "methods": "not-a-list"}, "列表"),
    ]
    for payload, keyword in cases:
        response = client.post("/api/contacts", json=payload)
        assert response.status_code == 400, payload
        assert keyword in response.get_json()["error"]

    assert client.get("/api/contacts").get_json()["total"] == 0


def test_empty_method_rows_are_ignored(client):
    payload = {
        "name": "周予川",
        "methods": [
            {"kind": "mobile", "value": "  ", "label": "空行"},
            {"kind": "email", "value": "z@example.com"},
        ],
    }
    contact = client.post("/api/contacts", json=payload).get_json()
    assert len(contact["methods"]) == 1
    assert contact["methods"][0]["kind"] == "email"


def test_update_contact_replaces_methods_without_orphans(client, make_contact, db):
    contact = make_contact("林小满", notes="旧备注", methods=[{"kind": "mobile", "value": "13800000000"}])
    payload = {
        "name": "林小满",
        "favorite": True,
        "notes": "新备注",
        "methods": [{"kind": "email", "value": "new@example.com", "label": "常用"}],
    }
    response = client.put(f"/api/contacts/{contact['id']}", json=payload)
    assert response.status_code == 200
    updated = response.get_json()
    assert updated["notes"] == "新备注"
    assert updated["favorite"] is True
    assert len(updated["methods"]) == 1
    assert db.execute("SELECT COUNT(*) FROM contact_methods").fetchone()[0] == 1


def test_favorite_toggle_filter_and_stats(client, contact_payload, make_contact):
    client.post("/api/contacts", json=contact_payload)
    make_contact(
        "周予川",
        methods=[{"kind": "mobile", "value": str(13700000000 + index)} for index in range(5)],
    )

    payload = contact_rows(client)
    assert payload["stats"] == {"total": 2, "favorites": 1, "methods": 9, "trash": 0}

    favorite = payload["contacts"][0]
    assert favorite["name"] == "林小满"
    assert client.get("/api/contacts", query_string={"favorite": 1}).get_json()["total"] == 1

    switched = client.patch(f"/api/contacts/{favorite['id']}/favorite", json={})
    assert switched.status_code == 200
    assert switched.get_json()["favorite"] is False

    kept = client.patch(f"/api/contacts/{favorite['id']}/favorite", json={"favorite": True})
    assert kept.get_json()["favorite"] is True
    assert client.patch("/api/contacts/9999/favorite", json={}).status_code == 404


def test_search_matches_name_method_label_and_notes(client, contact_payload, make_contact):
    client.post("/api/contacts", json=contact_payload)
    make_contact("周予川", notes="摄影社社长", methods=[{"kind": "qq", "value": "5201314", "label": "摄影群"}])

    assert names(client, query="小满") == ["林小满"]
    assert names(client, query="139000") == ["林小满"]
    assert names(client, query="项目组") == ["林小满"]
    assert names(client, query="摄影") == ["周予川"]
    assert names(client, query="5201314") == ["周予川"]
    assert names(client, query="查无此人") == []


def test_search_treats_like_wildcards_literally(client, make_contact):
    for name in ["100% 折扣店", "折扣店", "a_b", "axb", "张三"]:
        make_contact(name)

    assert names(client, query="100%") == ["100% 折扣店"]
    assert names(client, query="%") == ["100% 折扣店"]
    assert names(client, query="a_b") == ["a_b"]
    assert names(client, query="_") == ["a_b"]
    assert names(client, query="axb") == ["axb"]


def test_sort_and_pagination(client, make_contact):
    for name in ["Charlie", "alice", "Bob"]:
        make_contact(name)

    by_name = contact_rows(client, sort="name")
    assert [item["name"] for item in by_name["contacts"]] == ["alice", "Bob", "Charlie"]

    first_page = contact_rows(client, sort="name", limit=2)
    assert [item["name"] for item in first_page["contacts"]] == ["alice", "Bob"]
    assert first_page["has_more"] is True
    assert first_page["total"] == 3

    second_page = contact_rows(client, sort="name", limit=2, offset=2)
    assert [item["name"] for item in second_page["contacts"]] == ["Charlie"]
    assert second_page["has_more"] is False

    assert client.get("/api/contacts", query_string={"limit": 0}).status_code == 400
    assert client.get("/api/contacts", query_string={"sort": "unknown"}).status_code == 400
    assert client.get("/api/contacts", query_string={"limit": "abc"}).status_code == 400


def test_sort_by_recent_puts_updated_first(client, make_contact, db):
    older = make_contact("先创建")
    newer = make_contact("后创建")
    # 直接改时间戳，避免依赖真实时钟（同一秒内创建的两条记录无法比较）
    db.execute("UPDATE contacts SET updated_at = '2020-01-01 00:00:00.000' WHERE id = ?", (newer["id"],))
    db.execute("UPDATE contacts SET updated_at = '2026-01-01 00:00:00.000' WHERE id = ?", (older["id"],))
    db.commit()

    ordered = contact_rows(client, sort="recent")["contacts"]
    assert [item["name"] for item in ordered] == ["先创建", "后创建"]


def test_soft_delete_restore_and_trash(client, make_contact, contact_payload, db):
    trashed = client.post("/api/contacts", json=contact_payload).get_json()
    keeper = make_contact("保留的人")

    assert client.delete(f"/api/contacts/{trashed['id']}").status_code == 204
    assert client.delete(f"/api/contacts/{trashed['id']}").status_code == 404
    assert [item["id"] for item in contact_rows(client)["contacts"]] == [keeper["id"]]
    assert contact_rows(client)["stats"]["trash"] == 1

    trash_payload = client.get("/api/trash").get_json()
    assert trash_payload["total"] == 1
    assert trash_payload["contacts"][0]["methods"]

    assert client.get(f"/api/contacts/{trashed['id']}").status_code == 404
    restored = client.post(f"/api/contacts/{trashed['id']}/restore")
    assert restored.status_code == 200
    assert len(restored.get_json()["methods"]) == 4
    assert client.post("/api/contacts/9999/restore").status_code == 404

    assert db.execute("SELECT COUNT(*) FROM contact_methods").fetchone()[0] == 4


def test_purge_and_empty_trash(client, make_contact, db):
    first = make_contact("甲")
    second = make_contact("乙")
    for contact in (first, second):
        client.delete(f"/api/contacts/{contact['id']}")

    assert client.delete(f"/api/trash/{first['id']}").status_code == 204
    assert client.delete(f"/api/trash/{first['id']}").status_code == 404
    assert client.get("/api/trash").get_json()["total"] == 1

    emptied = client.delete("/api/trash").get_json()
    assert emptied["purged"] == 1
    assert emptied["stats"]["trash"] == 0
    assert db.execute("SELECT COUNT(*) FROM contacts").fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM contact_methods").fetchone()[0] == 0


def test_bulk_actions(client, make_contact):
    first = make_contact("甲")
    second = make_contact("乙")
    ids = [first["id"], second["id"]]

    favorited = client.post("/api/contacts/bulk", json={"action": "favorite", "ids": ids})
    assert favorited.status_code == 200
    assert favorited.get_json()["affected"] == 2
    assert favorited.get_json()["stats"]["favorites"] == 2

    unfavorited = client.post("/api/contacts/bulk", json={"action": "unfavorite", "ids": ids})
    assert unfavorited.get_json()["stats"]["favorites"] == 0

    deleted = client.post("/api/contacts/bulk", json={"action": "delete", "ids": ids})
    assert deleted.get_json()["stats"]["trash"] == 2
    assert client.get("/api/contacts").get_json()["total"] == 0

    client.post("/api/contacts/bulk", json={"action": "restore", "ids": ids})
    assert client.get("/api/trash").get_json()["total"] == 0

    client.post("/api/contacts/bulk", json={"action": "delete", "ids": ids})
    purged = client.post("/api/contacts/bulk", json={"action": "purge", "ids": ids})
    assert purged.get_json()["stats"]["trash"] == 0


def test_bulk_action_rejects_bad_requests(client, make_contact):
    contact = make_contact()
    cases = [
        {"action": "explode", "ids": [contact["id"]]},
        {"action": "favorite", "ids": []},
        {"action": "favorite", "ids": ["1"]},
        {"action": "favorite", "ids": [0]},
        {"action": "favorite"},
    ]
    for payload in cases:
        response = client.post("/api/contacts/bulk", json=payload)
        assert response.status_code == 400, payload
        assert "error" in response.get_json()


def test_missing_and_invalid_requests(client, contact_payload):
    assert client.get("/api/contacts/9999").status_code == 404
    assert client.put("/api/contacts/9999", json=contact_payload).status_code == 404

    no_json = client.post("/api/contacts", data="not json", content_type="text/plain")
    assert no_json.status_code == 400
    assert "JSON" in no_json.get_json()["error"]

    bad_favorite = client.patch("/api/contacts/1/favorite", json={"favorite": "yes"})
    assert bad_favorite.status_code == 400
    assert "布尔" in bad_favorite.get_json()["error"]
