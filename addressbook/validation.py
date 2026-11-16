"""联系人输入的集中校验：姓名、备注、收藏状态与多条联系方式。"""
import re

ALLOWED_KINDS = {"mobile", "phone", "email", "wechat", "qq", "weibo", "address", "other"}
KIND_LABELS = {
    "mobile": "手机",
    "phone": "电话",
    "email": "邮箱",
    "wechat": "微信",
    "qq": "QQ",
    "weibo": "微博",
    "address": "地址",
    "other": "其他",
}

MAX_NAME = 80
MAX_NOTES = 500
MAX_METHODS = 30
MAX_VALUE = 200
MAX_LABEL = 30
MAX_IMPORT_ROWS = 2000
MAX_BULK_IDS = 500
IMPORT_MODES = {"skip", "overwrite"}
SORT_KEYS = {"favorite", "name", "recent", "created"}

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class ValidationError(ValueError):
    """校验失败的统一异常，路由层转换成 400 响应。"""


def _clean(value):
    """去掉控制字符与首尾空白，保留内部换行。"""
    return _CONTROL_CHARS.sub("", value)


def _text(value, field, max_length, required=False):
    if value is None:
        value = ""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValidationError(f"{field}格式不正确")
    text = _clean(str(value)).strip()
    if required and not text:
        raise ValidationError(f"{field}不能为空")
    if len(text) > max_length:
        raise ValidationError(f"{field}不能超过 {max_length} 个字符")
    return text


def validate_contact(payload):
    """返回清洗后的联系人字典；任何不合法字段都会抛出 ValidationError。"""
    if not isinstance(payload, dict):
        raise ValidationError("联系人数据格式不正确")

    name = _text(payload.get("name"), "姓名", MAX_NAME, required=True)
    notes = _text(payload.get("notes"), "备注", MAX_NOTES)

    favorite = payload.get("favorite", False)
    if not isinstance(favorite, bool) and favorite not in (0, 1):
        raise ValidationError("收藏状态必须是布尔值")

    raw_methods = payload.get("methods", [])
    if not isinstance(raw_methods, list):
        raise ValidationError("联系方式必须是列表")
    if len(raw_methods) > MAX_METHODS:
        raise ValidationError(f"每个联系人最多 {MAX_METHODS} 条联系方式")

    methods = []
    for index, item in enumerate(raw_methods, start=1):
        if not isinstance(item, dict):
            raise ValidationError(f"第 {index} 条联系方式格式不正确")
        kind = _clean(str(item.get("kind") or "")).strip().lower()
        if kind not in ALLOWED_KINDS:
            raise ValidationError(f"第 {index} 条联系方式的类型不正确")
        value = _text(item.get("value"), f"第 {index} 条联系方式内容", MAX_VALUE)
        if not value:
            continue  # 空行直接忽略，允许用户点了“添加一条”却没填
        label = _text(item.get("label"), f"第 {index} 条联系方式标签", MAX_LABEL)
        methods.append({"kind": kind, "label": label, "value": value})

    return {"name": name, "favorite": bool(favorite), "notes": notes, "methods": methods}


def validate_ids(ids):
    """校验批量操作的联系人 id 列表。"""
    if not isinstance(ids, list) or not ids:
        raise ValidationError("请先选择至少一位联系人")
    if len(ids) > MAX_BULK_IDS:
        raise ValidationError(f"一次最多操作 {MAX_BULK_IDS} 位联系人")
    cleaned = []
    for item in ids:
        if isinstance(item, bool) or not isinstance(item, int):
            raise ValidationError("联系人编号格式不正确")
        if item <= 0:
            raise ValidationError("联系人编号格式不正确")
        if item not in cleaned:
            cleaned.append(item)
    return cleaned


def validate_mode(mode):
    mode = (mode or "skip").strip().lower()
    if mode not in IMPORT_MODES:
        raise ValidationError("导入重复处理方式只能是“跳过同名”或“覆盖同名”")
    return mode


def validate_sort(sort):
    sort = (sort or "favorite").strip().lower()
    if sort not in SORT_KEYS:
        raise ValidationError("排序方式不支持")
    return sort


def validate_paging(limit, offset):
    """limit/offset 为空表示不分页；limit 上限 200。"""
    try:
        limit_value = int(limit) if limit not in (None, "") else None
        offset_value = int(offset) if offset not in (None, "") else 0
    except (TypeError, ValueError):
        raise ValidationError("分页参数格式不正确")
    if limit_value is not None and limit_value <= 0:
        raise ValidationError("每页数量必须为正整数")
    if limit_value is not None:
        limit_value = min(limit_value, 200)
    if offset_value < 0:
        raise ValidationError("分页偏移量不能为负数")
    return limit_value, offset_value
