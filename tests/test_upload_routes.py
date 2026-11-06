import botocore.exceptions
import pytest

import core.upload_app.routes as routes
from core import db
from core.models import UserFileStore


def add_file(user_id="user-1"):
    file_record = UserFileStore(
        user_id=user_id,
        file_key=f"attachments/files/{user_id}/object.jpg",
        file_category="image",
        file_content_type="image/jpeg",
        original_file_name="photo.jpg",
    )
    db.session.add(file_record)
    db.session.commit()
    return file_record


def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json == {"status": "ok"}


def test_generate_upload_url_returns_presigned_payload(
    client, auth_headers, monkeypatch
):
    monkeypatch.setattr(
        routes,
        "generate_s3_presigned_upload_url",
        lambda _data: {
            "error": False,
            "presigned": {"url": "https://s3.example/upload", "fields": {"key": "x"}},
        },
    )

    response = client.post(
        "/file/generate_file_upload_url",
        json={"file_name": "photo.jpg"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json == {
        "success": True,
        "upload_url": "https://s3.example/upload",
        "fields": {"key": "x"},
    }


def test_generate_upload_url_reports_helper_error(
    client, auth_headers, monkeypatch
):
    monkeypatch.setattr(
        routes,
        "generate_s3_presigned_upload_url",
        lambda _data: {
            "error": True,
            "error_message": "file type not accepted.",
            "status_code": 400,
        },
    )

    response = client.post(
        "/file/generate_file_upload_url",
        json={"file_name": "photo.exe"},
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json == {
        "success": False,
        "error": {"message": "file type not accepted."},
    }


def test_generate_upload_url_requires_authentication(client):
    response = client.post(
        "/file/generate_file_upload_url", json={"file_name": "photo.jpg"}
    )

    assert response.status_code == 401


def test_post_upload_validation_returns_success(
    client, auth_headers, monkeypatch
):
    monkeypatch.setattr(
        routes, "upload_checks_and_additions", lambda _data: {"error": False}
    )

    response = client.post(
        "/file/post_upload_validation",
        json={
            "file_key": "attachments/files/user-1/object.jpg",
            "file_category": "image",
            "original_file_name": "photo.jpg",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json == {"message": "successfully added attachment."}


def test_post_upload_validation_returns_error(
    client, auth_headers, monkeypatch
):
    monkeypatch.setattr(
        routes,
        "upload_checks_and_additions",
        lambda _data: {"error": True, "error_message": "file not found."},
    )

    response = client.post(
        "/file/post_upload_validation",
        json={
            "file_key": "attachments/files/user-1/missing.jpg",
            "file_category": "image",
            "original_file_name": "missing.jpg",
        },
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json == {"error": "file not found."}


def test_download_returns_not_found_for_another_users_file(
    app, client, auth_headers
):
    with app.app_context():
        file_record = add_file(user_id="user-2")
        file_id = file_record.id

    response = client.post(
        "/file/download",
        json={"file_store_id": file_id, "file_key": "ignored-by-route"},
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json == {"error": "file not found."}


def test_download_returns_presigned_link(
    app, client, auth_headers, monkeypatch
):
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("PRESIGNED_URL_EXPIRATION_TIME", "600")
    with app.app_context():
        file_record = add_file()
        file_id = file_record.id
    monkeypatch.setattr(
        routes.s3,
        "generate_presigned_url",
        lambda **_kwargs: "https://s3.example/download",
    )

    response = client.post(
        "/file/download",
        json={"file_store_id": file_id, "file_key": "ignored-by-route"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json == {
        "download_url": "https://s3.example/download",
        "expires_in": 600,
    }


def test_download_handles_missing_storage_credentials(
    app, client, auth_headers, monkeypatch
):
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("PRESIGNED_URL_EXPIRATION_TIME", "600")
    with app.app_context():
        file_record = add_file()
        file_id = file_record.id

    def raise_no_credentials(**_kwargs):
        raise botocore.exceptions.NoCredentialsError()

    monkeypatch.setattr(routes.s3, "generate_presigned_url", raise_no_credentials)
    response = client.post(
        "/file/download",
        json={"file_store_id": file_id, "file_key": "ignored-by-route"},
        headers=auth_headers,
    )

    assert response.status_code == 500
    assert response.json == {"error": "storage not configured."}


def test_delete_removes_metadata_and_storage_object(
    app, client, auth_headers, monkeypatch
):
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
    with app.app_context():
        file_record = add_file()
        file_id = file_record.id
        file_key = file_record.file_key
    deleted = []
    monkeypatch.setattr(
        routes.s3,
        "delete_object",
        lambda **kwargs: deleted.append(kwargs),
    )

    response = client.delete(f"/file/delete/{file_id}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json == {"success": True}
    assert deleted == [{"Bucket": "test-bucket", "Key": file_key}]
    with app.app_context():
        assert db.session.get(UserFileStore, file_id) is None


def test_delete_returns_not_found_for_another_users_file(
    app, client, auth_headers
):
    with app.app_context():
        file_record = add_file(user_id="user-2")
        file_id = file_record.id

    response = client.delete(f"/file/delete/{file_id}", headers=auth_headers)

    assert response.status_code == 404
    assert response.json["error"]["message"] == "file not found."


@pytest.mark.parametrize("endpoint", ["/file/download", "/file/post_upload_validation"])
def test_json_routes_reject_missing_required_fields(
    client, auth_headers, endpoint
):
    response = client.post(endpoint, json={}, headers=auth_headers)

    assert response.status_code == 400
