import os
import jwt
import json
import uuid
import magic
import boto3
import requests
import botocore.exceptions
from flask import g, current_app
from sqlalchemy.exc import IntegrityError
from requests.exceptions import RequestException

from core import db, s3, cache
from core.models import UserFileStore


def get_jwk(kid, cache=None):
    """
    Gets JWK with key id
    """
    # if cache exists then load from cache
    key = None
    if cache:
        key = cache.get(kid)
    try:
        if key is None:
            jwks_uri = os.environ.get('AUTH0_JWKS_URI')
            jwks = requests.get(jwks_uri, timeout=5)
            jwks.raise_for_status()
            keys = jwks.json().get('keys')
            for k in keys:
                if cache:
                    cache.set(k['kid'], k)
                if k['kid'] == kid:
                    key = k
        if key is not None:
            return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
    except (RequestException, ValueError, KeyError) as e:
        raise Exception("Failed to resolve JWK") from e


def token_decode(token):
    """Decodes auth0 JWT tokens"""
    JWT_ISSUER = os.environ.get('AUTH0_ISSUER')
    try:
        key_id = jwt.get_unverified_header(token)['kid']
        jwk = get_jwk(
            key_id, cache=cache
        )
        token_data = jwt.decode(
            token, jwk, verify=True, issuer=JWT_ISSUER,
            audience=os.environ.get('AUTH0_AUDIENCE'), algorithms=['RS256'],
            options={"verify_iat": False}
        )
        if token_data['azp'] == os.environ.get('AUTH0_REGULAR_CLIENT_ID'):
            auth0_id_complete = token_data['sub']
            auth0_id = auth0_id_complete.split('|')
            g.user_id = auth0_id[1]
            return ({
                "error": False
            })
        else:
            return ({
                "error": True,
                "error_message": "User not allowed."
            })
    except Exception as e:
        current_app.logger.error("Error occured during authentication", e)
        return ({
            "error": True,
            "error_message": "Unauthorized."
        })


def generate_error_response(error_bool, error_message, status_code=None):
    """Returns error message in the correct format"""
    return {
        "error": error_bool, "error_message": error_message,
        "status_code": status_code if status_code else None
    }


def generate_s3_presigned_upload_url(json_data):
    """Generates presigned url for chat file upload to s3"""
    user_id = g.user_id
    filename = json_data['file_name']
    if filename != '':
        file_ext = filename.split('.')[-1]
        if file_ext not in os.environ.get('ALLOWED_FILE_EXTENSIONS'):
            return generate_error_response(
                True, "file type not accepted.", 400
            )
    else:
        return generate_error_response(
            True, "filename cannot be empty.", 400
        )
    # generating secure filename
    file_key = f"attachments/files/{user_id}/{uuid.uuid4()}.{file_ext}"

    s3_bucket = os.environ.get("S3_BUCKET_NAME")
    expires_in = int(os.environ.get('PRESIGNED_URL_EXPIRATION_TIME'))
    try:
        presigned = s3.generate_presigned_post(
            Bucket=s3_bucket, Key=file_key,
            Conditions=[
                [
                    "content-length-range", 1,
                    int(os.environ.get('MAX_FILE_SIZE'))
                ], {"x-amz-server-side-encryption": "AES256"}
            ],
            Fields={"x-amz-server-side-encryption": "AES256"},
            ExpiresIn=expires_in
        )
        return {
            "error": False, "presigned": presigned,
            "file_key": file_key
        }
    except botocore.exceptions.NoCredentialsError:
        current_app.logger.error("AWS credentials not configured", flush=True)
        return generate_error_response(True, "storage not configured.", 500)

    except botocore.exceptions.PartialCredentialsError:
        current_app.logger.error("Incomplete AWS credentials", flush=True)
        return generate_error_response(True, "storage not configured.", 500)

    except botocore.exceptions.ParamValidationError:
        current_app.logger.error("Invalid presign parameters", flush=True)
        return generate_error_response(
            True, "internal configuration error.", 500
        )

    except botocore.exceptions.ClientError:
        current_app.logger.error("AWS client error during presign", flush=True)
        return generate_error_response(
            True, "could not generate upload link.", 500
        )


def upload_checks_and_additions(json_data):
    """Validates uploaded file and adds it to UserFileStore"""
    # Ensuring user owns the key
    user_id = g.user_id
    file_key = json_data['file_key']
    s3_bucket = os.environ.get("S3_BUCKET_NAME")
    if not file_key.startswith(f"attachments/files/{user_id}/"):
        return generate_error_response(True, "invalid file key.")

    # Fetching the metadata from S3
    try:
        head = s3.head_object(Bucket=s3_bucket, Key=file_key)
    except s3.exceptions.NoSuchKey:
        return generate_error_response(True, "file not found.")

    # Enforcing size
    if head["ContentLength"] > int(os.environ.get('MAX_FILE_SIZE')):
        s3.delete_object(
            Bucket=s3_bucket, Key=file_key
        )
        return generate_error_response(True, "File too large.")

    # Magic Bytes checking
    obj = s3.get_object(
        Bucket=s3_bucket, Key=file_key, Range="bytes=0-8191"
    )
    header_data = obj["Body"].read()
    real_mime = magic.Magic(mime=True).from_buffer(header_data)

    if real_mime not in os.environ.get('ALLOWED_FILE_TYPES'):
        s3.delete_object(Bucket=s3_bucket, Key=file_key)
        return generate_error_response(True, "invalid content type.")

    # Adding the file key to database
    file_exists = UserFileStore.query.filter_by(
        user_id=user_id, file_key=file_key
    ).first()
    if file_exists is not None:
        return generate_error_response(True, "File already added.")
    try:
        store_ins = UserFileStore(
            user_id=user_id, file_key=file_key,
            file_category=json_data['file_category'],
            file_content_type=real_mime,
            original_file_name=json_data['original_file_name']
        )
        db.session.add(store_ins)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return generate_error_response(True, "File already registered.")
    return {
        "error": False
    }
