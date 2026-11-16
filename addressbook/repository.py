"""数据访问层：联系人 CRUD、收藏、回收站、批量操作、搜索分页与 Excel 导入落库。"""
import sqlite3

from .db import get_db


# 白名单排序表达式，避免把用户输入直接拼进 SQL。
SORT_ORDERS = {
    "favorite": "c.favorite DESC, c.name COLLATE NOCASE, c.id",
    "name": "c.name COLLATE NOCASE, c.id",
    "recent": "c.updated_at DESC, c.id DESC",
    "created": "c.created_at DESC, c.id DESC",
}
TRASH_ORDER = "c.deleted_at DESC, c.id DESC"
DEFAULT_SORT = "favorite"

# SQLite 的 CURRENT_TIMESTAMP 只有秒级精度，快速连续编辑时「最近更新」排序会出现并列。
# 这里统一使用毫秒级 UTC 时间戳，前端 formatTime 可以直接解析。
NOW = "strftime('%Y-%m-%d %H:%M:%f', 'now')"


def escape_like(text):
    """转义 LIKE 通配符，让用户输入的 % 和 _ 按普通字符匹配。"""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _filters(query="", favorite_only=False, trash=False):
    clauses = ["c.deleted_at IS NOT NULL" if trash else "c.deleted_at IS NULL"]
    params = []
    if favorite_only:
        clauses.append("c.favorite = 1")
    keyword = (query or "").strip()
    if keyword:
        pattern = f"%{escape_like(keyword)}%"
        clauses.append(
            "(c.name LIKE ? ESCAPE '\\' OR c.notes LIKE ? ESCAPE '\\' "
            "OR EXISTS (SELECT 1 FROM contact_methods m WHERE m.contact_id = c.id "
            "AND (m.value LIKE ? ESCAPE '\\' OR m.label LIKE ? ESCAPE '\\')))"
        )
        params.extend([pattern] * 4)
    return " WHERE " + " AND ".join(clauses), params


def _contact_from_row(row, methods):
    return {
        "id": row["id"],
        "name": row["name"],
        "favorite": bool(row["favorite"]),
        "notes": row["notes"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "deleted_at": row["deleted_at"],
        "methods": methods,
    }


def _attach_methods(contacts):
    """一次查询补齐所有联系人的联系方式，避免 N+1。"""
    if not contacts:
        return contacts
    db = get_db()
    ids = [contact["id"] for contact in contacts]
    placeholders = ",".join("?" * len(ids))
    rows = db.execute(
        f"SELECT id, contact_id, kind, label, value, sort_order FROM contact_methods "
        f"WHERE contact_id IN ({placeholders}) ORDER BY contact_id, sort_order, id",
        ids,
    ).fetchall()
    grouped = {contact_id: [] for contact_id in ids}
    for row in rows:
        grouped[row["contact_id"]].append(
            {"id": row["id"], "kind": row["kind"], "label": row["label"], "value": row["value"]}
        )
    for contact in contacts:
        contact["methods"] = grouped.get(contact["id"], [])
    return contacts


def list_contacts(query="", favorite_only=False, sort=DEFAULT_SORT, limit=None, offset=0, trash=False):
    db = get_db()
    where, params = _filters(query, favorite_only, trash)
    order = TRASH_ORDER if trash else SORT_ORDERS.get(sort, SORT_ORDERS[DEFAULT_SORT])
    sql = f"SELECT c.* FROM contacts c{where} ORDER BY {order}"
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params = [*params, int(limit), int(offset)]
    rows = db.execute(sql, params).fetchall()
    return _attach_methods([_contact_from_row(row, []) for row in rows])


def count_contacts(query="", favorite_only=False, trash=False):
    db = get_db()
    where, params = _filters(query, favorite_only, trash)
    return db.execute(f"SELECT COUNT(*) FROM contacts c{where}", params).fetchone()[0]


def search_contacts(query="", favorite_only=False, sort=DEFAULT_SORT, limit=None, offset=0, trash=False):
    """带总数的分页查询，供列表接口使用。"""
    contacts = list_contacts(query, favorite_only, sort, limit, offset, trash)
    total = count_contacts(query, favorite_only, trash)
    return {"contacts": contacts, "total": total, "has_more": offset + len(contacts) < total}


def get_contact(contact_id, include_deleted=False):
    db = get_db()
    sql = "SELECT * FROM contacts WHERE id = ?"
    if not include_deleted:
        sql += " AND deleted_at IS NULL"
    row = db.execute(sql, (contact_id,)).fetchone()
    if row is None:
        return None
    return _attach_methods([_contact_from_row(row, [])])[0]


def _insert_methods(db, contact_id, methods):
    db.executemany(
        "INSERT INTO contact_methods (contact_id, kind, label, value, sort_order) VALUES (?, ?, ?, ?, ?)",
        [(contact_id, item["kind"], item.get("label", ""), item["value"], index)
         for index, item in enumerate(methods)],
    )


def create_contact(data):
    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO contacts (name, favorite, notes, created_at, updated_at) "
            f"VALUES (?, ?, ?, {NOW}, {NOW})",
            (data["name"], int(bool(data.get("favorite"))), data.get("notes", "")),
        )
        _insert_methods(db, cursor.lastrowid, data.get("methods", []))
        db.commit()
    except sqlite3.Error:
        db.rollback()
        raise
    return get_contact(cursor.lastrowid)


def update_contact(contact_id, data):
    db = get_db()
    try:
        cursor = db.execute(
            f"UPDATE contacts SET name = ?, favorite = ?, notes = ?, updated_at = {NOW} "
            "WHERE id = ? AND deleted_at IS NULL",
            (data["name"], int(bool(data.get("favorite"))), data.get("notes", ""), contact_id),
        )
        if cursor.rowcount == 0:
            db.rollback()
            return None
        db.execute("DELETE FROM contact_methods WHERE contact_id = ?", (contact_id,))
        _insert_methods(db, contact_id, data.get("methods", []))
        db.commit()
    except sqlite3.Error:
        db.rollback()
        raise
    return get_contact(contact_id)


def set_favorite(contact_id, favorite=None):
    """favorite 为 None 时切换收藏状态，否则显式设置。"""
    db = get_db()
    if favorite is None:
        cursor = db.execute(
            f"UPDATE contacts SET favorite = 1 - favorite, updated_at = {NOW} "
            "WHERE id = ? AND deleted_at IS NULL",
            (contact_id,),
        )
    else:
        cursor = db.execute(
            f"UPDATE contacts SET favorite = ?, updated_at = {NOW} "
            "WHERE id = ? AND deleted_at IS NULL",
            (int(bool(favorite)), contact_id),
        )
    db.commit()
    return cursor.rowcount > 0


def delete_contact(contact_id):
    """软删除：移入回收站，可撤销；彻底删除由 purge_contact 完成。"""
    db = get_db()
    cursor = db.execute(
        f"UPDATE contacts SET deleted_at = {NOW} WHERE id = ? AND deleted_at IS NULL",
        (contact_id,),
    )
    db.commit()
    return cursor.rowcount > 0


def restore_contact(contact_id):
    db = get_db()
    cursor = db.execute(
        f"UPDATE contacts SET deleted_at = NULL, updated_at = {NOW} "
        "WHERE id = ? AND deleted_at IS NOT NULL",
        (contact_id,),
    )
    db.commit()
    return cursor.rowcount > 0


def purge_contact(contact_id):
    """彻底删除（含联系方式级联），只能删除回收站中的联系人。"""
    db = get_db()
    cursor = db.execute("DELETE FROM contacts WHERE id = ? AND deleted_at IS NOT NULL", (contact_id,))
    db.commit()
    return cursor.rowcount > 0


def empty_trash():
    db = get_db()
    cursor = db.execute("DELETE FROM contacts WHERE deleted_at IS NOT NULL")
    db.commit()
    return cursor.rowcount


def list_trash():
    return list_contacts(trash=True)


def bulk_action(action, ids):
    """批量收藏 / 取消收藏 / 删除 / 恢复 / 彻底删除。"""
    if not ids:
        return 0
    db = get_db()
    placeholders = ",".join("?" * len(ids))
    if action == "favorite":
        cursor = db.execute(
            f"UPDATE contacts SET favorite = 1, updated_at = {NOW} "
            f"WHERE deleted_at IS NULL AND id IN ({placeholders})", ids)
    elif action == "unfavorite":
        cursor = db.execute(
            f"UPDATE contacts SET favorite = 0, updated_at = {NOW} "
            f"WHERE deleted_at IS NULL AND id IN ({placeholders})", ids)
    elif action == "delete":
        cursor = db.execute(
            f"UPDATE contacts SET deleted_at = {NOW} "
            f"WHERE deleted_at IS NULL AND id IN ({placeholders})", ids)
    elif action == "restore":
        cursor = db.execute(
            f"UPDATE contacts SET deleted_at = NULL, updated_at = {NOW} "
            f"WHERE deleted_at IS NOT NULL AND id IN ({placeholders})", ids)
    elif action == "purge":
        cursor = db.execute(f"DELETE FROM contacts WHERE deleted_at IS NOT NULL AND id IN ({placeholders})", ids)
    else:  # pragma: no cover - 由 validation 拦截
        raise ValueError("不支持的批量操作")
    db.commit()
    return cursor.rowcount


def stats():
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM contacts WHERE deleted_at IS NULL").fetchone()[0]
    favorites = db.execute(
        "SELECT COUNT(*) FROM contacts WHERE deleted_at IS NULL AND favorite = 1").fetchone()[0]
    methods = db.execute(
        "SELECT COUNT(*) FROM contact_methods m JOIN contacts c ON c.id = m.contact_id "
        "WHERE c.deleted_at IS NULL").fetchone()[0]
    trash = db.execute("SELECT COUNT(*) FROM contacts WHERE deleted_at IS NOT NULL").fetchone()[0]
    return {"total": total, "favorites": favorites, "methods": methods, "trash": trash}


def _existing_names(db, names):
    """返回 {小写姓名: 联系人 id}，只统计未删除联系人。"""
    lookup = {}
    if not names:
        return lookup
    placeholders = ",".join("?" * len(names))
    rows = db.execute(
        f"SELECT id, name FROM contacts WHERE deleted_at IS NULL AND name COLLATE NOCASE IN ({placeholders})",
        list(names),
    ).fetchall()
    for row in rows:
        lookup[row["name"].casefold()] = row["id"]
    return lookup


def _import_decision(key, known, seen, mode):
    """预检和正式导入共用同一套逐行规则。"""
    if mode == "skip" and (key in seen or key in known):
        return "skip"
    return "update" if key in known else "create"


def preview_import(records, mode="skip"):
    """按所选模式模拟整批导入，不写数据库。"""
    db = get_db()
    names = {record["name"] for record in records}
    known = _existing_names(db, names)
    created, updated, skipped = [], [], []
    seen = set()
    for record in records:
        key = record["name"].casefold()
        decision = _import_decision(key, known, seen, mode)
        {"create": created, "update": updated, "skip": skipped}[decision].append(record["name"])
        if decision == "create":
            known[key] = None  # 预检中的临时记录；再次出现会被判定为已存在
        seen.add(key)
    return {
        "mode": mode,
        "total": len(records),
        "create": len(created),
        "update": len(updated),
        "skip": len(skipped),
        "created_names": created[:10],
        "updated_names": updated[:10],
        "skipped_names": skipped[:10],
    }


def import_contacts(records, mode="skip"):
    """单事务整批导入。mode=skip 跳过同名；mode=overwrite 用文件内容覆盖同名联系人。

    整批写入要么全部成功，要么全部回滚，避免出现部分导入的中间状态。
    """
    db = get_db()
    imported, updated, skipped = 0, 0, []
    try:
        existing = _existing_names(db, {record["name"] for record in records})
        seen = set()
        for record in records:
            key = record["name"].casefold()
            decision = _import_decision(key, existing, seen, mode)
            seen.add(key)
            if decision == "skip":
                skipped.append(record["name"])
                continue
            contact_id = existing.get(key)
            methods = record.get("methods", [])
            if decision == "update":
                db.execute("DELETE FROM contact_methods WHERE contact_id = ?", (contact_id,))
                db.execute(
                    "UPDATE contacts SET name = ?, favorite = ?, notes = ?, "
                    f"updated_at = {NOW} WHERE id = ? AND deleted_at IS NULL",
                    (record["name"], int(bool(record.get("favorite"))),
                     record.get("notes", ""), contact_id),
                )
                _insert_methods(db, contact_id, methods)
                updated += 1
            else:
                cursor = db.execute(
                    "INSERT INTO contacts (name, favorite, notes) VALUES (?, ?, ?)",
                    (record["name"], int(bool(record.get("favorite"))), record.get("notes", "")),
                )
                _insert_methods(db, cursor.lastrowid, methods)
                existing[key] = cursor.lastrowid
                imported += 1
        db.commit()
    except sqlite3.Error:
        db.rollback()
        raise
    return {"imported": imported, "updated": updated,
            "skipped_count": len(skipped), "skipped": skipped[:50]}
