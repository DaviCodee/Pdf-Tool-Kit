"""Smoke do adaptador de API."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from pdftoolkit.api.app import app
from pdftoolkit.core.registry import all_operations
from pdftoolkit.engines import pypdf_engine as pe

client = TestClient(app)


def test_list_operations_matches_registry():
    response = client.get("/operations")
    assert response.status_code == 200
    api_names = {item["name"] for item in response.json()}
    assert api_names == {op.name for op in all_operations()}


def test_schema_endpoint():
    response = client.get("/operations/split/schema")
    assert response.status_code == 200
    assert response.json()["type"] == "object"


def test_run_merge_returns_pdf(make_pdf):
    files = [
        ("files", ("a.pdf", make_pdf(2, "A"), "application/pdf")),
        ("files", ("b.pdf", make_pdf(3, "B"), "application/pdf")),
    ]
    response = client.post("/operations/merge", files=files)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert pe.count_pages(response.content) == 5


def test_run_split_returns_zip(make_pdf):
    files = [("files", ("x.pdf", make_pdf(5), "application/pdf"))]
    response = client.post(
        "/operations/split", files=files, data={"params": json.dumps({"every": 2})}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"


def test_metadata_read_returns_json(make_pdf):
    files = [("files", ("x.pdf", make_pdf(3), "application/pdf"))]
    response = client.post("/operations/metadata-read", files=files)
    assert response.status_code == 200
    assert response.json()["metadata"]["/Pages"] == "3"


def test_unknown_operation_404(make_pdf):
    files = [("files", ("x.pdf", make_pdf(1), "application/pdf"))]
    response = client.post("/operations/inexistente", files=files)
    assert response.status_code == 404


def test_invalid_params_422(make_pdf):
    files = [("files", ("x.pdf", make_pdf(2), "application/pdf"))]
    response = client.post(
        "/operations/rotate", files=files, data={"params": json.dumps({"degrees": 45})}
    )
    assert response.status_code == 422


def test_multi_file_fan_out_returns_zip(make_pdf):
    import io
    import zipfile

    files = [
        ("files", ("a.pdf", make_pdf(2, "A"), "application/pdf")),
        ("files", ("sub/b.pdf", make_pdf(1, "B"), "application/pdf")),
    ]
    response = client.post(
        "/operations/rotate", files=files, data={"params": json.dumps({"degrees": 90})}
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/zip"
    names = zipfile.ZipFile(io.BytesIO(response.content)).namelist()
    assert "rotacionado.pdf" in names
    assert "sub/rotacionado.pdf" in names


def test_listing_exposes_fan_out():
    response = client.get("/operations")
    ops = {op["name"]: op for op in response.json()}
    assert ops["rotate"]["fan_out"] == "True"
