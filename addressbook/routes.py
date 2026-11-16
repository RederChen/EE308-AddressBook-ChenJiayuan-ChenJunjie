"""Web 页面与 JSON API 路由。"""
from flask import Blueprint, jsonify, render_template, request, send_file

from . import repository
from .excel import export_workbook, parse_workbook, template_workbook
from .validation import (
    ValidationError,
    validate_contact,
    validate_ids,
    validate_mode,
    validate_paging,
    validate_sort,
)

bp = Blueprint("addressbook", __name__)

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
EXPORT_NAME = "拾光通讯录.xlsx"
TEMPLATE_NAME = "通讯录导入模板.xlsx"
BULK_ACTIONS = {"favorite", "unfavorite", "delete", "restore", "purge"}


def _json_payload():
    payload = request.get_json(silent=True)
    if payload is None:
        raise ValidationError("请发送有效的 JSON 请求")
    return payload


def _error(message, status=400, details=None):
    body = {"error": message}
    if details:
        body["details"] = details
    return jsonify(body), status


def _favorite_flag(value):
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


@bp.get("/")
def index():
    return render_template("index.html")


@bp.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "application": "拾光通讯录",
        "version": "1.3.0",
        "stats": repository.stats(),
    })


@bp.get("/api/contacts")
def list_contacts():
    try:
        query = request.args.get("query", "")
        favorite_only = _favorite_flag(request.args.get("favorite"))
        trash = _favorite_flag(request.args.get("trash"))
        sort = validate_sort(request.args.get("sort"))
        limit, offset = validate_paging(request.args.get("limit"), request.args.get("offset"))
    except ValidationError as exc:
        return _error(str(exc))

    result = repository.search_contacts(query, favorite_only, sort, limit, offset, trash)
    return jsonify({
        "contacts": result["contacts"],
        "total": result["total"],
        "has_more": result["has_more"],
        "limit": limit,
        "offset": offset,
        "sort": sort,
        "stats": repository.stats(),
    })


@bp.post("/api/contacts")
def create_contact():
    try:
        data = validate_contact(_json_payload())
    except ValidationError as exc:
        return _error(str(exc))
    contact = repository.create_contact(data)
    return jsonify(contact), 201


@bp.get("/api/contacts/<int:contact_id>")
def get_contact(contact_id):
    contact = repository.get_contact(contact_id)
    if contact is None:
        return _error("联系人不存在", 404)
    return jsonify(contact)


@bp.put("/api/contacts/<int:contact_id>")
def update_contact(contact_id):
    try:
        data = validate_contact(_json_payload())
    except ValidationError as exc:
        return _error(str(exc))
    contact = repository.update_contact(contact_id, data)
    if contact is None:
        return _error("联系人不存在", 404)
    return jsonify(contact)


@bp.delete("/api/contacts/<int:contact_id>")
def delete_contact(contact_id):
    if not repository.delete_contact(contact_id):
        return _error("联系人不存在", 404)
    return "", 204


@bp.patch("/api/contacts/<int:contact_id>/favorite")
def set_favorite(contact_id):
    payload = request.get_json(silent=True)
    payload = {} if payload is None else payload
    if not isinstance(payload, dict):
        return _error("请发送有效的 JSON 请求")

    favorite = None
    if "favorite" in payload:
        favorite = payload["favorite"]
        if not isinstance(favorite, bool):
            return _error("favorite 必须是布尔值")
    if not repository.set_favorite(contact_id, favorite):
        return _error("联系人不存在", 404)
    return jsonify(repository.get_contact(contact_id))


@bp.post("/api/contacts/<int:contact_id>/restore")
def restore_contact(contact_id):
    if not repository.restore_contact(contact_id):
        return _error("回收站中没有该联系人", 404)
    return jsonify(repository.get_contact(contact_id))


@bp.post("/api/contacts/bulk")
def bulk_contacts():
    try:
        payload = _json_payload()
        if not isinstance(payload, dict):
            raise ValidationError("请发送有效的 JSON 请求")
        action = payload.get("action")
        if action not in BULK_ACTIONS:
            raise ValidationError("不支持的批量操作")
        ids = validate_ids(payload.get("ids"))
    except ValidationError as exc:
        return _error(str(exc))
    affected = repository.bulk_action(action, ids)
    return jsonify({"action": action, "affected": affected, "stats": repository.stats()})


@bp.get("/api/trash")
def list_trash():
    contacts = repository.list_trash()
    return jsonify({"contacts": contacts, "total": len(contacts)})


@bp.delete("/api/trash/<int:contact_id>")
def purge_contact(contact_id):
    if not repository.purge_contact(contact_id):
        return _error("回收站中没有该联系人", 404)
    return "", 204


@bp.delete("/api/trash")
def empty_trash():
    return jsonify({"purged": repository.empty_trash(), "stats": repository.stats()})


@bp.get("/api/contacts/export")
def export_contacts():
    query = request.args.get("query", "")
    favorite_only = _favorite_flag(request.args.get("favorite"))
    trash = _favorite_flag(request.args.get("trash"))
    try:
        sort = validate_sort(request.args.get("sort"))
    except ValidationError as exc:
        return _error(str(exc))
    contacts = repository.list_contacts(query, favorite_only, sort, trash=trash)
    stream = export_workbook(contacts)
    return send_file(stream, as_attachment=True, download_name=EXPORT_NAME, mimetype=XLSX_MIME)


@bp.get("/api/contacts/template")
def download_template():
    return send_file(
        template_workbook(),
        as_attachment=True,
        download_name=TEMPLATE_NAME,
        mimetype=XLSX_MIME,
    )


def _read_upload():
    """读取并解析上传的 Excel；返回 (records, errors)，出错时返回错误响应。"""
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return None, _error("请选择要导入的 Excel 文件")
    if not uploaded.filename.lower().endswith(".xlsx"):
        return None, _error("仅支持 .xlsx 格式，不支持 .xls 或 CSV")
    try:
        records, errors = parse_workbook(uploaded.stream)
    except ValueError as exc:
        return None, _error(str(exc))
    return (records, errors), None


@bp.post("/api/contacts/import/preview")
def preview_import():
    try:
        mode = validate_mode(request.form.get("mode"))
    except ValidationError as exc:
        return _error(str(exc))
    parsed, failure = _read_upload()
    if failure is not None:
        return failure
    records, errors = parsed
    if errors:
        return _error("文件存在错误，请修正后再导入", details=errors)
    if not records:
        return _error("工作簿中没有可导入的联系人")
    preview = repository.preview_import(records, mode)
    preview["errors"] = []
    return jsonify(preview)


@bp.post("/api/contacts/import")
def import_contacts():
    parsed, failure = _read_upload()
    if failure is not None:
        return failure
    records, errors = parsed
    if errors:
        return _error("导入已取消，未写入任何数据", details=errors)
    if not records:
        return _error("工作簿中没有可导入的联系人")
    try:
        mode = validate_mode(request.form.get("mode"))
    except ValidationError as exc:
        return _error(str(exc))
    result = repository.import_contacts(records, mode)
    result["stats"] = repository.stats()
    return jsonify(result)
