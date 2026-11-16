from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .validation import validate_contact


HEADERS = ["姓名", "收藏", "手机", "电话", "邮箱", "微信", "QQ", "微博", "地址", "其他联系方式", "备注"]
LABEL_SHEET = "联系方式标签"
LABEL_HEADERS = ["联系人行号", "方式类型", "同类型序号", "联系方式内容", "标签"]
KIND_COLUMNS = {
    "mobile": "手机",
    "phone": "电话",
    "email": "邮箱",
    "wechat": "微信",
    "qq": "QQ",
    "weibo": "微博",
    "address": "地址",
    "other": "其他联系方式",
}
TRUE_VALUES = {"是", "1", "true", "yes", "y", "★", "已收藏"}
FALSE_VALUES = {"", "否", "0", "false", "no", "n", "未收藏"}


def _style_sheet(sheet):
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    widths = [16, 10, 26, 24, 30, 22, 20, 22, 36, 30, 36]
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
    sheet.title = "通讯录"
    sheet.append(HEADERS)
    label_rows = []
    for contact in contacts:
        grouped = {header: [] for header in KIND_COLUMNS.values()}
        occurrences = {}
        for method in contact["methods"]:
            kind = method["kind"]
            header = KIND_COLUMNS.get(kind, "其他联系方式")
            grouped[header].append(method["value"])
            occurrences[kind] = occurrences.get(kind, 0) + 1
            if method.get("label"):
                label_rows.append([sheet.max_row + 1, kind, occurrences[kind], method["value"], method["label"]])
        row = [
            contact["name"],
            "是" if contact["favorite"] else "否",
            *["；".join(grouped[header]) for header in KIND_COLUMNS.values()],
            contact["notes"],
        ]
        sheet.append(row)
    if label_rows:
        labels = workbook.create_sheet(LABEL_SHEET)
        labels.append(LABEL_HEADERS)
        for row in label_rows:
            labels.append(row)
        labels.column_dimensions["A"].width = 16
        labels.column_dimensions["B"].width = 16
        labels.column_dimensions["C"].width = 16
        labels.column_dimensions["D"].width = 32
        labels.column_dimensions["E"].width = 20
        labels.freeze_panes = "A2"
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
    sheet.append(["张三（示例，可删除）", "是", "13800000000；13900000000", "", "zhangsan@example.com", "zhangsan", "", "", "福建省福州市", "", "导入模板示例"])
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
    normalized = _cell_text(value).replace("\r", "\n").replace(";", "；").replace("\n", "；")
    return [item.strip() for item in normalized.split("；") if item.strip()]


def parse_workbook(stream):
    """Return (valid contact records, row errors); no database writes occur here."""
    try:
        workbook = load_workbook(stream, read_only=True, data_only=True)
    except Exception as error:
        raise ValueError("无法读取文件，请上传有效的 .xlsx 工作簿") from error

    sheet = workbook.active
    header_row = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), None)
    actual_headers = [_cell_text(value) for value in header_row] if header_row else []
    if actual_headers[: len(HEADERS)] != HEADERS:
        workbook.close()
        raise ValueError("表头不兼容，请下载并使用系统提供的 Excel 模板")

    labels_by_row = {}
    errors = []
    if LABEL_SHEET in workbook.sheetnames:
        label_sheet = workbook[LABEL_SHEET]
        label_headers = next(label_sheet.iter_rows(min_row=1, max_row=1, values_only=True), None)
        if not label_headers or [_cell_text(value) for value in label_headers[:5]] != LABEL_HEADERS:
            workbook.close()
            raise ValueError("联系方式标签工作表的表头不兼容")
        for number, row in enumerate(label_sheet.iter_rows(min_row=2, values_only=True), start=2):
            values = [_cell_text(value) for value in row[:5]]
            if not any(values):
                continue
            contact_row, kind, occurrence, value, label = values
            if not contact_row.isdecimal() or not occurrence.isdecimal() or not label:
                errors.append(f"标签表第 {number} 行：行号、序号和标签不能为空且序号必须是正整数")
                continue
            key = (kind, int(occurrence))
            labels_by_row.setdefault(int(contact_row), []).append((number, key, value, label))

    records = []
    seen_rows = set()
    for row_number, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        values = [_cell_text(value) for value in row[: len(HEADERS)]]
        if not any(values):
            continue
        seen_rows.add(row_number)
        data = dict(zip(HEADERS, values))
        if not data["姓名"]:
            errors.append(f"第 {row_number} 行：姓名不能为空")
            continue
        favorite = data["收藏"].casefold()
        if favorite not in TRUE_VALUES | FALSE_VALUES:
            errors.append(f"第 {row_number} 行：收藏列只能填写是/否")
            continue
        methods = []
        for kind, header in KIND_COLUMNS.items():
            for value in _split_values(data[header]):
                methods.append({"kind": kind, "value": value, "label": ""})
        method_lookup = {}
        counts = {}
        for method in methods:
            counts[method["kind"]] = counts.get(method["kind"], 0) + 1
            method_lookup[(method["kind"], counts[method["kind"]])] = method
        applied = set()
        for label_row, key, value, label in labels_by_row.get(row_number, []):
            method = method_lookup.get(key)
            if method is None or method["value"] != value or key in applied:
                errors.append(f"标签表第 {label_row} 行：联系方式与通讯录第 {row_number} 行不匹配")
                continue
            method["label"] = label
            applied.add(key)
        try:
            record = validate_contact(
                {
                    "name": data["姓名"],
                    "favorite": favorite in TRUE_VALUES,
                    "notes": data["备注"],
                    "methods": methods,
                }
            )
            records.append(record)
        except ValueError as error:
            errors.append(f"第 {row_number} 行：{error}")
    for contact_row in labels_by_row.keys() - seen_rows:
        errors.append(f"标签表引用的通讯录第 {contact_row} 行不存在")
    workbook.close()
    return records, errors
