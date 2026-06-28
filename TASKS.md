# Feature Roadmap

`[ ]` = todo · `[-]` = in progress · `[x]` = done

---

## Tier 1 — Makes Physical Construction Possible

- [x] **Discrete height quantization** — Snap continuous heights to N user-defined levels (e.g. 4 levels: 10/20/30/40mm). All pieces at the same level are identical → batch fold a stack. UI: slider for N levels + preview histogram.
- [x] **Bill of Materials PDF page** — Summary page appended to every blueprint: color swatches, piece count per height level, estimated cardstock sheet count (given paper size input).
- [x] **Assembly coordinates on pieces** — Print grid position (e.g. "R12-C08") on each cut net so you know exactly where it goes during assembly.
- [x] **Print calibration square** — 50×50mm reference square on page 1 of every PDF. Measure before cutting to verify printer is at 100% scale.

---

## Tier 2 — Art Quality

- [x] **DXF/SVG export** — Vector format for laser cutters and vinyl plotters. Dramatically better cut precision than hand-cutting from PDF. Single biggest quality upgrade.
- [x] **Batch cut grouping** — Group all identical pieces (same color + same height level) on consecutive pages. Stack cardstock, cut multiples simultaneously.
- [x] **Manual color palette editor** — Post-K-means UI: swap colors between clusters, merge two clusters, click a swatch to set a specific hex color. K-means picks statistically right colors, not artistically right ones.
- [x] **Depth/height curve editor** — Control luminance→height mapping via gamma parameter (0.25–4.0). Preview hint text describes effect. Applied to both depth and luminance algorithms.
- [x] **Image preprocessing panel** — Brightness, contrast, saturation sliders applied before processing. Boost contrast for stronger relief effect.

---

## Tier 3 — Platform

- [x] **Square prism mode** — Squares tile cleanly with no offset, simpler to fold than hexagons. Shape option alongside hex. Directly enables "Twisted Box" style artwork.
- [x] **Relief statistics panel** — After processing: piece count, color count, average height, estimated paper usage (A4 sheets), fold time estimate, total fold count.
- [x] **Backboard/frame generation** — 1:1 scale PDF gluing guide showing each cell outline with piece ID and grid position label. Acts as a physical assembly template.
- [x] **Save/load project** — Download/upload `.origami` JSON project file (grid + all settings) to resume work across sessions.
- [ ] **Cone/pyramid prism shapes** — Tapered pieces (wider base, pointed top) cast much more dramatic shadows. Paragami "Coral Sponge" / "Whirl Peak" style.

---

## Tier 4 — Advanced

- [ ] **Parametric pattern designs** — Non-photo-derived geometric motifs (waves, spirals, radial spikes) composable as layers on top of or instead of a photo. How paragami's signature pieces work.
- [x] **Tiling/modular panels** — Split large artworks into independently assembleable panels (e.g. A4 tiles) that tile together for very large installations. Configurable tile size; one PDF page group per tile.
- [ ] **LED compatibility mode** — Design consideration: hollow bases, minimum spacing for LED strip placement underneath pieces.
