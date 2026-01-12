import os
import boto3
import logging
from flask import Flask
from config import config
from flask_caching import Cache
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow


# flask extensions
cache = Cache()
db = SQLAlchemy()
marshmallow = Marshmallow()
migrate = Migrate(compare_type=True)
s3 = boto3.client("s3", region_name=os.environ.get("S3_REGION"))


def create_app(config_name, **kwargs) -> Flask:
    """
    Creates a flask app instance, initializes
    extensions, registers blueprints and other
    setups
    """
    # Adding logging
    logging.basicConfig(
        format=f'%(asctime)s %(levelname)s %('f'name)s %(threadName)s : %(message)s' # noqa
    )
    formatter = logging.Formatter(f'%(asctime)s %(levelname)s %('f'name)s %(threadName)s : %(message)s') # noqa
    file_logging = logging.FileHandler('error_record.log')
    file_logging.setLevel(logging.WARNING)
    file_logging.setFormatter(formatter)
    logging.getLogger().addHandler(file_logging)

    app = Flask(
        __name__
    )
    app.config.from_object(config[config_name])

    # Initializing flask extensions
    cache.init_app(app)
    db.init_app(app)
    marshmallow.init_app(app)
    migrate.init_app(app, db)
    with app.app_context():
        cache.clear()

    # Registering Blueprints
    from core.upload_app import bp as u_bp

    app.register_blueprint(u_bp)

    return app
