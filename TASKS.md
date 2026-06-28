# Feature Roadmap

`[ ]` = todo · `[-]` = in progress · `[x]` = done

---

## Tier 1 — Makes Physical Construction Possible

- [ ] **Discrete height quantization** — Snap continuous heights to N user-defined levels (e.g. 4 levels: 10/20/30/40mm). All pieces at the same level are identical → batch fold a stack. UI: slider for N levels + preview histogram.
- [ ] **Bill of Materials PDF page** — Summary page appended to every blueprint: color swatches, piece count per height level, estimated cardstock sheet count (given paper size input).
- [ ] **Assembly coordinates on pieces** — Print grid position (e.g. "R12-C08") on each cut net so you know exactly where it goes during assembly.
- [ ] **Print calibration square** — 50×50mm reference square on page 1 of every PDF. Measure before cutting to verify printer is at 100% scale.

---

## Tier 2 — Art Quality

- [ ] **DXF/SVG export** — Vector format for laser cutters and vinyl plotters. Dramatically better cut precision than hand-cutting from PDF. Single biggest quality upgrade.
- [ ] **Batch cut grouping** — Group all identical pieces (same color + same height level) on consecutive pages. Stack cardstock, cut multiples simultaneously.
- [ ] **Manual color palette editor** — Post-K-means UI: swap colors between clusters, merge two clusters, click a swatch to set a specific hex color. K-means picks statistically right colors, not artistically right ones.
- [ ] **Depth/height curve editor** — Control luminance→height mapping with a curve control (linear, S-curve, custom). Preview height histogram before committing.
- [ ] **Image preprocessing panel** — Brightness, contrast, saturation sliders applied before processing. Boost contrast for stronger relief effect.

---

## Tier 3 — Platform

- [ ] **Square prism mode** — Squares tile cleanly with no offset, simpler to fold than hexagons. Add as shape option alongside hex. Directly enables "Twisted Box" style artwork.
- [ ] **Relief statistics panel** — After processing: piece count, estimated fold time at N min/piece, paper sheets needed, estimated paper cost at $/sheet.
- [ ] **Backboard/frame generation** — Flat surround piece for framing the hex grid, with mounting holes. Makes the piece look finished on a wall.
- [ ] **Save/load project** — Download/upload `.origami` JSON project file (grid + settings) to resume work across sessions.
- [ ] **Cone/pyramid prism shapes** — Tapered pieces (wider base, pointed top) cast much more dramatic shadows. Paragami "Coral Sponge" / "Whirl Peak" style.

---

## Tier 4 — Advanced

- [ ] **Parametric pattern designs** — Non-photo-derived geometric motifs (waves, spirals, radial spikes) composable as layers on top of or instead of a photo. How paragami's signature pieces work.
- [ ] **Tiling/modular panels** — Split large artworks into independently assembleable panels (e.g. 60×60cm) that tile together for very large installations.
- [ ] **LED compatibility mode** — Design consideration: hollow bases, minimum spacing for LED strip placement underneath pieces.
