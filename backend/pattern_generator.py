"""
Parametric pattern generator — produces the same {grid, metadata} format
as process_image() but without a photo input.

Patterns: waves, radial, spiral, spikes, grid
Heights are computed from math formulas, then k_colors gray shades are
assigned based on quantized height buckets.
"""

import math
import numpy as np
from typing import Literal

PatternType = Literal["waves", "radial", "spiral", "spikes", "grid"]


def _hex_center(col: int, row: int, R: float):
    x = col * 1.5 * R
    y = row * math.sqrt(3) * R + (0.5 * math.sqrt(3) * R if col % 2 else 0)
    return x, y


def _hex_vertices(cx: float, cy: float, R: float):
    return [
        [cx + R * math.cos(math.radians(a)), cy + R * math.sin(math.radians(a))]
        for a in range(0, 360, 60)
    ]


def _height_for_pattern(
    x: float, y: float,
    cx: float, cy: float,
    pattern: PatternType,
    wavelength: float,
    num_arms: int,
) -> float:
    """Return a value in [0, 1] for normalized height."""
    dx, dy = x - cx, y - cy
    r = math.sqrt(dx * dx + dy * dy)
    theta = math.atan2(dy, dx)

    if pattern == "waves":
        return 0.5 + 0.5 * math.sin(2 * math.pi * x / wavelength)
    elif pattern == "radial":
        return 0.5 + 0.5 * math.cos(2 * math.pi * r / wavelength)
    elif pattern == "spiral":
        return 0.5 + 0.5 * math.sin(2 * math.pi * r / wavelength - num_arms * theta)
    elif pattern == "spikes":
        angular = math.cos(num_arms * theta)
        radial = math.exp(-r / max(wavelength, 1.0))
        return 0.5 + 0.5 * angular * radial
    elif pattern == "grid":
        sx = 0.5 + 0.5 * math.sin(2 * math.pi * x / wavelength)
        sy = 0.5 + 0.5 * math.sin(2 * math.pi * y / wavelength)
        return sx * sy
    return 0.5


def generate_pattern(
    pattern: PatternType = "waves",
    width_mm: float = 300.0,
    height_mm: float = 300.0,
    box_size_mm: float = 15.0,
    min_height_mm: float = 5.0,
    max_height_mm: float = 50.0,
    k_colors: int = 5,
    wavelength: float = 60.0,
    num_arms: int = 6,
    height_levels: int = 0,
) -> dict:
    """
    Generate a hex grid with heights derived from a parametric pattern.

    Returns {grid: [...], metadata: {...}} matching process_image() format.
    """
    R = box_size_mm / 2.0
    num_cols = max(1, int(width_mm / (1.5 * R)))
    num_rows = max(1, int(height_mm / (math.sqrt(3) * R)))

    cx = width_mm / 2.0
    cy = height_mm / 2.0

    # Compute raw heights
    cells_raw = []
    for col in range(num_cols):
        for row in range(num_rows):
            x, y = _hex_center(col, row, R)
            norm = _height_for_pattern(x, y, cx, cy, pattern, wavelength, num_arms)
            norm = max(0.0, min(1.0, norm))
            h = min_height_mm + norm * (max_height_mm - min_height_mm)
            cells_raw.append((col, row, x, y, norm, h))

    # Quantize heights if requested
    if height_levels and height_levels >= 2:
        levels = np.linspace(min_height_mm, max_height_mm, height_levels)
        cells_raw = [
            (col, row, x, y, norm, float(levels[int(np.argmin(np.abs(levels - h)))]))
            for (col, row, x, y, norm, h) in cells_raw
        ]

    # Assign k_colors gray shades based on height quantile buckets
    heights = np.array([c[5] for c in cells_raw])
    bins = np.linspace(min_height_mm, max_height_mm + 1e-9, k_colors + 1)
    bucket_idx = np.clip(np.digitize(heights, bins) - 1, 0, k_colors - 1)

    # Gray shades: lightest = lowest, darkest = highest
    grays = [
        "#{v:02x}{v:02x}{v:02x}".format(v=int(255 - (i / max(k_colors - 1, 1)) * 200))
        for i in range(k_colors)
    ]

    grid = []
    for idx, (col, row, x, y, norm, h) in enumerate(cells_raw):
        verts = _hex_vertices(x, y, R)
        color = grays[bucket_idx[idx]]
        grid.append({
            "id": f"P{idx}",
            "color": color,
            "height_mm": round(h, 3),
            "exterior_coords": [[round(v[0], 4), round(v[1], 4)] for v in verts],
            "top_vertices_z": [round(h, 3)] * 6,
            "is_cluster": False,
            "box_size_mm": box_size_mm,
            "grid_pos": {"row": row, "col": col},
        })

    metadata = {
        "num_cols": num_cols,
        "num_rows": num_rows,
        "box_size_mm": box_size_mm,
        "R": R,
        "width_mm": width_mm,
        "height_mm": height_mm,
        "min_height_mm": min_height_mm,
        "max_height_mm": max_height_mm,
        "height_levels": height_levels,
        "k_colors": k_colors,
        "shape": "hex",
        "pattern": pattern,
        "wavelength": wavelength,
        "num_arms": num_arms,
    }

    return {"grid": grid, "metadata": metadata}
