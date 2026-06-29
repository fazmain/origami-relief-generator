import pytest
from pattern_generator import generate_pattern


PATTERNS = ["waves", "radial", "spiral", "spikes", "grid"]


class TestGeneratePattern:
    def test_returns_grid_and_metadata(self):
        result = generate_pattern()
        assert "grid" in result
        assert "metadata" in result

    @pytest.mark.parametrize("pattern", PATTERNS)
    def test_all_patterns_produce_grid(self, pattern):
        result = generate_pattern(pattern=pattern, width_mm=100, height_mm=100, box_size_mm=20)
        assert len(result["grid"]) > 0

    def test_cells_have_required_fields(self):
        result = generate_pattern(width_mm=100, height_mm=100, box_size_mm=20)
        for cell in result["grid"]:
            assert "id" in cell
            assert "color" in cell
            assert "height_mm" in cell
            assert "exterior_coords" in cell
            assert "top_vertices_z" in cell
            assert "grid_pos" in cell

    def test_hex_cells_have_6_vertices(self):
        result = generate_pattern(width_mm=100, height_mm=100, box_size_mm=20)
        for cell in result["grid"]:
            assert len(cell["exterior_coords"]) == 6
            assert len(cell["top_vertices_z"]) == 6

    def test_heights_within_bounds(self):
        result = generate_pattern(
            width_mm=150, height_mm=150, box_size_mm=25,
            min_height_mm=10.0, max_height_mm=40.0,
        )
        for cell in result["grid"]:
            assert 10.0 <= cell["height_mm"] <= 40.0 + 1e-6

    def test_k_colors_limits_color_count(self):
        result = generate_pattern(width_mm=200, height_mm=200, box_size_mm=20, k_colors=3)
        colors = {cell["color"] for cell in result["grid"]}
        assert len(colors) <= 3

    def test_height_levels_quantizes(self):
        result = generate_pattern(
            width_mm=200, height_mm=200, box_size_mm=20,
            min_height_mm=10.0, max_height_mm=40.0, height_levels=4,
        )
        heights = {round(cell["height_mm"], 1) for cell in result["grid"]}
        assert len(heights) <= 4

    def test_metadata_has_pattern_key(self):
        result = generate_pattern(pattern="spiral")
        assert result["metadata"]["pattern"] == "spiral"

    def test_metadata_has_dimensions(self):
        result = generate_pattern(width_mm=200, height_mm=150)
        assert result["metadata"]["width_mm"] == 200.0
        assert result["metadata"]["height_mm"] == 150.0

    def test_colors_are_valid_hex(self):
        result = generate_pattern(width_mm=100, height_mm=100, box_size_mm=20, k_colors=5)
        import re
        for cell in result["grid"]:
            assert re.match(r"^#[0-9a-f]{6}$", cell["color"]), f"Invalid color: {cell['color']}"


class TestPatternApiEndpoint:
    def test_valid_waves_request(self):
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        r = client.post("/api/pattern", json={"pattern": "waves", "width_mm": 100, "height_mm": 100, "box_size_mm": 20})
        assert r.status_code == 200
        body = r.json()
        assert "grid" in body
        assert "metadata" in body
        assert len(body["grid"]) > 0

    def test_invalid_pattern_returns_400(self):
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        r = client.post("/api/pattern", json={"pattern": "garbage"})
        assert r.status_code == 400

    @pytest.mark.parametrize("pattern", ["waves", "radial", "spiral", "spikes", "grid"])
    def test_all_patterns_via_api(self, pattern):
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        r = client.post("/api/pattern", json={
            "pattern": pattern, "width_mm": 80, "height_mm": 80, "box_size_mm": 20,
        })
        assert r.status_code == 200
        assert len(r.json()["grid"]) > 0
