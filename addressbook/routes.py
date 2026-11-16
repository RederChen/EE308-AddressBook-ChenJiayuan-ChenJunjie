from flask import Blueprint, jsonify, render_template, request, send_file

from . import repository
from .excel import export_workbook, parse_workbook, template_workbook
from .validation import validate_contact


bp = Blueprint("addressbook", __name__)


def _json_payload():
    payload = request.get_json(silent=True)
    if payload is None:
        raise ValueError("Please send a valid JSON request")
    return payload


@bp.get("/")
def index():
    return render_template("index.html")


@bp.get("/api/health")
def health():
    return jsonify({"status": "ok", "application": "EverContact"})


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
        return jsonify({"error": "Contact not found"}), 404
    return jsonify(contact)


@bp.put("/api/contacts/<int:contact_id>")
def contacts_update(contact_id):
    try:
        data = validate_contact(_json_payload())
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    contact = repository.update_contact(contact_id, data)
    if contact is None:
        return jsonify({"error": "Contact not found"}), 404
    return jsonify(contact)


@bp.patch("/api/contacts/<int:contact_id>/favorite")
def contacts_favorite(contact_id):
    payload = request.get_json(silent=True) or {}
    favorite = payload.get("favorite") if "favorite" in payload else None
    if favorite is not None and not isinstance(favorite, bool):
        return jsonify({"error": "Favorite must be a boolean value"}), 400
    contact = repository.set_favorite(contact_id, favorite)
    if contact is None:
        return jsonify({"error": "Contact not found"}), 404
    return jsonify(contact)


@bp.delete("/api/contacts/<int:contact_id>")
def contacts_delete(contact_id):
    if not repository.delete_contact(contact_id):
        return jsonify({"error": "Contact not found"}), 404
    return "", 204


@bp.get("/api/contacts/export")
def contacts_export():
    stream = export_workbook(repository.list_contacts())
    return send_file(
        stream,
        as_attachment=True,
        download_name="EverContact.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@bp.get("/api/contacts/template")
def contacts_template():
    return send_file(
        template_workbook(),
        as_attachment=True,
        download_name="contact_import_template.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@bp.post("/api/contacts/import")
def contacts_import():
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return jsonify({"error": "Please select an Excel file to import"}), 400
    if not upload.filename.lower().endswith(".xlsx"):
        return jsonify({"error": "Only .xlsx files are supported; .xls and CSV files are not accepted"}), 400
    try:
        records, errors = parse_workbook(upload.stream)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    if errors:
        return jsonify({"error": "Import cancelled. No data was written", "details": errors}), 400
    if not records:
        return jsonify({"error": "The workbook contains no contacts to import"}), 400
    result = repository.import_contacts(records)
    result["stats"] = repository.stats()
    return jsonify(result)


@bp.app_errorhandler(413)
def file_too_large(_error):
    return jsonify({"error": "The file exceeds the 5 MiB size limit"}), 413
