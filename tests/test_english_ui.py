import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_SOURCES = [
    "addressbook/templates/index.html",
    "addressbook/static/app.js",
    "addressbook/routes.py",
    "addressbook/validation.py",
    "addressbook/excel.py",
    "seed_demo.py",
]


def test_ui_sources_contain_no_chinese_characters():
    chinese_pattern = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
    offenders = []
    for relative_path in UI_SOURCES:
        content = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        for line_number, line in enumerate(content.splitlines(), start=1):
            if chinese_pattern.search(line):
                offenders.append(f"{relative_path}:{line_number}")
    assert not offenders, f"Chinese text remains in UI sources: {offenders}"
