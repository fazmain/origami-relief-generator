"""
SVG export for laser cutting / vinyl plotters.

Each cell is rendered as:
  - Cut line: exterior polygon outline
  - Score lines: fold lines (dashed)
  - All dimensions in real mm (1 SVG user unit = 1mm)
"""

import math
import numpy as np


def _hex_vertices(cx: float, cy: float, R: float):
    return [
        (cx + R, cy),
        (cx + R / 2, cy + math.sqrt(3) * R / 2),
        (cx - R / 2, cy + math.sqrt(3) * R / 2),
        (cx - R, cy),
        (cx - R / 2, cy - math.sqrt(3) * R / 2),
        (cx + R / 2, cy - math.sqrt(3) * R / 2),
    ]


def _poly_path(pts) -> str:
    if not pts:
        return ""
    coords = " ".join(f"{x:.3f},{y:.3f}" for x, y in pts)
    return f"M {coords} Z"


def _unfolded_paths(exterior_coords, top_vertices_z, T=5.0, taper=0.0):
    """
    Compute 2D unfolded net paths for one piece.
    Returns (cut_paths, score_paths) — each a list of SVG 'd' strings.
    Taper (0-1) scales the top polygon toward centroid, producing trapezoidal walls.
    """
    base = [np.array(p, dtype=float) for p in exterior_coords]
    n = len(base)
    s = max(0.0, min(1.0, 1.0 - taper))

    # Centroid for taper scaling
    cx = sum(p[0] for p in base) / n
    cy = sum(p[1] for p in base) / n
    centroid = np.array([cx, cy])

    cut_paths = [_poly_path(base)]
    score_paths = []

    for i in range(n):
        next_i = (i + 1) % n
        p1, p2 = base[i], base[next_i]
        edge = p2 - p1
        edge_len = np.linalg.norm(edge)
        if edge_len < 1e-6:
            continue
        u = edge / edge_len
        v = np.array([u[1], -u[0]])

        h1 = float(top_vertices_z[i])
        h2 = float(top_vertices_z[next_i])

        if taper < 1e-6:
            w3 = p2 + v * h2
            w4 = p1 + v * h1
        else:
            # q_i = centroid + s*(p_i - centroid) = s*p_i + (1-s)*centroid
            # Δq1 from p1 in 3D: ((s-1)*(p1-centroid), h1)
            dq1 = (s - 1.0) * (p1 - centroid)
            u_q1 = float(np.dot(dq1, u))
            v_q1 = math.sqrt(max(0.0, np.dot(dq1, dq1) + h1 * h1 - u_q1 * u_q1))
            # Δq2 from p1: (s*p2 + (1-s)*centroid - p1, h2)
            dq2 = s * p2 + (1.0 - s) * centroid - p1
            u_q2 = float(np.dot(dq2, u))
            v_q2 = math.sqrt(max(0.0, np.dot(dq2, dq2) + h2 * h2 - u_q2 * u_q2))
            w4 = p1 + u_q1 * u + v_q1 * v
            w3 = p1 + u_q2 * u + v_q2 * v

        wall_pts = [p1, p2, w3, w4]
        cut_paths.append(_poly_path(wall_pts))
        score_paths.append(f"M {p1[0]:.3f},{p1[1]:.3f} L {p2[0]:.3f},{p2[1]:.3f}")

        t3 = w3 + u * T - v * (T * 0.5)
        t4 = w4 + u * T + v * (T * 0.5)
        cut_paths.append(_poly_path([w4, w3, t3, t4]))
        score_paths.append(f"M {w4[0]:.3f},{w4[1]:.3f} L {w3[0]:.3f},{w3[1]:.3f}")

    return cut_paths, score_paths


def generate_svg(grid_data: list, metadata: dict, taper: float = 0.0) -> str:
    """
    Generate a flat-layout SVG of all cut nets, arranged in rows.
    1 SVG unit = 1 mm. Suitable for laser cutters.
    """
    box_mm = metadata.get("box_size_mm", 15)
    R = box_mm / 2.0

    # Estimate per-piece bounding box width/height (conservative)
    max_height_mm = metadata.get("max_height_mm", 50)
    piece_w = box_mm * 2 + max_height_mm * 2 + 10  # rough estimate with tabs
    piece_h = box_mm * 2 + max_height_mm * 2 + 10

    COLS_PER_ROW = 5
    MARGIN = 5.0
    gap = MARGIN

    svg_pieces = []
    for idx, item in enumerate(grid_data):
        col_i = idx % COLS_PER_ROW
        row_i = idx // COLS_PER_ROW
        offset_x = MARGIN + col_i * (piece_w + gap)
        offset_y = MARGIN + row_i * (piece_h + gap)

        coords = item.get("exterior_coords", [])
        top_z = item.get("top_vertices_z", [])
        color = item.get("color", "#cccccc")

        if not coords or len(coords) < 3:
            continue

        # Translate coords to local canvas (center piece)
        cx = sum(p[0] for p in coords) / len(coords)
        cy = sum(p[1] for p in coords) / len(coords)
        local = [(p[0] - cx + offset_x + piece_w / 2, p[1] - cy + offset_y + piece_h / 2) for p in coords]

        cut_paths, score_paths = _unfolded_paths(
            [(p[0] - cx + piece_w / 2, p[1] - cy + piece_h / 2) for p in coords],
            top_z,
            taper=taper,
        )

        # Shift all paths to canvas position
        def shift_d(d: str) -> str:
            import re
            def replace(m):
                x, y = float(m.group(1)), float(m.group(2))
                return f"{x + offset_x:.3f},{y + offset_y:.3f}"
            return re.sub(r"([-\d.]+),([-\d.]+)", replace, d)

        piece_svg = f'<g id="{item["id"]}">\n'
        for d in cut_paths:
            piece_svg += f'  <path d="{shift_d(d)}" fill="{color}" fill-opacity="0.3" stroke="black" stroke-width="0.2"/>\n'
        for d in score_paths:
            piece_svg += f'  <path d="{shift_d(d)}" fill="none" stroke="#555555" stroke-width="0.1" stroke-dasharray="1,1"/>\n'
        piece_svg += f'  <text x="{offset_x + piece_w/2:.1f}" y="{offset_y + piece_h/2:.1f}" font-size="3" text-anchor="middle" fill="black">{item["id"]}</text>\n'
        if item.get("grid_pos"):
            gp = item["grid_pos"]
            piece_svg += f'  <text x="{offset_x + piece_w/2:.1f}" y="{offset_y + piece_h/2 + 4:.1f}" font-size="2.5" text-anchor="middle" fill="#444">R{gp["row"]:02d}-C{gp["col"]:02d}</text>\n'
        piece_svg += "</g>\n"
        svg_pieces.append(piece_svg)

    total_rows = math.ceil(len(grid_data) / COLS_PER_ROW) if grid_data else 1
    total_w = MARGIN * 2 + COLS_PER_ROW * (piece_w + gap)
    total_h = MARGIN * 2 + total_rows * (piece_h + gap)

    svg = (
        f'<?xml version="1.0" encoding="utf-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{total_w:.1f}mm" height="{total_h:.1f}mm" '
        f'viewBox="0 0 {total_w:.3f} {total_h:.3f}" '
        f'style="background:white">\n'
        f'<title>Origami Relief — Cut Net SVG</title>\n'
    )
    svg += "".join(svg_pieces)
    svg += "</svg>\n"
    return svg
