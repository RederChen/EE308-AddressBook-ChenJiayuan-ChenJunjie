"""Populate a local database with fictional demonstration contacts (never overwrites data)."""
from addressbook import create_app
from addressbook.db import get_db
from addressbook.repository import create_contact


DEMO_CONTACTS = [
    {"name": "Alice Morgan", "favorite": True, "notes": "Extreme Programming partner responsible for backend development and testing.", "methods": [
        {"kind": "mobile", "value": "138 0000 1024", "label": "Work"},
        {"kind": "mobile", "value": "139 0000 2026", "label": "Personal"},
        {"kind": "email", "value": "alice@example.com", "label": "School"},
        {"kind": "wechat", "value": "alice_xp", "label": ""},
        {"kind": "address", "value": "Minhou, Fuzhou, Fujian, China", "label": "School"},
    ]},
    {"name": "Brian Chen", "favorite": True, "notes": "Member of the Software Engineering course project team.", "methods": [
        {"kind": "mobile", "value": "136 0000 3088", "label": ""},
        {"kind": "email", "value": "brian@example.com", "label": ""},
        {"kind": "qq", "value": "10241024", "label": ""},
    ]},
    {"name": "Caleb Turner", "favorite": False, "notes": "Enjoys photography and weekend trips to Qishan.", "methods": [
        {"kind": "mobile", "value": "135 0000 7766", "label": ""},
        {"kind": "weibo", "value": "@CalebExplores", "label": ""},
    ]},
    {"name": "Sophia Reed", "favorite": False, "notes": "Often studies at a window seat on the library's third floor.", "methods": [
        {"kind": "mobile", "value": "137 0000 5521", "label": ""},
        {"kind": "email", "value": "sophia@example.com", "label": "Primary"},
        {"kind": "wechat", "value": "sophia_reed", "label": ""},
    ]},
    {"name": "Daniel Hayes", "favorite": False, "notes": "Badminton team member; practice on Wednesday evenings.", "methods": [
        {"kind": "phone", "value": "0591-8000 2026", "label": "Dormitory"},
        {"kind": "email", "value": "daniel@example.com", "label": ""},
    ]},
    {"name": "Dr. Emily Wilson", "favorite": True, "notes": "Software Engineering instructor (fictional demo contact).", "methods": [
        {"kind": "phone", "value": "0591-8000 1111", "label": "Office"},
        {"kind": "email", "value": "teacher@example.com", "label": "Work"},
        {"kind": "address", "value": "Fuzhou, Fujian, China", "label": "Office"},
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
