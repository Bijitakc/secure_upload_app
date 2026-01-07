import os
from flask import Flask
from config import config
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow


# flask extensions
db = SQLAlchemy()
migrate = Migrate(compare_type=True)
marshmallow = Marshmallow()

# Importing models here so that they are registered with SQLAlchemy
# from core import models  # noqa: F401,E402


def create_app(config_name, **kwargs) -> Flask:
    """
    Creates a flask app instance, initializes
    extensions, registers blueprints and other
    setups
    """
    app = Flask(
        __name__
    )
    app.config.from_object(config[config_name])

    # Initializing flask extensions
    db.init_app(app)
    migrate.init_app(app, db)
    marshmallow.init_app(app)

    # Registering Blueprints
    from core.upload_app import bp as u_bp

    app.register_blueprint(u_bp)

    return app
