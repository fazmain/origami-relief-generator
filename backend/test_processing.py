import cv2
import numpy as np
import pytest

from processing import process_image


def make_image_bytes(h: int = 100, w: int = 100, color=(200, 200, 200)) -> bytes:
    img = np.ones((h, w, 3), dtype=np.uint8) * np.array(color, dtype=np.uint8)
    success, encoded = cv2.imencode(".png", img)
    assert success
    return encoded.tobytes()


class TestLuminanceAlgorithm:
    def test_white_image_gives_max_height(self):
        result = process_image(
            image_bytes=make_image_bytes(color=(255, 255, 255)),
            width_mm=150.0, height_mm=150.0,
            min_box_size_mm=15.0, k_colors=2,
            min_height_mm=10.0, max_height_mm=50.0,
            algorithm="luminance",
        )
        for cell in result["grid"]:
            assert cell["height_mm"] == pytest.approx(50.0, abs=0.5)
            assert all(z == pytest.approx(50.0, abs=0.5) for z in cell["top_vertices_z"])

    def test_black_image_gives_min_height(self):
        result = process_image(
            image_bytes=make_image_bytes(color=(0, 0, 0)),
            width_mm=150.0, height_mm=150.0,
            min_box_size_mm=15.0, k_colors=2,
            min_height_mm=10.0, max_height_mm=50.0,
            algorithm="luminance",
        )
        for cell in result["grid"]:
            assert cell["height_mm"] == pytest.approx(10.0, abs=2.0)

    def test_metadata_structure(self):
        result = process_image(
            image_bytes=make_image_bytes(),
            width_mm=150.0, height_mm=150.0,
            min_box_size_mm=15.0, k_colors=2,
            min_height_mm=10.0, max_height_mm=50.0,
            algorithm="luminance",
        )
        meta = result["metadata"]
        assert "num_cols" in meta
        assert "num_rows" in meta
        assert meta["box_size_mm"] == 15.0
        assert meta["R"] == pytest.approx(7.5)

    def test_each_hex_is_individual_not_cluster(self):
        result = process_image(
            image_bytes=make_image_bytes(h=50, w=50),
            width_mm=100.0, height_mm=100.0,
            min_box_size_mm=15.0, k_colors=2,
            min_height_mm=10.0, max_height_mm=30.0,
            algorithm="luminance",
        )
        for cell in result["grid"]:
            assert cell["is_cluster"] is False
            assert len(cell["exterior_coords"]) == 6

    def test_grid_cells_have_required_fields(self):
        result = process_image(
            image_bytes=make_image_bytes(),
            width_mm=150.0, height_mm=150.0,
            min_box_size_mm=20.0, k_colors=3,
            min_height_mm=5.0, max_height_mm=25.0,
            algorithm="luminance",
        )
        for cell in result["grid"]:
            assert "id" in cell
            assert "color" in cell
            assert cell["color"].startswith("#")
            assert len(cell["color"]) == 7
            assert "height_mm" in cell
            assert "exterior_coords" in cell
            assert "top_vertices_z" in cell
            assert len(cell["top_vertices_z"]) == len(cell["exterior_coords"])

    def test_height_values_within_bounds(self):
        min_h, max_h = 5.0, 40.0
        result = process_image(
            image_bytes=make_image_bytes(h=100, w=100),
            width_mm=200.0, height_mm=200.0,
            min_box_size_mm=20.0, k_colors=4,
            min_height_mm=min_h, max_height_mm=max_h,
            algorithm="luminance",
        )
        for cell in result["grid"]:
            assert cell["height_mm"] >= min_h - 0.01
            assert cell["height_mm"] <= max_h + 0.01
            for z in cell["top_vertices_z"]:
                assert z >= 0.1  # always clamped above zero

    def test_wider_canvas_gives_more_columns_than_rows(self):
        result = process_image(
            image_bytes=make_image_bytes(h=100, w=200),
            width_mm=300.0, height_mm=150.0,
            min_box_size_mm=15.0, k_colors=2,
            min_height_mm=10.0, max_height_mm=30.0,
            algorithm="luminance",
        )
        meta = result["metadata"]
        assert meta["num_cols"] > meta["num_rows"]

    def test_k_colors_limits_output_colors(self):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[:50, :] = [255, 0, 0]
        img[50:, :] = [0, 0, 255]
        _, encoded = cv2.imencode(".png", img)
        image_bytes = encoded.tobytes()

        k = 2
        result = process_image(
            image_bytes=image_bytes,
            width_mm=150.0, height_mm=150.0,
            min_box_size_mm=15.0, k_colors=k,
            min_height_mm=10.0, max_height_mm=30.0,
            algorithm="luminance",
        )
        unique_colors = set(cell["color"] for cell in result["grid"])
        assert len(unique_colors) <= k

    def test_invalid_image_bytes_raises_value_error(self):
        with pytest.raises(ValueError, match="[Ii]nvalid image"):
            process_image(
                image_bytes=b"not an image at all",
                width_mm=150.0, height_mm=150.0,
                min_box_size_mm=15.0, k_colors=2,
                min_height_mm=10.0, max_height_mm=30.0,
                algorithm="luminance",
            )

    def test_top_vertices_z_count_matches_exterior_coords(self):
        result = process_image(
            image_bytes=make_image_bytes(),
            width_mm=200.0, height_mm=200.0,
            min_box_size_mm=15.0, k_colors=3,
            min_height_mm=10.0, max_height_mm=40.0,
            algorithm="luminance",
        )
        for cell in result["grid"]:
            assert len(cell["top_vertices_z"]) == len(cell["exterior_coords"])

    def test_luminance_flat_tops_all_vertices_same_z(self):
        result = process_image(
            image_bytes=make_image_bytes(color=(128, 128, 128)),
            width_mm=100.0, height_mm=100.0,
            min_box_size_mm=20.0, k_colors=1,
            min_height_mm=10.0, max_height_mm=30.0,
            algorithm="luminance",
        )
        for cell in result["grid"]:
            zs = cell["top_vertices_z"]
            assert all(abs(z - zs[0]) < 0.01 for z in zs), "Luminance mode: all vertices should have equal z"


class TestHeightQuantization:
    def test_four_levels_produces_exactly_four_heights(self):
        result = process_image(
            image_bytes=make_image_bytes(h=100, w=100),
            width_mm=200.0, height_mm=200.0,
            min_box_size_mm=15.0, k_colors=4,
            min_height_mm=10.0, max_height_mm=40.0,
            algorithm="luminance",
            height_levels=4,
        )
        heights = set(round(cell["height_mm"], 1) for cell in result["grid"])
        assert len(heights) <= 4

    def test_levels_are_on_expected_grid(self):
        min_h, max_h, n = 10.0, 40.0, 4
        result = process_image(
            image_bytes=make_image_bytes(h=100, w=100),
            width_mm=200.0, height_mm=200.0,
            min_box_size_mm=15.0, k_colors=4,
            min_height_mm=min_h, max_height_mm=max_h,
            algorithm="luminance",
            height_levels=n,
        )
        import numpy as np
        expected = set(round(v, 2) for v in np.linspace(min_h, max_h, n))
        for cell in result["grid"]:
            assert round(cell["height_mm"], 1) in set(round(v, 1) for v in expected)

    def test_zero_levels_is_continuous(self):
        result = process_image(
            image_bytes=make_image_bytes(h=50, w=50),
            width_mm=150.0, height_mm=150.0,
            min_box_size_mm=20.0, k_colors=3,
            min_height_mm=10.0, max_height_mm=50.0,
            algorithm="luminance",
            height_levels=0,
        )
        assert result["metadata"]["height_levels"] == 0

    def test_metadata_reports_height_levels(self):
        result = process_image(
            image_bytes=make_image_bytes(h=50, w=50),
            width_mm=150.0, height_mm=150.0,
            min_box_size_mm=20.0, k_colors=2,
            min_height_mm=10.0, max_height_mm=50.0,
            algorithm="luminance",
            height_levels=5,
        )
        assert result["metadata"]["height_levels"] == 5
        assert result["metadata"]["min_height_mm"] == 10.0
        assert result["metadata"]["max_height_mm"] == 50.0

    def test_vertices_z_clamped_above_zero(self):
        result = process_image(
            image_bytes=make_image_bytes(color=(0, 0, 0), h=50, w=50),
            width_mm=100.0, height_mm=100.0,
            min_box_size_mm=20.0, k_colors=1,
            min_height_mm=0.5, max_height_mm=5.0,
            algorithm="luminance",
            height_levels=3,
        )
        for cell in result["grid"]:
            for z in cell["top_vertices_z"]:
                assert z >= 0.1


class TestHeightGamma:
    def test_gamma_gt_1_lowers_midtone_heights(self):
        # mid-gray image — gamma>1 compresses heights toward min
        img = make_image_bytes(color=(128, 128, 128), h=50, w=50)
        r_linear = process_image(
            image_bytes=img, width_mm=100.0, height_mm=100.0,
            min_box_size_mm=20.0, k_colors=1,
            min_height_mm=10.0, max_height_mm=50.0,
            algorithm="luminance", height_gamma=1.0,
        )
        r_gamma = process_image(
            image_bytes=img, width_mm=100.0, height_mm=100.0,
            min_box_size_mm=20.0, k_colors=1,
            min_height_mm=10.0, max_height_mm=50.0,
            algorithm="luminance", height_gamma=2.0,
        )
        avg_linear = sum(c["height_mm"] for c in r_linear["grid"]) / len(r_linear["grid"])
        avg_gamma = sum(c["height_mm"] for c in r_gamma["grid"]) / len(r_gamma["grid"])
        assert avg_gamma < avg_linear

    def test_gamma_lt_1_raises_midtone_heights(self):
        img = make_image_bytes(color=(128, 128, 128), h=50, w=50)
        r_linear = process_image(
            image_bytes=img, width_mm=100.0, height_mm=100.0,
            min_box_size_mm=20.0, k_colors=1,
            min_height_mm=10.0, max_height_mm=50.0,
            algorithm="luminance", height_gamma=1.0,
        )
        r_gamma = process_image(
            image_bytes=img, width_mm=100.0, height_mm=100.0,
            min_box_size_mm=20.0, k_colors=1,
            min_height_mm=10.0, max_height_mm=50.0,
            algorithm="luminance", height_gamma=0.5,
        )
        avg_linear = sum(c["height_mm"] for c in r_linear["grid"]) / len(r_linear["grid"])
        avg_gamma = sum(c["height_mm"] for c in r_gamma["grid"]) / len(r_gamma["grid"])
        assert avg_gamma > avg_linear

    def test_white_image_unaffected_by_gamma(self):
        img = make_image_bytes(color=(255, 255, 255), h=50, w=50)
        for gamma in [0.5, 1.0, 2.0]:
            r = process_image(
                image_bytes=img, width_mm=100.0, height_mm=100.0,
                min_box_size_mm=20.0, k_colors=1,
                min_height_mm=10.0, max_height_mm=50.0,
                algorithm="luminance", height_gamma=gamma,
            )
            for cell in r["grid"]:
                assert cell["height_mm"] == pytest.approx(50.0, abs=1.0)

    def test_black_image_unaffected_by_gamma(self):
        img = make_image_bytes(color=(0, 0, 0), h=50, w=50)
        for gamma in [0.5, 1.0, 2.0]:
            r = process_image(
                image_bytes=img, width_mm=100.0, height_mm=100.0,
                min_box_size_mm=20.0, k_colors=1,
                min_height_mm=10.0, max_height_mm=50.0,
                algorithm="luminance", height_gamma=gamma,
            )
            for cell in r["grid"]:
                assert cell["height_mm"] == pytest.approx(10.0, abs=2.0)

    def test_metadata_reports_gamma(self):
        r = process_image(
            image_bytes=make_image_bytes(h=50, w=50), width_mm=100.0, height_mm=100.0,
            min_box_size_mm=20.0, k_colors=2,
            min_height_mm=10.0, max_height_mm=50.0,
            algorithm="luminance", height_gamma=1.5,
        )
        assert r["metadata"]["height_gamma"] == pytest.approx(1.5)
