import os
import boto3
import requests
import botocore.exceptions
from flask_expects_json import expects_json
from flask import g, request, current_app, jsonify

from core import s3
from core.upload_app import bp
from core.models import UserFileStore
from core.decorators import login_required
from core.utils import generate_s3_presigned_upload_url, \
    upload_checks_and_additions
from core.json_schemas import retrieve_file_schema, post_upload_schema, \
    generate_file_upload_schema


@bp.route('/file/generate_file_upload_url', methods=['POST'])
@expects_json(generate_file_upload_schema)
@login_required
def generate_file_upload_url():
    """Generates presigned url for files to be uploaded"""
    json_data = request.json
    upload_resp = generate_s3_presigned_upload_url(
        json_data
    )
    if upload_resp["error"] is True:
        return jsonify({
            "success": False,
            "error": {
                "message": upload_resp["error_message"]
            }
        }), upload_resp["status_code"]
    return jsonify({
        "success": True,
        "upload_url": upload_resp["presigned"]["url"],
        "fields": upload_resp["presigned"]["fields"]
    }), 200


@bp.route('/file/post_upload_validation', methods=['POST'])
@expects_json(post_upload_schema)
@login_required
def post_upload_validation():
    """Validates the uploaded file"""
    json_data = request.json
    check_resp = upload_checks_and_additions(
        json_data
    )
    if check_resp["error"] is True:
        return jsonify({
            "error": check_resp["error_message"]
        }), 400
    return jsonify({
        "message": "successfully added attachment."
    }), 200


@bp.route('/file/download', methods=['POST'])
@expects_json(retrieve_file_schema)
@login_required
def retrieve_file_link():
    """
    Generates presigned url for getting the file from s3
    """
    json_data = request.json
    user_id = g.user_id
    file_store_id = json_data['file_store_id']
    s3_bucket = os.environ.get("S3_BUCKET_NAME")
    expires_in = int(os.environ.get('PRESIGNED_URL_EXPIRATION_TIME'))

    file_check = UserFileStore.query.filter_by(
        id=file_store_id, user_id=user_id
    ).first()
    if not file_check:
        return jsonify({
            "error": "file not found."
        }), 404
    try:
        presigned_url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": s3_bucket, "Key": file_check.file_key,
                "ResponseContentType": file_check.file_content_type,
                "ResponseContentDisposition": (
                    f'inline; filename="{file_check.original_file_name}"'
                )
            },
            ExpiresIn=expires_in
        )
    except botocore.exceptions.NoCredentialsError:
        return jsonify({"error": "storage not configured."}), 500

    except botocore.exceptions.ClientError as e:
        current_app.logger.error(
            f"Failed to generate presigned URL. {e} occured.",
            flush=True
        )
        return jsonify({"error": "could not generate download link"}), 500
    return jsonify({
        "download_url": presigned_url,
        "expires_in": expires_in
    }), 200


@bp.route('/file/delete/<file_store_id>', methods=['DELETE'])
@login_required
def delete_file(file_store_id):
    """ Deletes the file """
    file_check = UserFileStore.query.filter_by(
        id=file_store_id
    ).first()
    if not file_check:
        return jsonify({
            "success": False,
            "error": {
                "message": "file not found."
            }
        }), 404
    s3.delete_object(
        Bucket=os.environ.get("S3_BUCKET_NAME"),
        Key=file_check.file_key
    )
    return jsonify({
        "success": True
    }), 200
