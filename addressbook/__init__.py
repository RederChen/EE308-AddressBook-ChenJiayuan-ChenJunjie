"""Flask 应用工厂：配置、数据库初始化、蓝图注册与统一错误处理。"""
from pathlib import Path

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from . import db


DEFAULT_MAX_UPLOAD = 5 * 1024 * 1024  # 5 MiB，与页面提示保持一致
HTTP_MESSAGES = {
    400: "请求参数不正确",
    404: "请求的资源不存在",
    405: "请求方法不被支持",
    413: "文件超过 5 MiB 大小限制",
    500: "服务器内部错误，请稍后重试",
}


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=str(Path(app.instance_path) / "addressbook.db"),
        MAX_CONTENT_LENGTH=DEFAULT_MAX_UPLOAD,
    )
    if test_config:
        app.config.update(test_config)

    app.json.ensure_ascii = False  # 直接返回中文，而不是 \uXXXX 转义
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)

    from .routes import bp

    app.register_blueprint(bp)

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        if request.path.startswith("/api/"):
            message = HTTP_MESSAGES.get(error.code, error.name)
            return jsonify({"error": message}), error.code
        return error

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        if request.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    return app
