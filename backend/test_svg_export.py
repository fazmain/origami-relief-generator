import math
import re

import pytest

from svg_export import generate_svg


def make_hex_item(idx=0, color="#ff0000", height_mm=20.0, R=7.5):
    """Flat-top hex with uniform z."""
    cx, cy = 50.0 + idx * 40, 50.0
    verts = [
        (cx + R, cy),
        (cx + R / 2, cy + math.sqrt(3) * R / 2),
        (cx - R / 2, cy + math.sqrt(3) * R / 2),
        (cx - R, cy),
        (cx - R / 2, cy - math.sqrt(3) * R / 2),
        (cx + R / 2, cy - math.sqrt(3) * R / 2),
    ]
    return {
        "id": f"P{idx}",
        "color": color,
        "height_mm": height_mm,
        "exterior_coords": verts,
        "top_vertices_z": [height_mm] * 6,
        "is_cluster": False,
        "grid_pos": {"col": idx, "row": 0},
    }


def make_metadata(box_size_mm=15.0, max_height_mm=50.0):
    return {
        "num_cols": 5,
        "num_rows": 3,
        "box_size_mm": box_size_mm,
        "R": box_size_mm / 2,
        "min_height_mm": 10.0,
        "max_height_mm": max_height_mm,
        "height_levels": 0,
    }


class TestGenerateSVG:
    def test_returns_string(self):
        svg = generate_svg([make_hex_item()], make_metadata())
        assert isinstance(svg, str)

    def test_valid_xml_header(self):
        svg = generate_svg([make_hex_item()], make_metadata())
        assert svg.startswith("<?xml")
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_svg_has_mm_units(self):
        svg = generate_svg([make_hex_item()], make_metadata())
        assert "mm" in svg

    def test_piece_id_in_output(self):
        svg = generate_svg([make_hex_item(idx=0)], make_metadata())
        assert "P0" in svg

    def test_assembly_label_in_output(self):
        svg = generate_svg([make_hex_item(idx=3)], make_metadata())
        assert "R00-C03" in svg

    def test_color_used_in_fill(self):
        svg = generate_svg([make_hex_item(color="#abcdef")], make_metadata())
        assert "#abcdef" in svg

    def test_empty_grid_produces_valid_svg(self):
        svg = generate_svg([], make_metadata())
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_multiple_pieces(self):
        items = [make_hex_item(i) for i in range(7)]
        svg = generate_svg(items, make_metadata())
        for i in range(7):
            assert f"P{i}" in svg

    def test_cut_paths_present(self):
        svg = generate_svg([make_hex_item()], make_metadata())
        # Cut lines have stroke="black"
        assert 'stroke="black"' in svg

    def test_score_lines_dashed(self):
        svg = generate_svg([make_hex_item()], make_metadata())
        assert "stroke-dasharray" in svg

    def test_skips_items_without_coords(self):
        bad = {"id": "X0", "color": "#000", "height_mm": 10, "exterior_coords": [], "top_vertices_z": [], "grid_pos": {"col": 0, "row": 0}}
        good = make_hex_item(idx=1)
        svg = generate_svg([bad, good], make_metadata())
        assert "X0" not in svg
        assert "P1" in svg

    def test_viewbox_dimensions_positive(self):
        svg = generate_svg([make_hex_item()], make_metadata())
        m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
        assert m, "viewBox not found"
        assert float(m.group(1)) > 0
        assert float(m.group(2)) > 0

    def test_cols_per_row_wrapping(self):
        items = [make_hex_item(i) for i in range(12)]
        svg = generate_svg(items, make_metadata())
        # With COLS_PER_ROW=5 and 12 items, should have 3 rows — height > width proportionally
        m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
        assert m
        # More than 2 row heights means height > just 1 row
        assert float(m.group(2)) > float(m.group(1)) * 0.3
