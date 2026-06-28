import os
import tempfile

import pytest

from pdf_generator import generate_pdf, generate_poster, get_piece_geometry


def minimal_hex_piece(color: str = "#ff0000", height: float = 20.0) -> dict:
    return {
        "id": "C0",
        "color": color,
        "height_mm": height,
        "exterior_coords": [
            [7.5, 0], [3.75, 6.495], [-3.75, 6.495],
            [-7.5, 0], [-3.75, -6.495], [3.75, -6.495],
        ],
        "top_vertices_z": [height] * 6,
        "is_cluster": False,
        "box_size_mm": 15.0,
    }


def minimal_metadata() -> dict:
    return {"num_cols": 1, "num_rows": 1, "box_size_mm": 15.0, "R": 7.5}


class TestGetPieceGeometry:
    def test_flat_hex_returns_correct_structure(self):
        geom = get_piece_geometry(15.0, [20.0] * 6)
        assert geom["base_pts"] is not None
        assert len(geom["base_pts"]) == 6
        assert len(geom["walls"]) == 6
        assert len(geom["tabs"]) == 6
        assert "bbox" in geom

    def test_bbox_has_positive_dimensions(self):
        geom = get_piece_geometry(15.0, [20.0] * 6)
        _, _, w, h = geom["bbox"]
        assert w > 0
        assert h > 0

    def test_sloped_top_returns_nonzero_bbox(self):
        geom = get_piece_geometry(15.0, [10.0, 20.0, 15.0, 10.0, 20.0, 15.0])
        _, _, w, h = geom["bbox"]
        assert w > 0
        assert h > 0

    def test_with_exterior_coords(self):
        coords = [
            [7.5, 0], [3.75, 6.495], [-3.75, 6.495],
            [-7.5, 0], [-3.75, -6.495], [3.75, -6.495],
        ]
        geom = get_piece_geometry(15.0, [20.0] * 6, exterior_coords=coords)
        assert geom["base_pts"] is not None
        assert len(geom["base_pts"]) == 6


class TestGeneratePdf:
    def test_creates_non_empty_pdf_file(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            result = generate_pdf([minimal_hex_piece()], minimal_metadata(), path)
            assert os.path.exists(path)
            assert os.path.getsize(path) > 100
            assert result == path
        finally:
            os.unlink(path)

    def test_multiple_pieces_no_crash(self):
        pieces = [
            minimal_hex_piece("#ff0000", 10.0),
            minimal_hex_piece("#0000ff", 30.0),
            minimal_hex_piece("#00ff00", 20.0),
        ]
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            generate_pdf(pieces, minimal_metadata(), path)
            assert os.path.getsize(path) > 100
        finally:
            os.unlink(path)

    def test_piece_without_exterior_coords_no_name_error(self):
        """Regression: NameError fix — piece missing exterior_coords must not crash."""
        piece = minimal_hex_piece()
        del piece["exterior_coords"]
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            generate_pdf([piece], minimal_metadata(), path)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_many_pieces_span_multiple_pages(self):
        pieces = [minimal_hex_piece() for _ in range(50)]
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            generate_pdf(pieces, minimal_metadata(), path)
            assert os.path.getsize(path) > 100
        finally:
            os.unlink(path)


class TestGeneratePoster:
    def test_creates_non_empty_pdf_file(self):
        meta = {**minimal_metadata(), "width_mm": 150, "height_mm": 150}
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            result = generate_poster([minimal_hex_piece()], meta, path)
            assert os.path.exists(path)
            assert os.path.getsize(path) > 100
            assert result == path
        finally:
            os.unlink(path)

    def test_empty_grid_produces_valid_file(self):
        meta = {**minimal_metadata(), "width_mm": 150, "height_mm": 150}
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            generate_poster([], meta, path)
            assert os.path.exists(path)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_large_canvas_no_crash(self):
        meta = {**minimal_metadata(), "width_mm": 1000, "height_mm": 700}
        pieces = [minimal_hex_piece() for _ in range(10)]
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            path = f.name
        try:
            generate_poster(pieces, meta, path)
            assert os.path.getsize(path) > 100
        finally:
            os.unlink(path)
