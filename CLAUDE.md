# Origami Relief Generator — Agent Reference

Full-stack app: upload photo → hexagonal 3D relief → printable PDF blueprints for physical origami art construction.

## Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 16, React 19, Tailwind CSS 4, React Three Fiber, TypeScript |
| Backend | FastAPI (Python 3.12), uvicorn |
| Image processing | OpenCV, NumPy, scikit-learn (K-Means), HuggingFace transformers, Pillow |
| Geometry | Shapely |
| PDF | ReportLab |

> **Next.js 16 note**: APIs and conventions may differ from training data. Read `node_modules/next/dist/docs/` before writing frontend code. See `frontend/AGENTS.md`.

## Running Locally

```bash
# Backend
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm run dev
# http://localhost:3000
```

## Key Files

```
backend/
  main.py           FastAPI app — /api/process, /api/pdf, /api/pdf_poster
  processing.py     Core pipeline: image → hex grid → clusters → JSON
  pdf_generator.py  PDF blueprint (cut nets) + 1:1 poster
  test_processing.py
  test_api.py
  test_pdf_generator.py
  requirements.txt

frontend/
  src/app/page.tsx                  Main UI — upload, controls, download buttons
  src/components/ReliefVisualizer.tsx  React Three Fiber 3D viewer
  tests/e2e/                        Playwright browser tests
  playwright.config.ts
  .env.local.example
```

## Architecture

See `ARCHITECTURE.md` for full pipeline and data structure reference.

## Critical Rules — Do Not Violate

1. **All coordinates in `exterior_coords` and `top_vertices_z` are in mm.** Never mix with pixels.
2. **PDF path must use `tempfile.NamedTemporaryFile`** — never a fixed filename. Concurrent requests corrupt fixed files.
3. **Frontend API URL is `process.env.NEXT_PUBLIC_API_URL`** (falls back to `http://localhost:8000`). Never hardcode.
4. **Tests must use `algorithm="luminance"`** — depth algorithm downloads a HuggingFace model. Use luminance for unit tests.
5. **When image is uploaded, only update `aspectRatio` and recompute height from current width (mm).** Do not set width/height from image pixel dimensions.
6. **Depth estimator loads lazily** (`get_depth_estimator()` in processing.py). First depth-mode request is slow (model download + load). This is expected.

## CORS

Backend CORS origins are controlled by the `ALLOWED_ORIGINS` env var (comma-separated). Default: `http://localhost:3000`.

## Testing

```bash
# Backend unit + API tests
cd backend && pytest -v

# Frontend E2E (Playwright)
cd frontend && npx playwright test

# Install Playwright browsers (first time)
cd frontend && npx playwright install chromium
```

## Feature Roadmap

See `TASKS.md` for planned features in priority order.

## Known Completed Bug Fixes

- `ReliefVisualizer.tsx`: early `return geo` (BufferGeometry) in useMemo caused crash on degenerate cells — fixed to return `{geometry, meshPosition}`.
- `pdf_generator.py`: `NameError` on `rect_x`/`rect_y` when item missing `exterior_coords` — label drawing moved inside the guard block.
- `page.tsx`: pixel dimensions from uploaded image were overwriting physical mm fields — fixed to only update aspect ratio.
- `main.py`: `content_type` None crash — added None guard before `.startswith()`.
- `main.py`: concurrent PDF requests overwrote each other — fixed with tempfile + BackgroundTasks cleanup.
- `processing.py`: luminance BFS was O(n) wasteful — replaced with direct list comprehension.
- `processing.py`: GeometryCollection from `unary_union` silently dropped cluster — added fallback to individual hexes.
