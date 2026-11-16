ALLOWED_KINDS = {"mobile", "phone", "email", "wechat", "qq", "weibo", "address", "other"}
MAX_METHODS = 30


def _text(value, field, max_length, required=False):
    if value is None:
        value = ""
    if not isinstance(value, (str, int, float)):
        raise ValueError(f"{field} has an invalid format")
    result = str(value).strip()
    if required and not result:
        raise ValueError(f"{field} is required")
    if len(result) > max_length:
        raise ValueError(f"{field} must not exceed {max_length} characters")
    return result


def validate_contact(payload):
    if not isinstance(payload, dict):
        raise ValueError("The request body must be a JSON object")

    methods = payload.get("methods", [])
    if not isinstance(methods, list):
        raise ValueError("Contact methods must be provided as a list")
    if len(methods) > MAX_METHODS:
        raise ValueError(f"Each contact can have up to {MAX_METHODS} contact methods")

    normalized_methods = []
    for index, method in enumerate(methods, start=1):
        if not isinstance(method, dict):
            raise ValueError(f"Contact method {index} has an invalid format")
        kind = _text(method.get("kind"), "Contact method type", 20, required=True).lower()
        if kind not in ALLOWED_KINDS:
            raise ValueError(f"Unsupported contact method type: {kind}")
        value = _text(method.get("value"), f"Contact method {index}", 200)
        label = _text(method.get("label"), "Contact method label", 30)
        if not value:
            continue
        normalized_methods.append({"kind": kind, "label": label, "value": value})

    favorite = payload.get("favorite", False)
    if not isinstance(favorite, (bool, int)) or favorite not in (True, False, 0, 1):
        raise ValueError("Favorite status has an invalid format")

    return {
        "name": _text(payload.get("name"), "Name", 80, required=True),
        "favorite": bool(favorite),
        "notes": _text(payload.get("notes"), "Notes", 500),
        "methods": normalized_methods,
    }
