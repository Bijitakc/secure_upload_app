from flask import Blueprint

bp = Blueprint('upload_app', __name__)

from core.upload_app import routes  # noqa: F401, E402
