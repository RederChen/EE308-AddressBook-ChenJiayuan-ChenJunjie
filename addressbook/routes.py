from flask import Blueprint, current_app, jsonify, render_template, request, send_file

from . import repository
from .excel import export_workbook, parse_workbook, template_workbook
from .validation import validate_contact


bp = Blueprint("addressbook", __name__)


def _json_payload():
    payload = request.get_json(silent=True)
    if payload is None:
        raise ValueError("请发送有效的 JSON 请求")
    return payload


@bp.get("/")
def index():
    return render_template("index.html")


@bp.get("/api/health")
def health():
    return jsonify({"status": "ok", "application": "拾光通讯录"})


@bp.get("/api/contacts")
def contacts_list():
    query = request.args.get("query", "").strip()
    favorite_only = request.args.get("favorite", "").lower() in {"1", "true", "yes"}
    return jsonify({"contacts": repository.list_contacts(query, favorite_only), "stats": repository.stats()})


@bp.post("/api/contacts")
def contacts_create():
    try:
        data = validate_contact(_json_payload())
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    return jsonify(repository.create_contact(data)), 201


@bp.get("/api/contacts/<int:contact_id>")
def contacts_detail(contact_id):
    contact = repository.get_contact(contact_id)
    if contact is None:
        return jsonify({"error": "联系人不存在"}), 404
    return jsonify(contact)


@bp.put("/api/contacts/<int:contact_id>")
def contacts_update(contact_id):
    try:
        data = validate_contact(_json_payload())
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    contact = repository.update_contact(contact_id, data)
    if contact is None:
        return jsonify({"error": "联系人不存在"}), 404
    return jsonify(contact)


@bp.patch("/api/contacts/<int:contact_id>/favorite")
def contacts_favorite(contact_id):
    payload = request.get_json(silent=True) or {}
    favorite = payload.get("favorite") if "favorite" in payload else None
    if favorite is not None and not isinstance(favorite, bool):
        return jsonify({"error": "favorite 必须是布尔值"}), 400
    contact = repository.set_favorite(contact_id, favorite)
    if contact is None:
        return jsonify({"error": "联系人不存在"}), 404
    return jsonify(contact)


@bp.delete("/api/contacts/<int:contact_id>")
def contacts_delete(contact_id):
    if not repository.delete_contact(contact_id):
        return jsonify({"error": "联系人不存在"}), 404
    return "", 204


@bp.get("/api/contacts/export")
def contacts_export():
    stream = export_workbook(repository.list_contacts())
    return send_file(
        stream,
        as_attachment=True,
        download_name="拾光通讯录.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@bp.get("/api/contacts/template")
def contacts_template():
    return send_file(
        template_workbook(),
        as_attachment=True,
        download_name="通讯录导入模板.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@bp.post("/api/contacts/import")
def contacts_import():
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return jsonify({"error": "请选择要导入的 Excel 文件"}), 400
    if not upload.filename.lower().endswith(".xlsx"):
        return jsonify({"error": "仅支持 .xlsx 格式，不支持 .xls 或 CSV"}), 400
    try:
        records, errors = parse_workbook(upload.stream)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    if errors:
        return jsonify({"error": "导入已取消，未写入任何数据", "details": errors}), 400
    if not records:
        return jsonify({"error": "工作簿中没有可导入的联系人"}), 400
    result = repository.import_contacts(records)
    result["stats"] = repository.stats()
    return jsonify(result)


@bp.app_errorhandler(413)
def file_too_large(_error):
    return jsonify({"error": "文件超过 5 MiB 大小限制"}), 413
