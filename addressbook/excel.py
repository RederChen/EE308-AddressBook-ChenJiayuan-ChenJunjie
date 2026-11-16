"""Excel 导入导出：每个联系人一行、每类联系方式一列，联系方式标签用独立工作表保存。

V1.2 修复：
- 导出时对以 = + - @ 开头的文本加英文单引号前缀，避免被 Excel 当作公式执行（公式注入）；
  重新导入时自动去掉该前缀，保证往返一致。
- 导入增加行数上限与更明确的逐行错误定位。
"""
import io

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .validation import (
    ALLOWED_KINDS,
    KIND_LABELS,
    MAX_IMPORT_ROWS,
    ValidationError,
    validate_contact,
)


HEADERS = ["姓名", "收藏", "手机", "电话", "邮箱", "微信", "QQ", "微博", "地址", "其他联系方式", "备注"]
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
KIND_ORDER = ["mobile", "phone", "email", "wechat", "qq", "weibo", "address", "other"]
LABEL_SHEET = "联系方式标签"
LABEL_HEADERS = ["联系人行号", "方式类型", "同类型序号", "联系方式内容", "标签"]

TRUE_VALUES = {"是", "1", "true", "yes", "y", "★", "已收藏"}
FALSE_VALUES = {"", "否", "0", "false", "no", "n", "未收藏"}

# 中文列名 / 类型名 → 内部 kind，用于解析标签工作表。
KIND_LABEL_TO_KIND = {label.casefold(): kind for kind, label in KIND_LABELS.items()}
KIND_LABEL_TO_KIND["其他联系方式"] = "other"
KIND_LABEL_TO_KIND["手机号码"] = "mobile"
KIND_LABEL_TO_KIND["电话号码"] = "phone"

DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
HEADER_FILL = PatternFill("solid", fgColor="31572C")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center")
BODY_ALIGNMENT = Alignment(vertical="top", wrap_text=True)
COLUMN_WIDTHS = [16, 10, 28, 24, 30, 22, 20, 22, 36, 32, 36]
LABEL_COLUMN_WIDTHS = [14, 14, 12, 28, 20]


def _safe_text(value):
    """导出文本：以危险字符开头时加单引号前缀，防止 Excel/WPS 将其当作公式。"""
    text = "" if value is None else str(value)
    if text.startswith(DANGEROUS_PREFIXES):
        return "'" + text
    return text


def _cell_text(value):
    """读取单元格文本：None→空串，整数型浮点去掉 .0，布尔转是/否，并还原导出的防注入前缀。"""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, float) and value.is_integer():
        text = str(int(value))
    else:
        text = str(value).strip()
    if len(text) > 1 and text[0] == "'" and text[1] in "=+-@\t":
        return text[1:]
    return text


def _split_values(text):
    """支持中文分号、英文分号、换行分隔的多个同类联系方式。"""
    if not text:
        return []
    normalized = text.replace("\r", "\n").replace(";", "；").replace("\n", "；")
    return [part.strip() for part in normalized.split("；") if part.strip()]


def _style_sheet(sheet, headers, widths):
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{max(sheet.max_row, 1)}"
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    for cell in sheet[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = HEADER_ALIGNMENT
    sheet.row_dimensions[1].height = 26
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = BODY_ALIGNMENT


def export_workbook(contacts):
    """把联系人写成一个 .xlsx 文件流：主表一人一行，非空标签写入“联系方式标签”工作表。"""
    book = Workbook()
    sheet = book.active
    sheet.title = "通讯录"
    sheet.append(HEADERS)

    label_rows = []
    for sheet_row, contact in enumerate(contacts, start=2):
        grouped = {kind: [] for kind in KIND_ORDER}
        for method in contact.get("methods", []):
            kind = method["kind"] if method["kind"] in ALLOWED_KINDS else "other"
            grouped[kind].append(method)

        row = [_safe_text(contact.get("name", "")), "是" if contact.get("favorite") else "否"]
        for kind in KIND_ORDER:
            row.append(_safe_text("；".join(item["value"] for item in grouped[kind])))
        row.append(_safe_text(contact.get("notes", "")))
        sheet.append(row)

        for kind in KIND_ORDER:
            for occurrence, method in enumerate(grouped[kind], start=1):
                label = (method.get("label") or "").strip()
                if label:
                    label_rows.append([
                        sheet_row,
                        KIND_LABELS[kind],
                        occurrence,
                        _safe_text(method["value"]),
                        _safe_text(label),
                    ])

    _style_sheet(sheet, HEADERS, COLUMN_WIDTHS)

    if label_rows:
        label_sheet = book.create_sheet(LABEL_SHEET)
        label_sheet.append(LABEL_HEADERS)
        for row in label_rows:
            label_sheet.append(row)
        _style_sheet(label_sheet, LABEL_HEADERS, LABEL_COLUMN_WIDTHS)

    stream = io.BytesIO()
    book.save(stream)
    book.close()
    stream.seek(0)
    return stream


def template_workbook():
    """返回带一行示例数据的导入模板。"""
    stream = export_workbook([])
    book = load_workbook(stream)
    sheet = book["通讯录"]
    sheet.append([
        "张三（示例，可删除）",
        "是",
        "13800000000；13900000000",
        "",
        "zhangsan@example.com",
        "zhangsan",
        "",
        "",
        "福建省福州市",
        "",
        "导入模板示例",
    ])
    _style_sheet(sheet, HEADERS, COLUMN_WIDTHS)
    output = io.BytesIO()
    book.save(output)
    book.close()
    output.seek(0)
    return output


def _read_label_sheet(book):
    """读取标签工作表，返回原始条目列表与错误列表。"""
    entries, errors = [], []
    for sheet in book.worksheets[1:]:
        if sheet.title.strip() != LABEL_SHEET:
            continue
        rows = sheet.iter_rows(values_only=True)
        header = next(rows, None)
        if header is None:
            return [], errors
        header_cells = [_cell_text(cell) for cell in list(header)[:len(LABEL_HEADERS)]]
        header_cells += [""] * (len(LABEL_HEADERS) - len(header_cells))
        if header_cells != LABEL_HEADERS:
            raise ValueError("联系方式标签工作表的表头不兼容")
        for row_number, values in enumerate(rows, start=2):
            cells = [_cell_text(cell) for cell in list(values)[:len(LABEL_HEADERS)]]
            cells += [""] * (len(LABEL_HEADERS) - len(cells))
            if not any(cells):
                continue
            contact_row, kind_text, occurrence_text, value, label = cells
            if not contact_row.isdecimal() or not occurrence_text.isdecimal():
                errors.append(f"标签表第 {row_number} 行：联系人行号与同类型序号必须为数字")
                continue
            if not label:
                errors.append(f"标签表第 {row_number} 行：标签不能为空")
                continue
            entries.append((row_number, int(contact_row), kind_text, int(occurrence_text), value, label))
        break
    return entries, errors


def _apply_labels(records, entries, contact_rows):
    """把标签条目关联回联系方式；关联不上就报错，避免把标签贴到错误的人身上。"""
    errors = []
    by_row = {record["__row__"]: record for record in records}
    used = set()
    for label_row, contact_row, kind_text, occurrence, value, label in entries:
        if contact_row not in contact_rows:
            errors.append(f"标签表第 {label_row} 行：引用的通讯录第 {contact_row} 行不存在")
            continue
        kind = KIND_LABEL_TO_KIND.get(kind_text.casefold())
        if kind is None and kind_text.casefold() in ALLOWED_KINDS:
            kind = kind_text.casefold()
        if kind is None:
            errors.append(f"标签表第 {label_row} 行：方式类型不正确")
            continue
        record = by_row[contact_row]
        matches = [method for method in record["methods"] if method["kind"] == kind]
        if occurrence < 1 or occurrence > len(matches):
            errors.append(f"标签表第 {label_row} 行：联系方式与通讯录第 {contact_row} 行不匹配")
            continue
        method = matches[occurrence - 1]
        key = (contact_row, kind, occurrence)
        if method["value"] != value or key in used:
            errors.append(f"标签表第 {label_row} 行：联系方式与通讯录第 {contact_row} 行不匹配")
            continue
        used.add(key)
        method["label"] = label
    return errors


def _parse_row(row_number, cells):
    name = cells[0]
    if not name:
        raise ValueError(f"第 {row_number} 行：姓名不能为空")
    favorite_text = cells[1].casefold()
    if favorite_text in TRUE_VALUES:
        favorite = True
    elif favorite_text in FALSE_VALUES:
        favorite = False
    else:
        raise ValueError(f"第 {row_number} 行：收藏列只能填写是/否")

    methods = []
    for kind in KIND_ORDER:
        column = HEADERS.index(KIND_COLUMNS[kind])
        for value in _split_values(cells[column]):
            methods.append({"kind": kind, "label": "", "value": value})

    record = {"name": name, "favorite": favorite, "notes": cells[-1], "methods": methods}
    try:
        return validate_contact(record)
    except ValidationError as exc:
        raise ValueError(f"第 {row_number} 行：{exc}")


def parse_workbook(stream):
    """解析工作簿，返回 (records, errors)；不写数据库，由调用方决定是否落库。"""
    try:
        book = load_workbook(stream, read_only=True, data_only=True)
    except Exception as exc:  # openpyxl 对坏文件会抛多种异常
        raise ValueError("无法读取文件，请上传有效的 .xlsx 工作簿") from exc
    try:
        if not book.worksheets:
            raise ValueError("工作簿中没有工作表")
        sheet = book.worksheets[0]
        row_iter = sheet.iter_rows(values_only=True)
        header = next(row_iter, None)
        if header is None:
            raise ValueError("工作簿为空，没有可导入的联系人")
        header_cells = [_cell_text(cell) for cell in list(header)[:len(HEADERS)]]
        header_cells += [""] * (len(HEADERS) - len(header_cells))
        if header_cells != HEADERS:
            raise ValueError("表头不兼容，请下载并使用系统提供的 Excel 模板")

        label_entries, errors = _read_label_sheet(book)

        records = []
        contact_rows = set()
        for row_number, values in enumerate(row_iter, start=2):
            cells = [_cell_text(cell) for cell in list(values)[:len(HEADERS)]]
            cells += [""] * (len(HEADERS) - len(cells))
            if not any(cells):
                continue
            if len(records) >= MAX_IMPORT_ROWS:
                errors.append(f"第 {row_number} 行：超过单次导入上限 {MAX_IMPORT_ROWS} 行，请拆分文件后重试")
                break
            try:
                record = _parse_row(row_number, cells)
            except ValueError as exc:
                errors.append(str(exc))
                continue
            record["__row__"] = row_number
            records.append(record)
            contact_rows.add(row_number)

        errors.extend(_apply_labels(records, label_entries, contact_rows))
        for record in records:
            record.pop("__row__", None)
        return records, errors
    finally:
        book.close()
