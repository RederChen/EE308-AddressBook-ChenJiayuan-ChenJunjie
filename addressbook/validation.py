ALLOWED_KINDS = {"mobile", "phone", "email", "wechat", "qq", "weibo", "address", "other"}
MAX_METHODS = 30


def _text(value, field, max_length, required=False):
    if value is None:
        value = ""
    if not isinstance(value, (str, int, float)):
        raise ValueError(f"{field}格式不正确")
    result = str(value).strip()
    if required and not result:
        raise ValueError(f"{field}不能为空")
    if len(result) > max_length:
        raise ValueError(f"{field}不能超过 {max_length} 个字符")
    return result


def validate_contact(payload):
    if not isinstance(payload, dict):
        raise ValueError("请求内容必须是 JSON 对象")

    methods = payload.get("methods", [])
    if not isinstance(methods, list):
        raise ValueError("联系方式必须是列表")
    if len(methods) > MAX_METHODS:
        raise ValueError(f"每个联系人最多保存 {MAX_METHODS} 条联系方式")

    normalized_methods = []
    for index, method in enumerate(methods, start=1):
        if not isinstance(method, dict):
            raise ValueError(f"第 {index} 条联系方式格式不正确")
        kind = _text(method.get("kind"), "联系方式类型", 20, required=True).lower()
        if kind not in ALLOWED_KINDS:
            raise ValueError(f"不支持的联系方式类型：{kind}")
        value = _text(method.get("value"), f"第 {index} 条联系方式", 200)
        label = _text(method.get("label"), "联系方式标签", 30)
        if not value:
            continue
        normalized_methods.append({"kind": kind, "label": label, "value": value})

    favorite = payload.get("favorite", False)
    if not isinstance(favorite, (bool, int)) or favorite not in (True, False, 0, 1):
        raise ValueError("收藏状态格式不正确")

    return {
        "name": _text(payload.get("name"), "姓名", 80, required=True),
        "favorite": bool(favorite),
        "notes": _text(payload.get("notes"), "备注", 500),
        "methods": normalized_methods,
    }
