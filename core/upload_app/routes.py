import os
import requests
from flask import request, jsonify

from core.upload_app import bp
from core.utils import generate_s3_presigned_upload_url


@bp.route('/generate_file_upload_url', methods=['POST'])
def generate_file_upload_url():
    """Generates presigned url for files to be uploaded"""
    json_data = request.json
    upload_resp = generate_s3_presigned_upload_url(
        json_data
    )
    if upload_resp["error"] is True:
        return jsonify({
            "error": upload_resp["error_message"]
        }), upload_resp["status_code"]
    return jsonify({
        "upload_url": upload_resp["presigned"]["url"],
        "fields": upload_resp["presigned"]["fields"]
    }), 200
