# System Architecture

## Pipeline Overview

```
User Upload (image + physical dimensions in mm)
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  processing.py — process_image()                    │
│                                                     │
│  1. Aspect-ratio crop (match canvas ratio)          │
│  2. Resize image → (num_cols × num_rows)            │
│     [one pixel per hexagon]                         │
│  3. K-Means color quantization (k_colors clusters)  │
│  4. Height mapping (depth or luminance algorithm)   │
│  5. BFS clustering (depth mode only)                │
│  6. Self-intersection check on unfolded nets        │
│                                                     │
│  Output: {grid: [...], metadata: {...}}             │
└───────────────┬─────────────────────────────────────┘
                │
        ┌───────┴────────┐
        ▼                ▼
┌──────────────┐  ┌──────────────────────────────────┐
│ pdf_generator│  │  Frontend ReliefVisualizer        │
│              │  │  (React Three Fiber)              │
│ Blueprint:   │  │                                   │
│  cut nets    │  │  - Prism geometry per cell        │
│  + placement │  │  - base at y=0, top at y=z[i]    │
│  guide page  │  │  - Explode view: shift by         │
│              │  │    centroid * explodeFactor        │
│ Poster:      │  │  - Directional light from         │
│  1:1 scale   │  │    spherical sun coords           │
│  hex map     │  └──────────────────────────────────┘
└──────────────┘
```

---

## Hex Grid Layout

Flat-top hexagon, column-offset stagger:

```
R = min_box_size_mm / 2          (hex radius)
scale_x = 1.5 * R                (horizontal center-to-center distance)
scale_y = √3 * R                 (vertical center-to-center distance)
num_cols = (width_mm - 0.5*R) / scale_x
num_rows = height_mm / scale_y
```

**Center of hex at column `c`, row `r`:**
```
cx = c * scale_x
cy = r * scale_y + (scale_y/2 if c % 2 == 1 else 0)   ← stagger odd columns
```

**6 vertices (flat-top, starting right, going counter-clockwise):**
```
(cx+R,   cy        )
(cx+R/2, cy+√3R/2  )
(cx-R/2, cy+√3R/2  )
(cx-R,   cy        )
(cx-R/2, cy-√3R/2  )
(cx+R/2, cy-√3R/2  )
```

**Neighbor directions** (used for BFS clustering):
- Even columns: `(0,-1), (1,-1), (1,0), (0,1), (-1,0), (-1,-1)`
- Odd columns:  `(0,-1), (1,0),  (1,1), (0,1), (-1,1), (-1,0)`

---

## Height Mapping

### Algorithm A: Depth Estimation

```
HuggingFace pipeline("depth-estimation")
  → depth map: 0-255 (255 = closest/tallest, 0 = furthest/lowest)

H_c = min_height + (depth[r,c] / 255.0) * (max_height - min_height)

Slopes via finite difference:
  m_x = (H(right) - H(left)) / (2 * scale_x)
  m_y = (H(down)  - H(up)  ) / (2 * scale_y)

Per-vertex z:
  z_i = H_c + m_x * dx_i + m_y * dy_i   (dx,dy = vertex offset from center)
  z_i = max(0.1, z_i)                    (never negative)
```

### Algorithm B: Luminance

```
gray = mean(quantized_RGB)     ← from K-means quantized image
H_c  = min_height + (gray / 255.0) * (max_height - min_height)
slopes = 0, all 6 vertices at same z = H_c
No clustering (each hex = one piece)
```

---

## BFS Clustering (depth mode only)

Merges adjacent hexes into a single polygon piece when:
- Same quantized color (`np.allclose(c1, c2, atol=2)`)
- Similar center height (`|H1 - H2| < 1.0 mm`)
- Similar x-slope (`|m_x1 - m_x2| < 0.1`)
- Similar y-slope (`|m_y1 - m_y2| < 0.1`)

Merged hex polygon:
```
Shapely unary_union(individual hex polygons)
  → Polygon → use exterior
  → MultiPolygon → use largest polygon exterior
  → Other (GeometryCollection) → fall back to individual hexes
```

**Self-intersection check:** Unfold the 3D net (base + walls + tabs + top cap) into 2D. If `union_area < sum_area - 1mm²`, the net overlaps itself → fall back to individual hexes for that cluster.

---

## Cell Data Structure (JSON output from processing.py)

```json
{
  "id": "C0",
  "color": "#a3b2c1",
  "height_mm": 25.3,
  "exterior_coords": [[x0,y0], [x1,y1], ...],
  "top_vertices_z": [z0, z1, ...],
  "is_cluster": false,
  "box_size_mm": 15.0
}
```

- `exterior_coords`: physical mm coordinates. For single hex: 6 points. For cluster: N points (merged polygon exterior).
- `top_vertices_z`: one z-value per exterior_coords vertex (mm). For flat pieces: all equal. For sloped: varies.
- `is_cluster`: true when merged from multiple hexes (depth mode).
- Both arrays have the same length.

**Metadata:**
```json
{
  "num_cols": 20,
  "num_rows": 15,
  "box_size_mm": 15.0,
  "R": 7.5
}
```

---

## PDF Blueprint Generation

### Cut Net (get_piece_geometry)

Each piece is unfolded into a flat cut-and-fold net:

```
1. Base polygon (centered at origin, scaled to mm * reportlab.mm)
2. For each edge i → i+1:
   a. Wall: trapezoid unfolded outward
      w_p1=base[i], w_p2=base[i+1]
      w_p3=base[i+1] + outward * h2
      w_p4=base[i]   + outward * h1
   b. Tab: small trapezoid (T=5mm) appended to wall's outer edge
3. Top cap: project 3D sloped top face onto 2D plane,
   aligned to the first wall's outer edge
```

Fold lines: dashed lines along base-to-wall and wall-to-cap transitions.

### Shelf Packing

Pieces sorted by height descending, then packed left-to-right, top-to-bottom on Letter pages with 10mm margins. New page when current row would overflow.

### Coordinate Systems

```
Backend (processing.py):
  origin = top-left of grid
  x → right, y → down (row-major)

PDF (reportlab):
  origin = bottom-left of page
  x → right, y → up
  1 unit = 1 point = 1/72 inch
  mm → points: multiply by reportlab.lib.units.mm (~2.835)

Poster y-inversion:
  hy = (h_mm - (py + offset_y)) * mm
  [because backend y increases down, PDF y increases up]

3D viewer (Three.js):
  origin = center of grid (offsetX, offsetZ applied)
  x → right, y → up (height), z → toward viewer
  units = mm (direct)
```

---

## API Endpoints

| Method | Path | Input | Output |
|--------|------|-------|--------|
| GET | `/api/ping` | — | `{status, message}` |
| POST | `/api/process` | multipart: image + form fields | `{grid, metadata}` JSON |
| POST | `/api/pdf` | JSON: `{grid, metadata}` | PDF file download |
| POST | `/api/pdf_poster` | JSON: `{grid, metadata, width_mm, height_mm}` | PDF file download |

Form fields for `/api/process`:
- `width_mm`, `height_mm`: physical canvas size (mm)
- `min_box_size_mm`: hex diameter (mm), default 15
- `k_colors`: K-Means clusters, default 6
- `min_height_mm`: shortest piece height, default 10
- `max_height_mm`: tallest piece height, default 50
- `algorithm`: `"depth"` or `"luminance"`

---

## Frontend State Flow

```
File upload
  → handleFileChange: read aspect ratio, recompute height (mm), keep width (mm)

Form submit
  → handleSubmit: POST /api/process
  → setGridData(data.grid) + setMetadata(data.metadata)

gridData set
  → ReliefVisualizer renders with PolygonPrism per cell

Download PDF
  → handleDownloadPDF: POST /api/pdf with {grid, metadata}
  → blob → anchor click → download

3D controls
  → explodeFactor: shifts mesh position by centroid * factor
  → sunAzimuth/sunElevation: spherical → Cartesian for directional light position
```

---

## Performance Notes

- **Depth estimation cold start**: first depth-mode request triggers model download (~1-2GB) + load. Can take 30-120s on first run. Subsequent requests use cached `depth_estimator` global.
- **Large grids**: a 500-piece grid with clustering enabled runs Shapely geometry ops per cluster. For very large grids (1000+), consider chunking or caching cluster results.
- **PDF generation**: scales linearly with piece count. 500 pieces ≈ 1-2s.
- **3D viewer**: each piece is a separate `BufferGeometry`. For 500+ pieces, consider instanced rendering.
