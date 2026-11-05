import pytest
from flask import Flask, g

from core import db
from core.upload_app import bp
import core.decorators as decorators


@pytest.fixture
def app(tmp_path, monkeypatch):
    database_path = tmp_path / "test.sqlite"
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret",
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{database_path}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    db.init_app(app)
    app.register_blueprint(bp)

    def authenticate(_token):
        g.user_id = "user-1"
        return {"error": False}

    monkeypatch.setattr(decorators, "token_decode", authenticate)
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token"}
