import os
import math
import numpy as np
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor

def pt(x, y):
    return (x, y)

def get_piece_geometry(box_size_mm, top_vertices_z, exterior_coords=None):
    R = (box_size_mm / 2.0) * mm
    T = 5 * mm # Tab size
    
    # Base Vertices centered at 0,0
    if exterior_coords is None:
        hex2d = [
            np.array([R, 0]),
            np.array([R/2, math.sqrt(3)*R/2]),
            np.array([-R/2, math.sqrt(3)*R/2]),
            np.array([-R, 0]),
            np.array([-R/2, -math.sqrt(3)*R/2]),
            np.array([R/2, -math.sqrt(3)*R/2])
        ]
        base_pts = [p for p in hex2d]
    else:
        cx = sum(p[0] for p in exterior_coords) / len(exterior_coords)
        cy = sum(p[1] for p in exterior_coords) / len(exterior_coords)
        base_pts = [np.array([(p[0] - cx)*mm, (p[1] - cy)*mm]) for p in exterior_coords]
        
    num_sides = len(base_pts)
    
    geom = {
        "base_pts": base_pts,
        "walls": [],
        "tabs": [],
        "fold_lines": [],
        "cap_pts": None,
        "cap_fold": None
    }
    
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
        
        w_p1 = p1
        w_p2 = p2
        w_p3 = p2 + v_dir * h2
        w_p4 = p1 + v_dir * h1
        
        geom["walls"].append([w_p1, w_p2, w_p3, w_p4])
        geom["fold_lines"].append((w_p1, w_p2))
        all_points.extend([w_p3, w_p4])
        
        if i == 0:
            top_cap_edge = (w_p4, w_p3)
            
        tab_vec = u_dir
        tab_p1 = w_p2
        tab_p2 = w_p3
        tab_p3 = tab_p2 + tab_vec * T - v_dir * (T*0.5)
        tab_p4 = tab_p1 + tab_vec * T + v_dir * (T*0.5)
        
        geom["tabs"].append([tab_p1, tab_p2, tab_p3, tab_p4])
        geom["fold_lines"].append((tab_p1, tab_p2))
        all_points.extend([tab_p3, tab_p4])
        
    V = []
    for i in range(num_sides):
        V.append(np.array([base_pts[i][0], base_pts[i][1], top_vertices_z[i] * mm]))
    
    v01 = V[1] - V[0]
    v02 = V[2] - V[0]
    normal = np.cross(v01, v02)
    norm_len = np.linalg.norm(normal)
    if norm_len > 1e-6:
        normal = normal / norm_len
        u_3d = v01 / np.linalg.norm(v01)
        v_3d = np.cross(normal, u_3d)
        v_3d = v_3d / np.linalg.norm(v_3d)
        
        proj_2d = []
        for p in V:
            dp = p - V[0]
            u_coord = np.dot(dp, u_3d)
            v_coord = np.dot(dp, v_3d)
            proj_2d.append(np.array([u_coord, v_coord]))
            
        if top_cap_edge:
            P0 = top_cap_edge[0]
            P1 = top_cap_edge[1]
            u_paper = P1 - P0
            u_len = np.linalg.norm(u_paper)
            if u_len > 1e-6:
                u_paper = u_paper / u_len
                v_paper = np.array([u_paper[1], -u_paper[0]])
                
                cap_pts_paper = []
                for uv in proj_2d:
                    pos = P0 + uv[0] * u_paper + uv[1] * v_paper
                    cap_pts_paper.append(pos)
                    
                geom["cap_pts"] = cap_pts_paper
                geom["cap_fold"] = (P0, P1)
                all_points.extend(cap_pts_paper)

    min_x = min(p[0] for p in all_points)
    max_x = max(p[0] for p in all_points)
    min_y = min(p[1] for p in all_points)
    max_y = max(p[1] for p in all_points)
    
    # Bounding box: min_x, min_y, width, height
    geom["bbox"] = (min_x, min_y, max_x - min_x, max_y - min_y)
    return geom

def draw_geometry(c, x, y, geom, piece_id, color_hex):
    def translate(pts):
        return [(pt[0] + x, pt[1] + y) for pt in pts]
        
    def draw_polygon(points, fill=False, stroke=True):
        p = c.beginPath()
        p.moveTo(*points[0])
        for p_t in points[1:]:
            p.lineTo(*p_t)
        p.close()
        c.drawPath(p, fill=fill, stroke=stroke)

    c.setLineWidth(1)
    c.setFillColor(HexColor(color_hex))
    
    # Draw Base
    c.setStrokeColorRGB(0, 0, 0)
    c.setDash()
    draw_polygon(translate(geom["base_pts"]), fill=True)
    
    # Draw Walls
    for wall in geom["walls"]:
        c.setDash()
        c.setStrokeColorRGB(0, 0, 0)
        draw_polygon(translate(wall), fill=True)
        
    # Draw Tabs
    for tab in geom["tabs"]:
        c.setDash()
        c.setStrokeColorRGB(0, 0, 0)
        draw_polygon(translate(tab), fill=True)
        
    # Draw Top Cap
    if geom["cap_pts"]:
        c.setDash()
        c.setStrokeColorRGB(0, 0, 0)
        draw_polygon(translate(geom["cap_pts"]), fill=True)
        
    # Draw Fold lines
    c.setDash(3, 3)
    c.setStrokeColorRGB(0.5, 0.5, 0.5)
    for p1, p2 in geom["fold_lines"]:
        tp1 = (p1[0] + x, p1[1] + y)
        tp2 = (p2[0] + x, p2[1] + y)
        c.line(tp1[0], tp1[1], tp2[0], tp2[1])
        
    if geom["cap_fold"]:
        p1, p2 = geom["cap_fold"]
        tp1 = (p1[0] + x, p1[1] + y)
        tp2 = (p2[0] + x, p2[1] + y)
        c.line(tp1[0], tp1[1], tp2[0], tp2[1])
        
    # Label
    col_obj = HexColor(color_hex)
    c.setFillColorRGB(0, 0, 0) if (col_obj.red + col_obj.green + col_obj.blue) > 1.5 else c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(x, y - 4, str(piece_id))


def generate_pdf(grid_data, metadata, output_path="blueprint.pdf"):
    c = canvas.Canvas(output_path, pagesize=letter)
    page_width, page_height = letter
    
    page_w_mm = page_width / mm
    page_h_mm = page_height / mm
    
    margin_mm = 10
    
    pieces = []
    for item in grid_data:
        box_size = metadata.get("box_size_mm", 15)
        geom = get_piece_geometry(box_size, item["top_vertices_z"], item.get("exterior_coords"))
        geom["id"] = item["id"]
        geom["color"] = item["color"]
        # Add 5mm padding to width/height to avoid edges touching
        bbox = geom["bbox"]
        pieces.append({
            "geom": geom,
            "width": bbox[2] + 5*mm,
            "height": bbox[3] + 5*mm
        })
        
    # Sort pieces by height descending for shelf packing
    pieces.sort(key=lambda p: p["height"], reverse=True)
    
    # Shelf packing algorithm
    current_x = margin_mm * mm
    current_y = (page_h_mm - margin_mm) * mm
    row_height = 0
    
    usable_width = (page_w_mm - 2*margin_mm) * mm
    
    for piece in pieces:
        w = piece["width"]
        h = piece["height"]
        
        # If it doesn't fit on this row, move to next row
        if current_x + w > margin_mm * mm + usable_width:
            current_x = margin_mm * mm
            current_y -= row_height
            row_height = 0
            
        # If it doesn't fit on this page, new page
        if current_y - h < margin_mm * mm:
            c.showPage()
            current_x = margin_mm * mm
            current_y = (page_h_mm - margin_mm) * mm
            row_height = 0
            
        # Draw the piece
        # geom["bbox"] = (min_x, min_y, w, h)
        # We want to place it so its bounding box min_x, min_y is at current_x, current_y - h
        min_x, min_y, bw, bh = piece["geom"]["bbox"]
        draw_x = current_x - min_x + 2.5*mm
        draw_y = current_y - h - min_y + 2.5*mm
        
        draw_geometry(c, draw_x, draw_y, piece["geom"], piece["geom"]["id"], piece["geom"]["color"])
        
        current_x += w
        row_height = max(row_height, h)
        
    c.showPage()
    
    # --- Placement Guide Page ---
    c.setFillColorRGB(0,0,0)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin_mm * mm, (page_h_mm - margin_mm) * mm, "PLACEMENT GUIDE")
    
    cols = metadata["num_cols"]
    rows = metadata["num_rows"]
    R = metadata["R"]
    
    scale_x = 1.5 * R
    scale_y = math.sqrt(3) * R
    
    available_w = page_w_mm - 2*margin_mm
    available_h = page_h_mm - 3*margin_mm
    
    scale = min(available_w / (cols * scale_x + R), available_h / (rows * scale_y + scale_y))
    
    start_x = margin_mm * mm
    start_y = (page_h_mm - 2*margin_mm) * mm
    
    c.setLineWidth(1)
    
    for item in grid_data:
        pid = item["id"]
        color = item["color"]
        
        c.setFillColor(HexColor(color))
        c.setDash()
        c.setStrokeColorRGB(0, 0, 0)
        
        if "exterior_coords" in item:
            poly_pts = []
            for px, py in item["exterior_coords"]:
                hx = start_x + (px * scale * mm)
                hy = start_y - (py * scale * mm)
                poly_pts.append((hx, hy))
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
        
    c.save()
    return output_path

def generate_poster(grid_data, metadata, output_path="poster.pdf"):
    # 1:1 Scale Poster
    # The canvas dimensions are width_mm x height_mm
    # Since y increases from bottom to top in PDF, we will draw directly.
    w_mm = metadata.get("width_mm", 300)
    h_mm = metadata.get("height_mm", 300)
    
    # Custom page size
    c = canvas.Canvas(output_path, pagesize=(w_mm * mm, h_mm * mm))
    
    c.setLineWidth(1)
    
    # We will center the grid on the canvas
    # The backend grid is drawn around (0,0) with coordinates
    # Let's see the extent of exterior_coords
    min_px = float('inf')
    max_px = float('-inf')
    min_py = float('inf')
    max_py = float('-inf')
    
    for item in grid_data:
        if "exterior_coords" in item:
            for px, py in item["exterior_coords"]:
                min_px = min(min_px, px)
                max_px = max(max_px, px)
                min_py = min(min_py, py)
                max_py = max(max_py, py)
                
    if min_px == float('inf'):
        # Empty grid
        c.save()
        return output_path
        
    grid_w = max_px - min_px
    grid_h = max_py - min_py
    
    # Offset to center the grid exactly on the w_mm x h_mm poster
    offset_x = (w_mm - grid_w) / 2.0 - min_px
    offset_y = (h_mm - grid_h) / 2.0 - min_py
    
    for item in grid_data:
        pid = item["id"]
        color = item["color"]
        
        c.setFillColor(HexColor(color))
        c.setDash()
        c.setStrokeColorRGB(0, 0, 0)
        
        if "exterior_coords" in item:
            poly_pts = []
            for px, py in item["exterior_coords"]:
                # px and py are in mm. PDF y is up.
                # In backend processing, py increases downwards (row index), so we must invert Y to match original image orientation.
                # Actually, in the placement guide above: hy = start_y - (py * scale * mm)
                # So we do: hy = h_mm*mm - (py + offset_y) * mm
                hx = (px + offset_x) * mm
                hy = (h_mm - (py + offset_y)) * mm
                poly_pts.append((hx, hy))
                
            p = c.beginPath()
            p.moveTo(*poly_pts[0])
            for pt_h in poly_pts[1:]:
                p.lineTo(*pt_h)
            p.close()
            c.drawPath(p, fill=True, stroke=True)
            
            cx = sum(p[0] for p in poly_pts) / len(poly_pts)
            cy = sum(p[1] for p in poly_pts) / len(poly_pts)
            
            font_size = 12
            col_obj = HexColor(color)
            c.setFillColorRGB(0, 0, 0) if (col_obj.red + col_obj.green + col_obj.blue) > 1.5 else c.setFillColorRGB(1, 1, 1)
            c.setFont("Helvetica-Bold", font_size)
            c.drawCentredString(cx, cy - font_size/3, str(pid))
            
    c.save()
    return output_path

