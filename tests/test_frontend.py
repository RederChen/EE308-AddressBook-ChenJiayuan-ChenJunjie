"""前端与后端契约：静态资源、DOM id、SVG 图标与 API 路径一致性。

这些检查不需要浏览器，却能拦住「HTML 改名了、JS 还在找旧 id」
以及「JS 调用了后端并不存在的接口」这类只在打开页面时才暴露的问题。
"""
import re
from pathlib import Path

from werkzeug.exceptions import MethodNotAllowed, NotFound

PROJECT = Path(__file__).resolve().parents[1]
TEMPLATE = PROJECT / "addressbook" / "templates" / "index.html"
SCRIPT = PROJECT / "addressbook" / "static" / "app.js"
STYLES = PROJECT / "addressbook" / "static" / "styles.css"


def markup():
    return TEMPLATE.read_text(encoding="utf-8")


def script():
    return SCRIPT.read_text(encoding="utf-8")


def test_static_assets_are_served(client):
    page = client.get("/")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "/static/styles.css" in html
    assert "/static/app.js" in html

    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/styles.css").status_code == 200


def test_every_element_id_used_by_javascript_exists_in_template():
    html_ids = set(re.findall(r'id="([^"]+)"', markup()))
    used = set()
    js = script()
    for pattern in (
        r'getElementById\("([^"]+)"\)',
        r'\$+\("#([A-Za-z0-9_-]+)',           # $("#id") / $$("#id .child")
        r'querySelector(?:All)?\("#([A-Za-z0-9_-]+)',  # document.querySelector("#id")
    ):
        used.update(re.findall(pattern, js))
    assert used, "app.js 没有解析到任何 DOM id，检查正则或实现"
    assert not used - html_ids, f"app.js 引用了不存在的 id：{sorted(used - html_ids)}"


def test_icon_sprite_covers_every_icon_used_by_javascript():
    sprite = {"i-" + name for name in re.findall(r'id="i-([a-z-]+)"', markup())}
    used = set(re.findall(r'icon\("([a-z-]+)"\)', script()))
    assert used
    assert not used - sprite, f"缺少 SVG symbol：{sorted(used - sprite)}"


def test_template_ids_are_unique_and_dialogs_are_present():
    ids = re.findall(r'id="([^"]+)"', markup())
    assert len(ids) == len(set(ids))
    html = markup()
    assert html.count("<dialog") == 2
    assert html.count("</dialog>") == 2


def test_page_exposes_current_features():
    html = markup()
    for text in ("回收站", "批量管理", "排序", "导入", "导出当前列表", "v1.3.0", "拾光通讯录"):
        assert text in html, text
    assert 'name="import-mode"' in html
    assert 'id="sort-select"' in html
    assert 'id="load-more-button"' in html


def test_frontend_only_calls_known_api_paths(client):
    js = script()
    paths = set(re.findall(r'["`](/api/[^"`]+)["`]', js))
    paths.update(re.findall(r'href="(/api/[^"]+)"', markup()))
    paths.add("/api/contacts")
    assert paths

    adapter = client.application.url_map.bind("localhost")
    for raw in paths:
        path = re.sub(r"\$\{[^}]+\}", "1", raw).split("?")[0]
        try:
            adapter.match(path, method="GET")
        except MethodNotAllowed:
            pass
        except NotFound:
            raise AssertionError(f"前端调用了不存在的接口：{path}（来自 {raw}）")


def test_stylesheet_has_current_components():
    css = STYLES.read_text(encoding="utf-8")
    for selector in (".bulk-bar", ".card-check", ".copy-button", ".import-preview", ".list-footer", ".sort-box"):
        assert selector in css, selector
