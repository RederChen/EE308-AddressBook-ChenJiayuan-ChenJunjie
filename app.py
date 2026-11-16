import os

from addressbook import create_app


app = create_app()


if __name__ == "__main__":
    host = os.environ.get("ADDRESS_BOOK_HOST", "127.0.0.1")
    port = int(os.environ.get("ADDRESS_BOOK_PORT", "5000"))
    print(f"拾光通讯录 v1.3.0 已启动：http://{host}:{port}  （Ctrl+C 停止）")
    app.run(host=host, port=port, debug=False)
