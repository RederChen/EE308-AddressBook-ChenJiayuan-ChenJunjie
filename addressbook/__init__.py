from pathlib import Path

from flask import Flask

from . import db


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=str(Path(app.instance_path) / "addressbook.db"),
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
        JSON_AS_ASCII=False,
    )
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(app)

    from .routes import bp

    app.register_blueprint(bp)
    return app
