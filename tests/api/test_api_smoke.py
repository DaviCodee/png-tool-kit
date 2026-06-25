"""Smoke do adaptador de API."""

from __future__ import annotations

import json
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from pngtoolkit.api.app import app
from pngtoolkit.core.registry import all_operations

client = TestClient(app)


def test_list_operations_matches_registry():
    response = client.get("/operations")
    assert response.status_code == 200
    api_names = {item["name"] for item in response.json()}
    assert api_names == {op.name for op in all_operations()}


def test_schema_endpoint():
    response = client.get("/operations/resize/schema")
    assert response.status_code == 200
    assert response.json()["type"] == "object"


def test_run_resize_returns_image(make_image):
    files = [("files", ("foto.png", make_image(80, 60), "image/png"))]
    response = client.post(
        "/operations/resize", files=files, data={"params": json.dumps({"width": 40})}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert Image.open(BytesIO(response.content)).size == (40, 30)


def test_run_favicon_returns_zip(make_image):
    files = [("files", ("logo.png", make_image(256, 256), "image/png"))]
    response = client.post("/operations/favicon", files=files)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"


def test_exif_read_returns_json(jpg_with_exif):
    files = [("files", ("foto.jpg", jpg_with_exif, "image/jpeg"))]
    response = client.post("/operations/exif-read", files=files)
    assert response.status_code == 200
    assert response.json()["exif"]["Make"] == "PngToolKit"


def test_unknown_operation_404(make_image):
    files = [("files", ("foto.png", make_image(), "image/png"))]
    response = client.post("/operations/inexistente", files=files)
    assert response.status_code == 404


def test_invalid_params_422(make_image):
    files = [("files", ("foto.png", make_image(), "image/png"))]
    response = client.post(
        "/operations/resize", files=files, data={"params": json.dumps({"width": -5})}
    )
    assert response.status_code == 422


def test_invalid_image_422(make_image):
    files = [("files", ("foto.png", b"garbage", "image/png"))]
    response = client.post(
        "/operations/resize", files=files, data={"params": json.dumps({"width": 10})}
    )
    assert response.status_code == 422
