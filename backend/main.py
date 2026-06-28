import logging
import os
import tempfile

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from processing import process_image
from pdf_generator import generate_pdf, generate_poster
from svg_export import generate_svg

logger = logging.getLogger(__name__)

app = FastAPI(title="Origami Relief Generator API")

origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


@app.get("/api/ping")
def ping():
    return {"status": "ok", "message": "pong"}


@app.post("/api/process")
async def process_image_endpoint(
    image: UploadFile = File(...),
    width_mm: float = Form(...),
    height_mm: float = Form(...),
    min_box_size_mm: float = Form(15.0),
    k_colors: int = Form(6),
    min_height_mm: float = Form(10.0),
    max_height_mm: float = Form(50.0),
    algorithm: str = Form("depth"),
    height_levels: int = Form(0),
    height_gamma: float = Form(1.0),
    brightness: float = Form(0.0),
    contrast: float = Form(1.0),
    saturation: float = Form(1.0),
    shape: str = Form("hex"),
):
    if width_mm <= 0 or height_mm <= 0:
        raise HTTPException(status_code=400, detail="Canvas dimensions must be positive")

    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File provided is not an image")

    if shape not in ["hex", "square"]:
        raise HTTPException(status_code=400, detail="Invalid shape")
    if algorithm not in ["depth", "luminance"]:
        raise HTTPException(status_code=400, detail="Invalid algorithm")

    image_bytes = await image.read()
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image too large (max 20 MB)")

    try:
        result = process_image(
            image_bytes=image_bytes,
            width_mm=width_mm,
            height_mm=height_mm,
            min_box_size_mm=min_box_size_mm,
            k_colors=k_colors,
            min_height_mm=min_height_mm,
            max_height_mm=max_height_mm,
            algorithm=algorithm,
            height_levels=height_levels,
            height_gamma=max(0.1, min(10.0, height_gamma)),
            brightness=max(-1.0, min(1.0, brightness)),
            contrast=max(0.1, min(5.0, contrast)),
            saturation=max(0.0, min(5.0, saturation)),
            shape=shape,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.error("Image processing failed", exc_info=True)
        raise HTTPException(status_code=500, detail="Image processing failed")


@app.post("/api/pdf")
async def generate_pdf_endpoint(
    background_tasks: BackgroundTasks,
    payload: dict = Body(...),
):
    grid_data = payload.get("grid")
    metadata = payload.get("metadata")
    if not grid_data or not metadata:
        raise HTTPException(status_code=400, detail="Missing grid or metadata")

    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        output_path = tmp.name
        tmp.close()

        generate_pdf(grid_data, metadata, output_path)
        background_tasks.add_task(os.unlink, output_path)

        return FileResponse(
            path=output_path,
            filename="origami_blueprint.pdf",
            media_type="application/pdf",
        )
    except Exception:
        logger.error("PDF blueprint generation failed", exc_info=True)
        raise HTTPException(status_code=500, detail="PDF generation failed")


@app.post("/api/pdf_poster")
async def generate_pdf_poster_endpoint(
    background_tasks: BackgroundTasks,
    payload: dict = Body(...),
):
    grid_data = payload.get("grid")
    metadata = payload.get("metadata")
    if not grid_data or not metadata:
        raise HTTPException(status_code=400, detail="Missing grid or metadata")

    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        output_path = tmp.name
        tmp.close()

        generate_poster(grid_data, metadata, output_path)
        background_tasks.add_task(os.unlink, output_path)

        return FileResponse(
            path=output_path,
            filename="origami_poster.pdf",
            media_type="application/pdf",
        )
    except Exception:
        logger.error("Poster generation failed", exc_info=True)
        raise HTTPException(status_code=500, detail="Poster generation failed")


@app.post("/api/svg")
async def generate_svg_endpoint(payload: dict = Body(...)):
    grid_data = payload.get("grid")
    metadata = payload.get("metadata")
    if not grid_data or not metadata:
        raise HTTPException(status_code=400, detail="Missing grid or metadata")

    try:
        svg_content = generate_svg(grid_data, metadata)
        from fastapi.responses import Response
        return Response(
            content=svg_content,
            media_type="image/svg+xml",
            headers={"Content-Disposition": "attachment; filename=origami_cut_nets.svg"},
        )
    except Exception:
        logger.error("SVG generation failed", exc_info=True)
        raise HTTPException(status_code=500, detail="SVG generation failed")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
