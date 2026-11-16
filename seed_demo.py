"""Populate a local database with fictional demonstration contacts (never overwrites data)."""
from addressbook import create_app
from addressbook.db import get_db
from addressbook.repository import create_contact


DEMO_CONTACTS = [
    {"name": "林小满", "favorite": True, "notes": "极限编程搭档，负责后端与测试。", "methods": [
        {"kind": "mobile", "value": "138 0000 1024", "label": "工作"},
        {"kind": "mobile", "value": "139 0000 2026", "label": "个人"},
        {"kind": "email", "value": "xiaoman@example.com", "label": "学校"},
        {"kind": "wechat", "value": "xiaoman_xp", "label": ""},
        {"kind": "address", "value": "福建省福州市闽侯县", "label": "学校"},
    ]},
    {"name": "陈以安", "favorite": True, "notes": "软件工程课程小组成员。", "methods": [
        {"kind": "mobile", "value": "136 0000 3088", "label": ""},
        {"kind": "email", "value": "yian@example.com", "label": ""},
        {"kind": "qq", "value": "10241024", "label": ""},
    ]},
    {"name": "周予川", "favorite": False, "notes": "喜欢摄影，周末常去旗山。", "methods": [
        {"kind": "mobile", "value": "135 0000 7766", "label": ""},
        {"kind": "weibo", "value": "@予川看世界", "label": ""},
    ]},
    {"name": "苏念", "favorite": False, "notes": "图书馆三楼靠窗座位的常客。", "methods": [
        {"kind": "mobile", "value": "137 0000 5521", "label": ""},
        {"kind": "email", "value": "sunian@example.com", "label": "常用"},
        {"kind": "wechat", "value": "su_nian", "label": ""},
    ]},
    {"name": "许嘉禾", "favorite": False, "notes": "羽毛球队，周三晚上训练。", "methods": [
        {"kind": "phone", "value": "0591-8000 2026", "label": "宿舍"},
        {"kind": "email", "value": "jiahe@example.com", "label": ""},
    ]},
    {"name": "郑老师", "favorite": True, "notes": "软件工程课程教师（演示虚构信息）。", "methods": [
        {"kind": "phone", "value": "0591-8000 1111", "label": "办公室"},
        {"kind": "email", "value": "teacher@example.com", "label": "工作"},
        {"kind": "address", "value": "福建省福州市", "label": "办公室"},
    ]},
]


def seed():
    app = create_app()
    with app.app_context():
        count = get_db().execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
        if count:
            print(f"Database already contains {count} contacts; no demo data was added.")
            return
        for contact in DEMO_CONTACTS:
            create_contact(contact)
        print(f"Added {len(DEMO_CONTACTS)} fictional demo contacts.")


if __name__ == "__main__":
    seed()
