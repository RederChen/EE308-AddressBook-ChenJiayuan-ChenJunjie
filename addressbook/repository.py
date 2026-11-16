from .db import get_db


def _contact_from_row(row, methods):
    return {
        "id": row["id"],
        "name": row["name"],
        "favorite": bool(row["favorite"]),
        "notes": row["notes"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "methods": methods,
    }


def _attach_methods(contacts):
    if not contacts:
        return []
    db = get_db()
    ids = [contact["id"] for contact in contacts]
    placeholders = ",".join("?" for _ in ids)
    rows = db.execute(
        f"SELECT * FROM contact_methods WHERE contact_id IN ({placeholders}) ORDER BY sort_order, id",
        ids,
    ).fetchall()
    grouped = {contact_id: [] for contact_id in ids}
    for row in rows:
        grouped[row["contact_id"]].append(
            {"id": row["id"], "kind": row["kind"], "label": row["label"], "value": row["value"]}
        )
    return [_contact_from_row(contact, grouped[contact["id"]]) for contact in contacts]


def list_contacts(query="", favorite_only=False):
    sql = "SELECT * FROM contacts"
    clauses = []
    params = []
    if query:
        clauses.append(
            "(name LIKE ? OR notes LIKE ? OR EXISTS "
            "(SELECT 1 FROM contact_methods m WHERE m.contact_id = contacts.id AND m.value LIKE ?))"
        )
        keyword = f"%{query.strip()}%"
        params.extend([keyword, keyword, keyword])
    if favorite_only:
        clauses.append("favorite = 1")
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY favorite DESC, name COLLATE NOCASE, id"
    rows = get_db().execute(sql, params).fetchall()
    return _attach_methods(rows)


def get_contact(contact_id):
    row = get_db().execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()
    if row is None:
        return None
    return _attach_methods([row])[0]


def _insert_methods(contact_id, methods):
    get_db().executemany(
        "INSERT INTO contact_methods (contact_id, kind, label, value, sort_order) VALUES (?, ?, ?, ?, ?)",
        [
            (contact_id, method["kind"], method.get("label", ""), method["value"], index)
            for index, method in enumerate(methods)
        ],
    )


def create_contact(data):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO contacts (name, favorite, notes) VALUES (?, ?, ?)",
        (data["name"], int(data["favorite"]), data["notes"]),
    )
    contact_id = cursor.lastrowid
    _insert_methods(contact_id, data["methods"])
    db.commit()
    return get_contact(contact_id)


def update_contact(contact_id, data):
    db = get_db()
    cursor = db.execute(
        "UPDATE contacts SET name = ?, favorite = ?, notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (data["name"], int(data["favorite"]), data["notes"], contact_id),
    )
    if cursor.rowcount == 0:
        db.rollback()
        return None
    db.execute("DELETE FROM contact_methods WHERE contact_id = ?", (contact_id,))
    _insert_methods(contact_id, data["methods"])
    db.commit()
    return get_contact(contact_id)


def set_favorite(contact_id, favorite=None):
    db = get_db()
    if favorite is None:
        cursor = db.execute(
            "UPDATE contacts SET favorite = 1 - favorite, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (contact_id,),
        )
    else:
        cursor = db.execute(
            "UPDATE contacts SET favorite = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (int(bool(favorite)), contact_id),
        )
    if cursor.rowcount == 0:
        db.rollback()
        return None
    db.commit()
    return get_contact(contact_id)


def delete_contact(contact_id):
    db = get_db()
    cursor = db.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
    db.commit()
    return cursor.rowcount > 0


def stats():
    row = get_db().execute(
        "SELECT COUNT(*) AS total, COALESCE(SUM(favorite), 0) AS favorites FROM contacts"
    ).fetchone()
    methods = get_db().execute("SELECT COUNT(*) AS count FROM contact_methods").fetchone()["count"]
    return {"total": row["total"], "favorites": row["favorites"], "methods": methods}


def import_contacts(records):
    """Import all valid records atomically; skip duplicate names case-insensitively."""
    db = get_db()
    imported = 0
    skipped = []
    seen = set()
    try:
        for data in records:
            normalized_name = data["name"].casefold()
            exists = db.execute("SELECT 1 FROM contacts WHERE name = ? COLLATE NOCASE", (data["name"],)).fetchone()
            if normalized_name in seen or exists:
                skipped.append(data["name"])
                continue
            seen.add(normalized_name)
            cursor = db.execute(
                "INSERT INTO contacts (name, favorite, notes) VALUES (?, ?, ?)",
                (data["name"], int(data["favorite"]), data["notes"]),
            )
            _insert_methods(cursor.lastrowid, data["methods"])
            imported += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"imported": imported, "skipped": skipped}
