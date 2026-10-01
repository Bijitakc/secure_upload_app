from flask import Blueprint

bp = Blueprint('metrics_app', __name__)

from core.metrics_app import routes  # noqa: F401, E402
