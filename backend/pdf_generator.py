import math
from collections import defaultdict

import numpy as np
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def get_piece_geometry(box_size_mm, top_vertices_z, exterior_coords=None):
    R = (box_size_mm / 2.0) * mm
    T = 5 * mm

    if exterior_coords is None:
        hex2d = [
            np.array([R, 0]),
            np.array([R / 2, math.sqrt(3) * R / 2]),
            np.array([-R / 2, math.sqrt(3) * R / 2]),
            np.array([-R, 0]),
            np.array([-R / 2, -math.sqrt(3) * R / 2]),
            np.array([R / 2, -math.sqrt(3) * R / 2]),
        ]
        base_pts = list(hex2d)
    else:
        cx = sum(p[0] for p in exterior_coords) / len(exterior_coords)
        cy = sum(p[1] for p in exterior_coords) / len(exterior_coords)
        base_pts = [np.array([(p[0] - cx) * mm, (p[1] - cy) * mm]) for p in exterior_coords]

    num_sides = len(base_pts)
    geom = {"base_pts": base_pts, "walls": [], "tabs": [], "fold_lines": [], "cap_pts": None, "cap_fold": None}
    all_points = list(base_pts)
    top_cap_edge = None

    for i in range(num_sides):
        next_i = (i + 1) % num_sides
        p1 = base_pts[i]
        p2 = base_pts[next_i]
        edge_vec = p2 - p1
        edge_len = np.linalg.norm(edge_vec)
        if edge_len < 1e-6:
            continue
        u_dir = edge_vec / edge_len
        v_dir = np.array([u_dir[1], -u_dir[0]])

        h1 = top_vertices_z[i] * mm
        h2 = top_vertices_z[next_i] * mm
        w_p1, w_p2 = p1, p2
        w_p3 = p2 + v_dir * h2
        w_p4 = p1 + v_dir * h1

        geom["walls"].append([w_p1, w_p2, w_p3, w_p4])
        geom["fold_lines"].append((w_p1, w_p2))
        all_points.extend([w_p3, w_p4])

        if i == 0:
            top_cap_edge = (w_p4, w_p3)

        tab_p1, tab_p2 = w_p2, w_p3
        tab_p3 = tab_p2 + u_dir * T - v_dir * (T * 0.5)
        tab_p4 = tab_p1 + u_dir * T + v_dir * (T * 0.5)
        geom["tabs"].append([tab_p1, tab_p2, tab_p3, tab_p4])
        geom["fold_lines"].append((tab_p1, tab_p2))
        all_points.extend([tab_p3, tab_p4])

    V = [np.array([base_pts[i][0], base_pts[i][1], top_vertices_z[i] * mm]) for i in range(num_sides)]
    v01 = V[1] - V[0]
    v02 = V[2] - V[0]
    normal = np.cross(v01, v02)
    norm_len = np.linalg.norm(normal)
    if norm_len > 1e-6:
        normal /= norm_len
        u_3d = v01 / np.linalg.norm(v01)
        v_3d = np.cross(normal, u_3d)
        v_3d /= np.linalg.norm(v_3d)
        proj_2d = [np.array([np.dot(p - V[0], u_3d), np.dot(p - V[0], v_3d)]) for p in V]

        if top_cap_edge:
            P0, P1 = top_cap_edge
            u_paper = P1 - P0
            u_len = np.linalg.norm(u_paper)
            if u_len > 1e-6:
                u_paper /= u_len
                v_paper = np.array([u_paper[1], -u_paper[0]])
                cap_pts = [P0 + uv[0] * u_paper + uv[1] * v_paper for uv in proj_2d]
                geom["cap_pts"] = cap_pts
                geom["cap_fold"] = (P0, P1)
                all_points.extend(cap_pts)

    min_x = min(p[0] for p in all_points)
    max_x = max(p[0] for p in all_points)
    min_y = min(p[1] for p in all_points)
    max_y = max(p[1] for p in all_points)
    geom["bbox"] = (min_x, min_y, max_x - min_x, max_y - min_y)
    return geom


def draw_geometry(c, x, y, geom, piece_id, color_hex, grid_pos=None):
    def translate(pts):
        return [(p[0] + x, p[1] + y) for p in pts]

    def draw_polygon(points, fill=False, stroke=True):
        path = c.beginPath()
        path.moveTo(*points[0])
        for pt in points[1:]:
            path.lineTo(*pt)
        path.close()
        c.drawPath(path, fill=fill, stroke=stroke)

    c.setLineWidth(1)
    c.setFillColor(HexColor(color_hex))
    c.setStrokeColorRGB(0, 0, 0)
    c.setDash()

    draw_polygon(translate(geom["base_pts"]), fill=True)
    for wall in geom["walls"]:
        draw_polygon(translate(wall), fill=True)
    for tab in geom["tabs"]:
        draw_polygon(translate(tab), fill=True)
    if geom["cap_pts"]:
        draw_polygon(translate(geom["cap_pts"]), fill=True)

    c.setDash(3, 3)
    c.setStrokeColorRGB(0.5, 0.5, 0.5)
    for p1, p2 in geom["fold_lines"]:
        c.line(p1[0] + x, p1[1] + y, p2[0] + x, p2[1] + y)
    if geom["cap_fold"]:
        p1, p2 = geom["cap_fold"]
        c.line(p1[0] + x, p1[1] + y, p2[0] + x, p2[1] + y)

    col_obj = HexColor(color_hex)
    is_light = (col_obj.red + col_obj.green + col_obj.blue) > 1.5
    c.setFillColorRGB(0, 0, 0) if is_light else c.setFillColorRGB(1, 1, 1)
    c.setDash()

    # Piece ID
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(x, y - 3, str(piece_id))

    # Assembly grid position (Task 3)
    if grid_pos:
        c.setFont("Helvetica", 7)
        label = f"R{grid_pos['row']:02d}-C{grid_pos['col']:02d}"
        c.drawCentredString(x, y - 3 - 8, label)


def _draw_bom_page(c, grid_data, metadata, page_width, page_height, margin_mm):
    c.showPage()
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin_mm * mm, page_height - margin_mm * mm, "BILL OF MATERIALS")

    height_levels = metadata.get("height_levels", 0)
    min_h = metadata.get("min_height_mm")
    max_h = metadata.get("max_height_mm")

    groups: dict = defaultdict(int)
    for item in grid_data:
        h_key = round(item["height_mm"], 1)
        groups[(item["color"], h_key)] += 1

    rows_bom = sorted(groups.items(), key=lambda x: (x[0][0], x[0][1]))

    col_x = [
        margin_mm * mm,
        margin_mm * mm + 20 * mm,
        margin_mm * mm + 55 * mm,
        margin_mm * mm + 85 * mm,
    ]
    y = page_height - (margin_mm + 15) * mm

    c.setFont("Helvetica-Bold", 10)
    for label, x in zip(["Swatch", "Color", "Height (mm)", "Count"], col_x):
        c.drawString(x, y, label)
    y -= 6 * mm
    c.setLineWidth(0.5)
    c.line(col_x[0], y + 3 * mm, page_width - margin_mm * mm, y + 3 * mm)

    c.setFont("Helvetica", 9)
    swatch_size = 5 * mm
    total_pieces = 0

    for (color_hex, h_key), count in rows_bom:
        if y < margin_mm * mm + 20 * mm:
            c.showPage()
            y = page_height - margin_mm * mm
            c.setFont("Helvetica", 9)

        c.setFillColor(HexColor(color_hex))
        c.setStrokeColorRGB(0, 0, 0)
        c.rect(col_x[0], y, swatch_size, swatch_size, fill=1, stroke=1)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(col_x[1], y + 1 * mm, color_hex)
        c.drawString(col_x[2], y + 1 * mm, f"{h_key:.1f}")
        c.drawString(col_x[3], y + 1 * mm, str(count))
        total_pieces += count
        y -= 7 * mm

    y -= 4 * mm
    c.setLineWidth(0.5)
    c.line(col_x[0], y + 5 * mm, page_width - margin_mm * mm, y + 5 * mm)
    c.setFont("Helvetica-Bold", 10)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(col_x[0], y, "TOTAL PIECES")
    c.drawString(col_x[3], y, str(total_pieces))

    y -= 10 * mm
    c.setFont("Helvetica", 9)

    box_mm = metadata.get("box_size_mm", 15)
    pieces_per_sheet = max(1, int((180 / (box_mm * 3)) * (270 / (box_mm * 3))))
    sheets = math.ceil(total_pieces / pieces_per_sheet)
    c.drawString(col_x[0], y, f"Estimated paper sheets (A4, rough): ~{sheets}")

    if height_levels and height_levels >= 2 and min_h is not None and max_h is not None:
        levels = np.linspace(min_h, max_h, height_levels)
        y -= 6 * mm
        level_str = "  |  ".join(f"L{i+1}: {v:.1f}mm" for i, v in enumerate(levels))
        c.drawString(col_x[0], y, f"Height levels: {level_str}")


def generate_pdf(grid_data, metadata, output_path="blueprint.pdf"):
    c = canvas.Canvas(output_path, pagesize=letter)
    page_width, page_height = letter
    page_w_mm = page_width / mm
    page_h_mm = page_height / mm
    margin_mm = 10

    # --- Calibration square: top-right corner of page 1 (Task 4) ---
    cal_size = 50 * mm
    cal_x = page_width - margin_mm * mm - cal_size
    cal_y = page_height - margin_mm * mm - cal_size
    c.setStrokeColorRGB(0, 0, 0)
    c.setFillColorRGB(1, 1, 1)
    c.setLineWidth(1)
    c.rect(cal_x, cal_y, cal_size, cal_size, fill=1, stroke=1)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 7)
    c.drawCentredString(cal_x + cal_size / 2, cal_y - 5 * mm, "50 × 50 mm — verify scale before cutting")

    # Build sorted piece list (batch cut grouping: sort by color then height)
    box_size = metadata.get("box_size_mm", 15)
    pieces = []
    for item in grid_data:
        geom = get_piece_geometry(box_size, item["top_vertices_z"], item.get("exterior_coords"))
        geom["id"] = item["id"]
        geom["color"] = item["color"]
        geom["grid_pos"] = item.get("grid_pos")
        bbox = geom["bbox"]
        pieces.append({
            "geom": geom,
            "width": bbox[2] + 5 * mm,
            "height": bbox[3] + 5 * mm,
            "color": item["color"],
            "height_mm": item["height_mm"],
        })

    # Sort by (color, height) so identical pieces are grouped together (Task 6)
    pieces.sort(key=lambda p: (p["color"], p["height_mm"]))

    usable_width = (page_w_mm - 2 * margin_mm) * mm
    current_x = margin_mm * mm
    current_y = (page_h_mm - margin_mm) * mm
    row_height = 0

    for piece in pieces:
        w = piece["width"]
        h = piece["height"]

        if current_x + w > margin_mm * mm + usable_width:
            current_x = margin_mm * mm
            current_y -= row_height
            row_height = 0

        if current_y - h < margin_mm * mm:
            c.showPage()
            current_x = margin_mm * mm
            current_y = (page_h_mm - margin_mm) * mm
            row_height = 0

        min_x, min_y, _bw, _bh = piece["geom"]["bbox"]
        draw_x = current_x - min_x + 2.5 * mm
        draw_y = current_y - h - min_y + 2.5 * mm
        draw_geometry(c, draw_x, draw_y, piece["geom"], piece["geom"]["id"], piece["geom"]["color"], piece["geom"]["grid_pos"])

        current_x += w
        row_height = max(row_height, h)

    # --- Placement Guide Page ---
    c.showPage()
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin_mm * mm, (page_h_mm - margin_mm) * mm, "PLACEMENT GUIDE")

    cols = metadata["num_cols"]
    rows = metadata["num_rows"]
    R = metadata["R"]
    scale_x = 1.5 * R
    scale_y = math.sqrt(3) * R
    available_w = page_w_mm - 2 * margin_mm
    available_h = page_h_mm - 3 * margin_mm
    scale = min(available_w / (cols * scale_x + R), available_h / (rows * scale_y + scale_y))
    start_x = margin_mm * mm
    start_y = (page_h_mm - 2 * margin_mm) * mm
    c.setLineWidth(1)

    for item in grid_data:
        pid = item["id"]
        color = item["color"]
        c.setFillColor(HexColor(color))
        c.setDash()
        c.setStrokeColorRGB(0, 0, 0)

        if "exterior_coords" in item:
            poly_pts = [(start_x + px * scale * mm, start_y - py * scale * mm) for px, py in item["exterior_coords"]]
            path = c.beginPath()
            path.moveTo(*poly_pts[0])
            for pt in poly_pts[1:]:
                path.lineTo(*pt)
            path.close()
            c.drawPath(path, fill=True, stroke=True)

            cx = sum(pt[0] for pt in poly_pts) / len(poly_pts)
            cy = sum(pt[1] for pt in poly_pts) / len(poly_pts)
            font_size = max(4, min(10, R * scale * 1.5))
            col_obj = HexColor(color)
            c.setFillColorRGB(0, 0, 0) if (col_obj.red + col_obj.green + col_obj.blue) > 1.5 else c.setFillColorRGB(1, 1, 1)
            c.setFont("Helvetica", font_size)
            c.drawCentredString(cx, cy - font_size / 3, pid)

    # --- Bill of Materials Page (Task 2) ---
    _draw_bom_page(c, grid_data, metadata, page_width, page_height, margin_mm)

    c.save()
    return output_path


def generate_poster(grid_data, metadata, output_path="poster.pdf"):
    w_mm = metadata.get("width_mm", 300)
    h_mm = metadata.get("height_mm", 300)
    c = canvas.Canvas(output_path, pagesize=(w_mm * mm, h_mm * mm))
    c.setLineWidth(1)

    min_px = min((px for item in grid_data if "exterior_coords" in item for px, _ in item["exterior_coords"]), default=None)
    max_px = max((px for item in grid_data if "exterior_coords" in item for px, _ in item["exterior_coords"]), default=None)
    min_py = min((py for item in grid_data if "exterior_coords" in item for _, py in item["exterior_coords"]), default=None)
    max_py = max((py for item in grid_data if "exterior_coords" in item for _, py in item["exterior_coords"]), default=None)

    if min_px is None:
        c.save()
        return output_path

    grid_w = max_px - min_px
    grid_h = max_py - min_py
    offset_x = (w_mm - grid_w) / 2.0 - min_px
    offset_y = (h_mm - grid_h) / 2.0 - min_py

    for item in grid_data:
        pid = item["id"]
        color = item["color"]
        c.setFillColor(HexColor(color))
        c.setDash()
        c.setStrokeColorRGB(0, 0, 0)

        if "exterior_coords" in item:
            poly_pts = [((px + offset_x) * mm, (h_mm - (py + offset_y)) * mm) for px, py in item["exterior_coords"]]
            path = c.beginPath()
            path.moveTo(*poly_pts[0])
            for pt in poly_pts[1:]:
                path.lineTo(*pt)
            path.close()
            c.drawPath(path, fill=True, stroke=True)

            cx = sum(pt[0] for pt in poly_pts) / len(poly_pts)
            cy = sum(pt[1] for pt in poly_pts) / len(poly_pts)
            font_size = 12
            col_obj = HexColor(color)
            c.setFillColorRGB(0, 0, 0) if (col_obj.red + col_obj.green + col_obj.blue) > 1.5 else c.setFillColorRGB(1, 1, 1)
            c.setFont("Helvetica-Bold", font_size)
            c.drawCentredString(cx, cy - font_size / 3, str(pid))

    c.save()
    return output_path


def generate_backboard(grid_data, metadata, output_path="backboard.pdf"):
    """
    Generate a 1:1 scale backboard gluing guide.
    Prints each hex/square cell as an outline with its piece ID and grid pos,
    for use as a physical template when assembling the relief.
    """
    w_mm = metadata.get("width_mm", metadata.get("num_cols", 10) * metadata.get("box_size_mm", 15))
    h_mm = metadata.get("height_mm", metadata.get("num_rows", 10) * metadata.get("box_size_mm", 15))
    c = canvas.Canvas(output_path, pagesize=(w_mm * mm, h_mm * mm))
    c.setLineWidth(0.3)

    if not grid_data:
        c.save()
        return output_path

    min_px = min(px for item in grid_data for px, _ in item.get("exterior_coords", [[0, 0]]))
    max_px = max(px for item in grid_data for px, _ in item.get("exterior_coords", [[0, 0]]))
    min_py = min(py for item in grid_data for _, py in item.get("exterior_coords", [[0, 0]]))
    max_py = max(py for item in grid_data for _, py in item.get("exterior_coords", [[0, 0]]))

    grid_w = max_px - min_px
    grid_h = max_py - min_py
    offset_x = (w_mm - grid_w) / 2.0 - min_px
    offset_y = (h_mm - grid_h) / 2.0 - min_py

    for item in grid_data:
        coords = item.get("exterior_coords", [])
        if not coords:
            continue

        color = item.get("color", "#cccccc")
        poly_pts = [
            ((px + offset_x) * mm, (h_mm - (py + offset_y)) * mm)
            for px, py in coords
        ]

        c.setFillColor(HexColor(color))
        c.setFillAlpha(0.15)
        c.setStrokeColorRGB(0, 0, 0)
        c.setDash()

        path = c.beginPath()
        path.moveTo(*poly_pts[0])
        for pt in poly_pts[1:]:
            path.lineTo(*pt)
        path.close()
        c.drawPath(path, fill=True, stroke=True)

        c.setFillAlpha(1.0)
        cx = sum(pt[0] for pt in poly_pts) / len(poly_pts)
        cy = sum(pt[1] for pt in poly_pts) / len(poly_pts)

        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 5)
        c.drawCentredString(cx, cy + 2, item["id"])

        gp = item.get("grid_pos")
        if gp:
            c.setFont("Helvetica", 4)
            c.drawCentredString(cx, cy - 3, f"R{gp['row']:02d}-C{gp['col']:02d}")

    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1)
    c.rect(2 * mm, 2 * mm, (w_mm - 4) * mm, (h_mm - 4) * mm, fill=0, stroke=1)
    c.setFont("Helvetica-Bold", 8)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(4 * mm, (h_mm - 8) * mm, "BACKBOARD ASSEMBLY GUIDE — 1:1 SCALE")
    c.setFont("Helvetica", 6)
    c.drawString(4 * mm, (h_mm - 14) * mm, f"{len(grid_data)} pieces | {w_mm:.0f}mm x {h_mm:.0f}mm | align piece IDs with labels")

    c.save()
    return output_path


def generate_tiled_pdf(grid_data, metadata, output_path="tiled.pdf", tile_width_mm=210, tile_height_mm=297):
    """
    Split grid into spatial tiles. One PDF page group per tile, containing cut nets
    for pieces whose centroid falls in that tile. Tile coordinates printed in header.
    """
    if not grid_data:
        c2 = canvas.Canvas(output_path, pagesize=letter)
        c2.save()
        return output_path

    margin_mm = 10
    box_size = metadata.get("box_size_mm", 15)

    tile_map: dict = {}
    for item in grid_data:
        coords = item.get("exterior_coords", [])
        if not coords:
            continue
        cxp = sum(p[0] for p in coords) / len(coords)
        cyp = sum(p[1] for p in coords) / len(coords)
        tx = int(cxp // tile_width_mm)
        ty = int(cyp // tile_height_mm)
        key = (tx, ty)
        tile_map.setdefault(key, []).append(item)

    if not tile_map:
        c2 = canvas.Canvas(output_path, pagesize=letter)
        c2.save()
        return output_path

    page_w = tile_width_mm * mm
    page_h = tile_height_mm * mm
    c2 = canvas.Canvas(output_path, pagesize=(page_w, page_h))

    for tile_key in sorted(tile_map.keys()):
        tx, ty = tile_key
        items = tile_map[tile_key]

        c2.setFillColorRGB(0, 0, 0)
        c2.setFont("Helvetica-Bold", 9)
        c2.drawString(margin_mm * mm, (tile_height_mm - margin_mm) * mm,
                      f"TILE ({tx},{ty}) — Origami Relief — {len(items)} pieces")
        c2.setFont("Helvetica", 7)
        c2.drawString(margin_mm * mm, (tile_height_mm - margin_mm - 5) * mm,
                      f"Region: x={tx*tile_width_mm:.0f}–{(tx+1)*tile_width_mm:.0f}mm, "
                      f"y={ty*tile_height_mm:.0f}–{(ty+1)*tile_height_mm:.0f}mm")

        usable_w = (tile_width_mm - 2 * margin_mm) * mm
        cur_x = margin_mm * mm
        cur_y = (tile_height_mm - margin_mm - 15) * mm
        row_h = 0

        for item in sorted(items, key=lambda p: (p["color"], p["height_mm"])):
            geom = get_piece_geometry(box_size, item["top_vertices_z"], item.get("exterior_coords"))
            geom["id"] = item["id"]
            geom["color"] = item["color"]
            geom["grid_pos"] = item.get("grid_pos")
            bbox = geom["bbox"]
            w = bbox[2] + 5 * mm
            h = bbox[3] + 5 * mm

            if cur_x + w > margin_mm * mm + usable_w:
                cur_x = margin_mm * mm
                cur_y -= row_h
                row_h = 0

            if cur_y - h < margin_mm * mm:
                c2.showPage()
                c2.setFillColorRGB(0, 0, 0)
                c2.setFont("Helvetica-Bold", 9)
                c2.drawString(margin_mm * mm, (tile_height_mm - margin_mm) * mm,
                              f"TILE ({tx},{ty}) continued")
                cur_x = margin_mm * mm
                cur_y = (tile_height_mm - margin_mm - 15) * mm
                row_h = 0

            min_x, min_y, _bw, _bh = bbox
            draw_geometry(c2, cur_x - min_x + 2.5 * mm, cur_y - h - min_y + 2.5 * mm,
                          geom, geom["id"], geom["color"], geom["grid_pos"])
            cur_x += w
            row_h = max(row_h, h)

        c2.showPage()

    c2.save()
    return output_path
