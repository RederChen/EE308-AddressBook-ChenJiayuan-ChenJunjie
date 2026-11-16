from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .validation import validate_contact


HEADERS = ["Name", "Favorite", "Mobile", "Phone", "Email", "WeChat", "QQ", "Weibo", "Address", "Other Contact Methods", "Notes"]
KIND_COLUMNS = {
    "mobile": "Mobile",
    "phone": "Phone",
    "email": "Email",
    "wechat": "WeChat",
    "qq": "QQ",
    "weibo": "Weibo",
    "address": "Address",
    "other": "Other Contact Methods",
}
TRUE_VALUES = {"1", "true", "yes", "y", "favorite"}
FALSE_VALUES = {"", "0", "false", "no", "n", "not favorite"}


def _style_sheet(sheet):
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    widths = [20, 12, 28, 26, 32, 24, 20, 24, 38, 34, 38]
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="31572C")
        cell.alignment = Alignment(horizontal="center", vertical="center")
    sheet.row_dimensions[1].height = 26


def export_workbook(contacts):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Contacts"
    sheet.append(HEADERS)
    for contact in contacts:
        grouped = {header: [] for header in KIND_COLUMNS.values()}
        for method in contact["methods"]:
            header = KIND_COLUMNS.get(method["kind"], "Other Contact Methods")
            grouped[header].append(method["value"])
        row = [
            contact["name"],
            "Yes" if contact["favorite"] else "No",
            *[";".join(grouped[header]) for header in KIND_COLUMNS.values()],
            contact["notes"],
        ]
        sheet.append(row)
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    _style_sheet(sheet)
    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return stream


def template_workbook():
    empty_stream = export_workbook([])
    book = load_workbook(empty_stream)
    sheet = book.active
    sheet.append(["Sample Contact (delete this row)", "Yes", "13800000000;13900000000", "", "sample@example.com", "sample_contact", "", "", "Fuzhou, Fujian, China", "", "Import template example"])
    stream = BytesIO()
    book.save(stream)
    book.close()
    stream.seek(0)
    return stream


def _cell_text(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _split_values(value):
    normalized = _cell_text(value).replace("\r", "\n").replace("\n", ";")
    return [item.strip() for item in normalized.split(";") if item.strip()]


def parse_workbook(stream):
    """Return (valid contact records, row errors); no database writes occur here."""
    try:
        workbook = load_workbook(stream, read_only=True, data_only=True)
    except Exception as error:
        raise ValueError("Unable to read the file. Please upload a valid .xlsx workbook") from error

    sheet = workbook.active
    header_row = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), None)
    actual_headers = [_cell_text(value) for value in header_row] if header_row else []
    if actual_headers[: len(HEADERS)] != HEADERS:
        workbook.close()
        raise ValueError("Incompatible headers. Please download and use the Excel template provided by the application")

    records = []
    errors = []
    for row_number, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        values = [_cell_text(value) for value in row[: len(HEADERS)]]
        if not any(values):
            continue
        data = dict(zip(HEADERS, values))
        if not data["Name"]:
            errors.append(f"Row {row_number}: Name is required")
            continue
        favorite = data["Favorite"].casefold()
        if favorite not in TRUE_VALUES | FALSE_VALUES:
            errors.append(f"Row {row_number}: Favorite must be Yes or No")
            continue
        methods = []
        for kind, header in KIND_COLUMNS.items():
            for value in _split_values(data[header]):
                methods.append({"kind": kind, "value": value, "label": ""})
        try:
            record = validate_contact(
                {
                    "name": data["Name"],
                    "favorite": favorite in TRUE_VALUES,
                    "notes": data["Notes"],
                    "methods": methods,
                }
            )
            records.append(record)
        except ValueError as error:
            errors.append(f"Row {row_number}: {error}")
    workbook.close()
    return records, errors
