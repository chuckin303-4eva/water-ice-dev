import io
import os

import pytest
from PIL import Image

from app.core.config import settings
from app.core.models.user import User
from app.services import geocoding_service
from app.services.geocoding_service import GeocodeResult
from tests.conftest import auth_headers

_FAKE_GEOCODE = GeocodeResult(
    latitude=39.7392,
    longitude=-104.9903,
    address="123 Main St, Denver, CO 80202",
    city_name="Denver",
    county_name="Denver",
    state_code="CO",
    zip_code="80202",
)


@pytest.fixture(autouse=True)
def _mock_geocoding(monkeypatch):
    monkeypatch.setattr(geocoding_service, "geocode_address", lambda address: _FAKE_GEOCODE)
    monkeypatch.setattr(geocoding_service, "reverse_geocode", lambda lat, lon: _FAKE_GEOCODE)


@pytest.fixture(autouse=True)
def _use_temp_upload_dir(monkeypatch, tmp_path):
    # Real files, but in a throwaway pytest tmp_path instead of the real
    # backend/uploads/ -- auto-cleaned, no side effects on the repo.
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))


def _make_jpeg_bytes(color=(200, 50, 50), size=(20, 20)) -> bytes:
    image = Image.new("RGB", size, color)
    buf = io.BytesIO()
    image.save(buf, format="JPEG")
    return buf.getvalue()


def _make_location(client, headers) -> dict:
    return client.post("/locations", json={"address": "123 Main St, Denver, CO"}, headers=headers).json()


def _make_competitor(client, headers) -> dict:
    return client.post(
        "/competitors", json={"address": "456 Rival Ave", "name": "Test Rival"}, headers=headers
    ).json()


def test_upload_photo_for_location(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    location = _make_location(client, headers)

    response = client.post(
        f"/locations/{location['id']}/photos",
        files={"file": ("site.jpg", _make_jpeg_bytes(), "image/jpeg")},
        data={"caption": "Front of the store"},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["entity_type"] == "location"
    assert body["entity_id"] == location["id"]
    assert body["caption"] == "Front of the store"
    assert body["file_url"].startswith("/media/location/")
    assert body["uploaded_by"] == test_user.id
    assert body["is_primary"] is False

    # The compressed file actually landed on disk where file_url implies.
    filename = body["file_url"].rsplit("/", 1)[-1]
    assert os.path.exists(os.path.join(settings.upload_dir, "location", filename))


def test_upload_photo_for_competitor(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    competitor = _make_competitor(client, headers)

    response = client.post(
        f"/competitors/{competitor['id']}/photos",
        files={"file": ("rival.png", _make_jpeg_bytes(), "image/png")},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["entity_type"] == "competitor"
    assert body["entity_id"] == competitor["id"]
    assert body["file_url"].startswith("/media/competitor/")


def test_upload_rejects_unsupported_content_type(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    location = _make_location(client, headers)

    response = client.post(
        f"/locations/{location['id']}/photos",
        files={"file": ("notes.txt", b"not an image", "text/plain")},
        headers=headers,
    )
    assert response.status_code == 422


def test_upload_rejects_file_that_isnt_really_an_image(client, test_user: User) -> None:
    """Content-Type says image/jpeg, but the bytes aren't a real image --
    Pillow's decode-to-verify should catch this."""
    headers = auth_headers(client, test_user)
    location = _make_location(client, headers)

    response = client.post(
        f"/locations/{location['id']}/photos",
        files={"file": ("fake.jpg", b"this is not actually a jpeg", "image/jpeg")},
        headers=headers,
    )
    assert response.status_code == 422


def test_upload_rejects_oversized_file(client, test_user: User, monkeypatch) -> None:
    monkeypatch.setattr(settings, "max_upload_size_bytes", 10)
    headers = auth_headers(client, test_user)
    location = _make_location(client, headers)

    response = client.post(
        f"/locations/{location['id']}/photos",
        files={"file": ("site.jpg", _make_jpeg_bytes(), "image/jpeg")},
        headers=headers,
    )
    assert response.status_code == 422


def test_upload_photo_for_nonexistent_location_404(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    response = client.post(
        "/locations/00000000-0000-0000-0000-000000000000/photos",
        files={"file": ("site.jpg", _make_jpeg_bytes(), "image/jpeg")},
        headers=headers,
    )
    assert response.status_code == 404


def test_list_photos_for_location(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    location = _make_location(client, headers)
    client.post(
        f"/locations/{location['id']}/photos",
        files={"file": ("a.jpg", _make_jpeg_bytes(), "image/jpeg")},
        headers=headers,
    )
    client.post(
        f"/locations/{location['id']}/photos",
        files={"file": ("b.jpg", _make_jpeg_bytes(), "image/jpeg")},
        headers=headers,
    )

    response = client.get(f"/locations/{location['id']}/photos", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_delete_photo_removes_file_and_row(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    location = _make_location(client, headers)
    photo = client.post(
        f"/locations/{location['id']}/photos",
        files={"file": ("a.jpg", _make_jpeg_bytes(), "image/jpeg")},
        headers=headers,
    ).json()
    filename = photo["file_url"].rsplit("/", 1)[-1]
    file_path = os.path.join(settings.upload_dir, "location", filename)
    assert os.path.exists(file_path)

    response = client.delete(f"/locations/{location['id']}/photos/{photo['id']}", headers=headers)
    assert response.status_code == 204
    assert not os.path.exists(file_path)

    remaining = client.get(f"/locations/{location['id']}/photos", headers=headers).json()
    assert remaining == []


def test_is_primary_unsets_previous_primary(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    location = _make_location(client, headers)
    first = client.post(
        f"/locations/{location['id']}/photos",
        files={"file": ("a.jpg", _make_jpeg_bytes(), "image/jpeg")},
        data={"is_primary": "true"},
        headers=headers,
    ).json()
    second = client.post(
        f"/locations/{location['id']}/photos",
        files={"file": ("b.jpg", _make_jpeg_bytes(), "image/jpeg")},
        data={"is_primary": "true"},
        headers=headers,
    ).json()
    assert second["is_primary"] is True

    photos = {p["id"]: p for p in client.get(f"/locations/{location['id']}/photos", headers=headers).json()}
    assert photos[first["id"]]["is_primary"] is False
    assert photos[second["id"]]["is_primary"] is True


def test_cannot_delete_photo_via_wrong_parent_entity(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    location = _make_location(client, headers)
    other_location = _make_location(client, headers)
    photo = client.post(
        f"/locations/{location['id']}/photos",
        files={"file": ("a.jpg", _make_jpeg_bytes(), "image/jpeg")},
        headers=headers,
    ).json()

    response = client.delete(f"/locations/{other_location['id']}/photos/{photo['id']}", headers=headers)
    assert response.status_code == 404


def test_cannot_delete_location_photo_via_competitor_endpoint(client, test_user: User) -> None:
    headers = auth_headers(client, test_user)
    location = _make_location(client, headers)
    competitor = _make_competitor(client, headers)
    photo = client.post(
        f"/locations/{location['id']}/photos",
        files={"file": ("a.jpg", _make_jpeg_bytes(), "image/jpeg")},
        headers=headers,
    ).json()

    response = client.delete(f"/competitors/{competitor['id']}/photos/{photo['id']}", headers=headers)
    assert response.status_code == 404
