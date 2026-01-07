import os
import uuid
import boto3
import botocore.exceptions


def generate_error_response(error_bool, error_message, status_code=None):
    """Returns error message in the correct format"""
    return {
        "error": error_bool, "error_message": error_message,
        "status_code": status_code if status_code else None
    }


def generate_s3_presigned_upload_url(json_data):
    """Generates presigned url for chat file upload to s3"""
    user_id = json_data['user_id']
    filename = json_data['file_name']
    if filename != '':
        file_ext = filename.split('.')[-1]
        if file_ext not in os.environ.get('ALLOWED_FILE_TYPES'):
            return generate_error_response(
                True, "file type not accepted.", 400
            )
    else:
        return generate_error_response(
            True, "filename cannot be empty.", 400
        )
    # generating secure filename
    file_key = f"files/{user_id}/{uuid.uuid4()}.{file_ext}"

    s3 = boto3.client("s3", region_name=os.environ.get("S3_REGION"))
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
        print("AWS credentials not configured", flush=True)
        return generate_error_response(True, "storage not configured.", 500)

    except botocore.exceptions.PartialCredentialsError:
        print("Incomplete AWS credentials", flush=True)
        return generate_error_response(True, "storage not configured.", 500)

    except botocore.exceptions.ParamValidationError:
        print("Invalid presign parameters", flush=True)
        return generate_error_response(
            True, "internal configuration error.", 500
        )

    except botocore.exceptions.ClientError:
        print("AWS client error during presign", flush=True)
        return generate_error_response(
            True, "could not generate upload link.", 500
        )
