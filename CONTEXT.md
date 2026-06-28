# Project Context: Origami Relief Generator

## What are we building?
A full-stack web application that translates 2D images into 3D geometric grids (hexagons or square prisms) which can be physically assembled using origami.

## Core Features
1. **Upload & Configuration**: Users upload a 2D reference photograph and set the physical canvas dimensions (e.g., 24x36 inches).
2. **Processing Engine**: The system divides the canvas into a grid, calculates average colors, converts to luminance to map height, and uses K-Means to quantize colors to a small buildable set.
3. **3D Visualization**: Users preview an interactive 3D model of the resulting physical artwork.
4. **Export Blueprint**: Generates a physically scaled, print-ready PDF containing the cut/fold blueprints (origami nets) and a 2D placement guide.

## Tech Stack
* **Frontend**: Next.js (React), Tailwind CSS (Notion-style minimalist aesthetic), React Three Fiber (3D visualization).
* **Backend**: Python (FastAPI).
* **Image Processing**: OpenCV, NumPy, scikit-learn.
* **PDF Generation**: reportlab or cairo.

## Operational Directives
* Strict separation of pixels vs. physical dimensions (mm/inches).
* Explicit conversion utilities for physical unit scaling.
* High-contrast black-and-white minimalist design.
* Autonomy with checkpoints after each major phase.
