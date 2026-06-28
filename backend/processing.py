import cv2
import numpy as np
from sklearn.cluster import KMeans
from transformers import pipeline
from PIL import Image
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely.validation import make_valid
from collections import deque

# Load pipeline globally to avoid reloading on every request (lazy init)
depth_estimator = None

def get_depth_estimator():
    global depth_estimator
    if depth_estimator is None:
        depth_estimator = pipeline("depth-estimation")
    return depth_estimator


def rgb_to_hex(r, g, b):
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

def calculate_hex_slopes(depth_map, cx, cy, min_height, max_height, R, scale_x, scale_y):
    h_img, w_img = depth_map.shape
    
    D_c = depth_map[cy, cx]
    D_left = depth_map[cy, max(0, cx-1)]
    D_right = depth_map[cy, min(w_img-1, cx+1)]
    D_up = depth_map[max(0, cy-1), cx]
    D_down = depth_map[min(h_img-1, cy+1), cx]
    
    def d_to_h(D):
        # D is 0-255, 255 is closest (highest), 0 is furthest (lowest)
        return min_height + (D / 255.0) * (max_height - min_height)
        
    H_c = d_to_h(D_c)
    
    m_x = (d_to_h(D_right) - d_to_h(D_left)) / (2 * scale_x)
    m_y = (d_to_h(D_down) - d_to_h(D_up)) / (2 * scale_y)
    
    # Flat top hexagon
    vertices_2d = [
        (R, 0),
        (R/2, np.sqrt(3)*R/2),
        (-R/2, np.sqrt(3)*R/2),
        (-R, 0),
        (-R/2, -np.sqrt(3)*R/2),
        (R/2, -np.sqrt(3)*R/2)
    ]
    
    top_vertices_z = []
    for dx, dy in vertices_2d:
        z = H_c + m_x * dx + m_y * dy
        top_vertices_z.append(round(max(0.1, z), 2))
        
    return round(H_c, 2), top_vertices_z, m_x, m_y

def get_neighbors(c, r, num_cols, num_rows):
    if c % 2 == 0:
        dirs = [(0, -1), (1, -1), (1, 0), (0, 1), (-1, 0), (-1, -1)]
    else:
        dirs = [(0, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)]
    neighbors = []
    for dc, dr in dirs:
        nc, nr = c + dc, r + dr
        if 0 <= nc < num_cols and 0 <= nr < num_rows:
            neighbors.append((nc, nr))
    return neighbors

def process_image(image_bytes, width_mm, height_mm, min_box_size_mm=15, k_colors=6, min_height_mm=10, max_height_mm=50, algorithm="depth"):
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image file")

    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    img_h, img_w = img.shape[:2]
    target_aspect = width_mm / height_mm
    img_aspect = img_w / img_h
    
    if img_aspect > target_aspect:
        new_w = int(img_h * target_aspect)
        offset = (img_w - new_w) // 2
        img = img[:, offset:offset+new_w]
    elif img_aspect < target_aspect:
        new_h = int(img_w / target_aspect)
        offset = (img_h - new_h) // 2
        img = img[offset:offset+new_h, :]

    R = min_box_size_mm / 2.0
    scale_x = 1.5 * R
    scale_y = np.sqrt(3) * R

    num_cols = max(1, int((width_mm - 0.5 * R) / scale_x))
    num_rows = max(1, int(height_mm / scale_y))

    # Resize image so each pixel is a hexagon
    small_img = cv2.resize(img, (num_cols, num_rows), interpolation=cv2.INTER_AREA)

    pixels = small_img.reshape(-1, 3)
    kmeans = KMeans(n_clusters=k_colors, random_state=42, n_init=10)
    kmeans.fit(pixels)
    quantized_colors = kmeans.cluster_centers_[kmeans.labels_]
    quantized_img = quantized_colors.reshape(num_rows, num_cols, 3)

    # Compute height and slopes based on algorithm
    if algorithm == "depth":
        estimator = get_depth_estimator()
        pil_img = Image.fromarray(img)
        depth_result = estimator(pil_img)
        depth_pil = depth_result["depth"]
        depth_array = np.array(depth_pil)
        depth_map = cv2.resize(depth_array, (num_cols, num_rows), interpolation=cv2.INTER_AREA)
    else:
        # Luminance fallback
        gray_img = cv2.cvtColor(quantized_img.astype(np.uint8), cv2.COLOR_RGB2GRAY)
        depth_map = gray_img  # 0-255 luminance

    hex_data = {}
    
    for r in range(num_rows):
        for c in range(num_cols):
            color = quantized_img[r, c]
            
            if algorithm == "depth":
                H_c, top_vertices_z, m_x, m_y = calculate_hex_slopes(
                    depth_map, c, r, min_height_mm, max_height_mm, R, scale_x, scale_y
                )
            else:
                # Luminance algorithm
                lum = depth_map[r, c]
                H_c = min_height_mm + (lum / 255.0) * (max_height_mm - min_height_mm)
                m_x = 0.0
                m_y = 0.0
                top_vertices_z = [round(H_c, 2)] * 6
                
            hex_data[(c, r)] = {
                "color": tuple(color),
                "H_c": H_c,
                "m_x": m_x,
                "m_y": m_y,
                "top_vertices_z": top_vertices_z
            }

    # Clustering
    if algorithm == "luminance":
        # No clustering for luminance — each hex is its own independent piece
        clusters = [[(c, r)] for r in range(num_rows) for c in range(num_cols)]
    else:
        visited = set()
        clusters = []

        for r in range(num_rows):
            for c in range(num_cols):
                if (c, r) not in visited:
                    cluster = []
                    queue = deque([(c, r)])
                    visited.add((c, r))

                    base_hex = hex_data[(c, r)]

                    while queue:
                        curr_c, curr_r = queue.popleft()
                        cluster.append((curr_c, curr_r))

                        curr_hex = hex_data[(curr_c, curr_r)]

                        for nc, nr in get_neighbors(curr_c, curr_r, num_cols, num_rows):
                            if (nc, nr) not in visited:
                                n_hex = hex_data[(nc, nr)]

                                # Merge condition: same color, very similar plane
                                color_match = np.allclose(curr_hex["color"], n_hex["color"], atol=2)
                                h_match = abs(base_hex["H_c"] - n_hex["H_c"]) < 1.0
                                m_x_match = abs(base_hex["m_x"] - n_hex["m_x"]) < 0.1
                                m_y_match = abs(base_hex["m_y"] - n_hex["m_y"]) < 0.1

                                if color_match and h_match and m_x_match and m_y_match:
                                    visited.add((nc, nr))
                                    queue.append((nc, nr))

                    clusters.append(cluster)

    results = []
    
    # Helper to check if an unfolded polygon net self-intersects
    def check_self_intersection(exterior_coords, top_z, T=5):
        base_pts = [np.array([p[0], p[1]]) for p in exterior_coords]
        unfolded_polys = [Polygon(base_pts)]
        n = len(base_pts)
        for i in range(n):
            next_i = (i + 1) % n
            p1 = base_pts[i]
            p2 = base_pts[next_i]
            edge_vec = p2 - p1
            edge_len = np.linalg.norm(edge_vec)
            if edge_len < 1e-5:
                continue
            u_dir = edge_vec / edge_len
            v_dir = np.array([u_dir[1], -u_dir[0]])
            
            h1 = top_z[i]
            h2 = top_z[next_i]
            w_p1 = p1
            w_p2 = p2
            w_p3 = p2 + v_dir * h2
            w_p4 = p1 + v_dir * h1
            
            wall_poly = Polygon([w_p1, w_p2, w_p3, w_p4])
            if not wall_poly.is_valid:
                wall_poly = make_valid(wall_poly)
            unfolded_polys.append(wall_poly)
            
            side_vec = w_p3 - w_p2
            side_len = np.linalg.norm(side_vec)
            if side_len > 1e-5:
                s_dir = side_vec / side_len
                tab_poly = Polygon([
                    w_p2,
                    w_p3,
                    w_p3 + u_dir * T - s_dir * (T*0.5),
                    w_p2 + u_dir * T + s_dir * (T*0.5)
                ])
                if not tab_poly.is_valid:
                    tab_poly = make_valid(tab_poly)
                unfolded_polys.append(tab_poly)
                
        # Top Cap
        V = [np.array([base_pts[i][0], base_pts[i][1], top_z[i]]) for i in range(n)]
        v01 = V[1] - V[0]
        v02 = V[2] - V[0]
        normal = np.cross(v01, v02)
        normal_len = np.linalg.norm(normal)
        if normal_len > 1e-5:
            normal = normal / normal_len
            u_3d = v01 / np.linalg.norm(v01)
            v_3d = np.cross(normal, u_3d)
            v_3d = v_3d / np.linalg.norm(v_3d)
            
            proj_2d = []
            for p in V:
                dp = p - V[0]
                u_coord = np.dot(dp, u_3d)
                v_coord = np.dot(dp, v_3d)
                proj_2d.append(np.array([u_coord, v_coord]))
                
            w0_p1 = base_pts[0]
            w0_p2 = base_pts[1]
            w0_edge = w0_p2 - w0_p1
            w0_len = np.linalg.norm(w0_edge)
            if w0_len > 1e-5:
                w0_u = w0_edge / w0_len
                w0_v = np.array([w0_u[1], -w0_u[0]])
                P0 = w0_p1 + w0_v * top_z[0]
                P1 = w0_p2 + w0_v * top_z[1]
                
                u_paper = P1 - P0
                u_paper_len = np.linalg.norm(u_paper)
                if u_paper_len > 1e-5:
                    u_paper = u_paper / u_paper_len
                    v_paper = np.array([u_paper[1], -u_paper[0]])
                    cap_pts = []
                    for uv in proj_2d:
                        pos = P0 + uv[0] * u_paper + uv[1] * v_paper
                        cap_pts.append(pos)
                    cap_poly = Polygon(cap_pts)
                    if not cap_poly.is_valid:
                        cap_poly = make_valid(cap_poly)
                    unfolded_polys.append(cap_poly)

        merged = unary_union(unfolded_polys)
        sum_area = sum(p.area for p in unfolded_polys if hasattr(p, 'area'))
        return (sum_area - merged.area) > 1.0

    def add_single_hex(c, r, idx_str):
        cx = c * scale_x
        cy = r * scale_y
        if c % 2 == 1:
            cy += scale_y / 2
        vertices_2d = [
            (cx + R, cy),
            (cx + R/2, cy + np.sqrt(3)*R/2),
            (cx - R/2, cy + np.sqrt(3)*R/2),
            (cx - R, cy),
            (cx - R/2, cy - np.sqrt(3)*R/2),
            (cx + R/2, cy - np.sqrt(3)*R/2)
        ]
        h_data = hex_data[(c, r)]
        H_c = h_data["H_c"]
        m_x = h_data["m_x"]
        m_y = h_data["m_y"]
        top_z = []
        for px, py in vertices_2d:
            dx = px - cx
            dy = py - cy
            z = H_c + m_x * dx + m_y * dy
            top_z.append(round(max(0.1, z), 2))
            
        color = h_data["color"]
        results.append({
            "id": idx_str,
            "color": rgb_to_hex(color[0], color[1], color[2]),
            "height_mm": H_c,
            "exterior_coords": vertices_2d,
            "top_vertices_z": top_z,
            "is_cluster": False,
            "box_size_mm": min_box_size_mm
        })
    
    cluster_idx = 0
    for cluster in clusters:
        if len(cluster) == 1:
            add_single_hex(cluster[0][0], cluster[0][1], f"C{cluster_idx}")
            cluster_idx += 1
            continue
            
        polys = []
        for (c, r) in cluster:
            cx = c * scale_x
            cy = r * scale_y
            if c % 2 == 1:
                cy += scale_y / 2
                
            vertices_2d = [
                (cx + R, cy),
                (cx + R/2, cy + np.sqrt(3)*R/2),
                (cx - R/2, cy + np.sqrt(3)*R/2),
                (cx - R, cy),
                (cx - R/2, cy - np.sqrt(3)*R/2),
                (cx + R/2, cy - np.sqrt(3)*R/2)
            ]
            polys.append(Polygon(vertices_2d))
            
        merged_poly = unary_union(polys)
        
        if merged_poly.geom_type == "Polygon":
            exterior_coords = list(merged_poly.exterior.coords)[:-1]
        elif merged_poly.geom_type == "MultiPolygon":
            largest_poly = max(merged_poly.geoms, key=lambda p: p.area)
            exterior_coords = list(largest_poly.exterior.coords)[:-1]
        else:
            # Unexpected geometry (GeometryCollection, etc) — fall back to individual hexes
            for i, (c, r) in enumerate(cluster):
                add_single_hex(c, r, f"C{cluster_idx}_{i}")
            cluster_idx += 1
            continue
            
        base_c, base_r = cluster[0]
        base_hex = hex_data[(base_c, base_r)]
        H_c = base_hex["H_c"]
        m_x = base_hex["m_x"]
        m_y = base_hex["m_y"]
        
        base_cx = base_c * scale_x
        base_cy = base_r * scale_y
        if base_c % 2 == 1:
            base_cy += scale_y / 2
            
        top_vertices_z = []
        for px, py in exterior_coords:
            dx = px - base_cx
            dy = py - base_cy
            z = H_c + m_x * dx + m_y * dy
            top_vertices_z.append(round(max(0.1, z), 2))
            
        # Self-intersection check
        overlaps = False
        if len(exterior_coords) > 3:
            try:
                overlaps = check_self_intersection(exterior_coords, top_vertices_z)
            except Exception as e:
                overlaps = True # Fallback if math fails
                
        if overlaps:
            # Fallback to individual hexes
            for i, (c, r) in enumerate(cluster):
                add_single_hex(c, r, f"C{cluster_idx}_{i}")
            cluster_idx += 1
        else:
            color = base_hex["color"]
            results.append({
                "id": f"C{cluster_idx}",
                "color": rgb_to_hex(color[0], color[1], color[2]),
                "height_mm": H_c,
                "exterior_coords": exterior_coords,
                "top_vertices_z": top_vertices_z,
                "is_cluster": True,
                "box_size_mm": min_box_size_mm
            })
            cluster_idx += 1

    return {
        "grid": results,
        "metadata": {
            "num_cols": num_cols,
            "num_rows": num_rows,
            "box_size_mm": min_box_size_mm,
            "R": R
        }
    }
