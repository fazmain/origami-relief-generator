import io

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def make_png_bytes(h: int = 50, w: int = 50, color=(200, 200, 200)) -> bytes:
    img = np.ones((h, w, 3), dtype=np.uint8) * np.array(color, dtype=np.uint8)
    _, encoded = cv2.imencode(".png", img)
    return encoded.tobytes()


LUMINANCE_FORM = {
    "width_mm": "150",
    "height_mm": "150",
    "algorithm": "luminance",
    "min_box_size_mm": "20",
    "k_colors": "2",
    "min_height_mm": "10",
    "max_height_mm": "30",
}

MINIMAL_GRID_PAYLOAD = {
    "grid": [
        {
            "id": "C0",
            "color": "#ff0000",
            "height_mm": 20.0,
            "exterior_coords": [
                [7.5, 0], [3.75, 6.495], [-3.75, 6.495],
                [-7.5, 0], [-3.75, -6.495], [3.75, -6.495],
            ],
            "top_vertices_z": [20.0, 20.0, 20.0, 20.0, 20.0, 20.0],
            "is_cluster": False,
            "box_size_mm": 15.0,
        }
    ],
    "metadata": {"num_cols": 1, "num_rows": 1, "box_size_mm": 15.0, "R": 7.5},
}


class TestPingEndpoint:
    def test_returns_ok(self):
        r = client.get("/api/ping")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestProcessEndpoint:
    def test_valid_luminance_request_returns_grid(self):
        png = make_png_bytes()
        r = client.post(
            "/api/process",
            data=LUMINANCE_FORM,
            files={"image": ("test.png", io.BytesIO(png), "image/png")},
        )
        assert r.status_code == 200
        body = r.json()
        assert "grid" in body
        assert "metadata" in body
        assert len(body["grid"]) > 0

    def test_non_image_content_type_rejected(self):
        r = client.post(
            "/api/process",
            data=LUMINANCE_FORM,
            files={"image": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        assert r.status_code == 400

    def test_zero_width_rejected(self):
        png = make_png_bytes()
        form = {**LUMINANCE_FORM, "width_mm": "0"}
        r = client.post(
            "/api/process",
            data=form,
            files={"image": ("test.png", io.BytesIO(png), "image/png")},
        )
        assert r.status_code == 400

    def test_negative_height_rejected(self):
        png = make_png_bytes()
        form = {**LUMINANCE_FORM, "height_mm": "-10"}
        r = client.post(
            "/api/process",
            data=form,
            files={"image": ("test.png", io.BytesIO(png), "image/png")},
        )
        assert r.status_code == 400

    def test_invalid_algorithm_rejected(self):
        png = make_png_bytes()
        form = {**LUMINANCE_FORM, "algorithm": "garbage"}
        r = client.post(
            "/api/process",
            data=form,
            files={"image": ("test.png", io.BytesIO(png), "image/png")},
        )
        assert r.status_code == 400

    def test_corrupt_image_bytes_returns_400(self):
        r = client.post(
            "/api/process",
            data=LUMINANCE_FORM,
            files={"image": ("test.png", io.BytesIO(b"notanimage"), "image/png")},
        )
        assert r.status_code == 400

    def test_grid_cells_have_expected_shape(self):
        png = make_png_bytes()
        r = client.post(
            "/api/process",
            data=LUMINANCE_FORM,
            files={"image": ("test.png", io.BytesIO(png), "image/png")},
        )
        assert r.status_code == 200
        for cell in r.json()["grid"]:
            assert "id" in cell
            assert "color" in cell
            assert "exterior_coords" in cell
            assert "top_vertices_z" in cell
            assert len(cell["top_vertices_z"]) == len(cell["exterior_coords"])


class TestPdfEndpoint:
    def test_valid_payload_returns_pdf(self):
        r = client.post("/api/pdf", json=MINIMAL_GRID_PAYLOAD)
        assert r.status_code == 200
        assert "application/pdf" in r.headers["content-type"]

    def test_missing_grid_returns_400(self):
        r = client.post("/api/pdf", json={"metadata": MINIMAL_GRID_PAYLOAD["metadata"]})
        assert r.status_code == 400

    def test_missing_metadata_returns_400(self):
        r = client.post("/api/pdf", json={"grid": MINIMAL_GRID_PAYLOAD["grid"]})
        assert r.status_code == 400

    def test_empty_body_returns_400(self):
        r = client.post("/api/pdf", json={})
        assert r.status_code == 400


class TestPosterEndpoint:
    def test_valid_payload_returns_pdf(self):
        payload = {
            **MINIMAL_GRID_PAYLOAD,
            "metadata": {**MINIMAL_GRID_PAYLOAD["metadata"], "width_mm": 150, "height_mm": 150},
        }
        r = client.post("/api/pdf_poster", json=payload)
        assert r.status_code == 200
        assert "application/pdf" in r.headers["content-type"]

    def test_missing_grid_returns_400(self):
        r = client.post("/api/pdf_poster", json={"metadata": MINIMAL_GRID_PAYLOAD["metadata"]})
        assert r.status_code == 400
