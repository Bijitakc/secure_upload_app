from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from core.metrics_app import bp


@bp.route("/metrics")
def metrics():
    """Returns metrics"""
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}
