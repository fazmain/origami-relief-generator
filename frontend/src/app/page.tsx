"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { CellData } from "../components/ReliefVisualizer";

// Dynamically import Three.js to avoid SSR issues
const ReliefVisualizer = dynamic(() => import("../components/ReliefVisualizer"), {
  ssr: false,
  loading: () => <div className="w-full h-full flex items-center justify-center bg-gray-100 border border-black">Loading 3D Visualizer...</div>
});

interface Metadata {
  num_cols: number;
  num_rows: number;
  box_size_mm: number;
  R: number;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [width, setWidth] = useState<number>(300);
  const [height, setHeight] = useState<number>(300);
  const [aspectRatio, setAspectRatio] = useState<number>(1);
  const [maxHeightMm, setMaxHeightMm] = useState<number>(50);
  const [minHeightMm, setMinHeightMm] = useState<number>(10);
  
  const [algorithm, setAlgorithm] = useState<"depth" | "luminance">("depth");
  
  const [resolutionMode, setResolutionMode] = useState<"size" | "count">("count");
  const [boxSizeMm, setBoxSizeMm] = useState<number>(15);
  const [targetPieces, setTargetPieces] = useState<number>(500);

  const [loading, setLoading] = useState(false);
  
  const [gridData, setGridData] = useState<CellData[] | null>(null);
  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [error, setError] = useState<string>("");

  // 3D Visualizer Controls
  const [explodeFactor, setExplodeFactor] = useState<number>(0);
  const [sunAzimuth, setSunAzimuth] = useState<number>(45);
  const [sunElevation, setSunElevation] = useState<number>(45);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0] || null;
    setFile(selectedFile);

    if (selectedFile) {
      const img = new window.Image();
      const objectUrl = URL.createObjectURL(selectedFile);
      img.onload = () => {
        const aspect = img.width / img.height;
        setAspectRatio(aspect);
        // Keep current width (mm), recompute height to match image aspect ratio.
        // Do NOT use img.width/img.height — those are pixels, not physical mm.
        setHeight(Math.round(width / aspect));
        URL.revokeObjectURL(objectUrl);
      };
      img.src = objectUrl;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please select an image file.");
      return;
    }

    setLoading(true);
    setError("");
    setGridData(null);

    let finalBoxSize = boxSizeMm;
    if (resolutionMode === "count") {
      const canvasArea = width * height;
      const hexAreaFactor = 1.5 * Math.sqrt(3);
      const R = Math.sqrt(canvasArea / (targetPieces * hexAreaFactor));
      finalBoxSize = 2 * R;
    }

    // Footprint check for PDF generation (Letter size width is ~215.9mm, margin 10mm -> ~205.9mm max)
    const footprint = 2 * finalBoxSize + 2 * maxHeightMm + 10 + 10;
    if (footprint > 205.9) {
      // Just warn the user, do not block generation
      alert(`Warning: The physical piece size (${finalBoxSize.toFixed(1)}mm) and max height (${maxHeightMm}mm) create a footprint (${footprint.toFixed(1)}mm) that exceeds standard Letter paper width (205.9mm). PDF generation may clip out of bounds.`);
    }

    const formData = new FormData();
    formData.append("image", file);
    formData.append("width_mm", width.toString());
    formData.append("height_mm", height.toString());
    formData.append("min_box_size_mm", finalBoxSize.toString());
    formData.append("min_height_mm", minHeightMm.toString());
    formData.append("max_height_mm", maxHeightMm.toString());
    formData.append("algorithm", algorithm);

    try {
      const res = await fetch(`${API_URL}/api/process`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to process image");
      }

      const data = await res.json();
      setGridData(data.grid);
      setMetadata(data.metadata);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("An unknown error occurred");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPDF = async () => {
    if (!gridData || !metadata) return;
    
    try {
      const res = await fetch(`${API_URL}/api/pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ grid: gridData, metadata }),
      });

      if (!res.ok) {
        throw new Error("Failed to generate PDF");
      }

      // Convert response to blob and trigger download
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "origami_blueprint.pdf";
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: unknown) {
      if (err instanceof Error) {
        alert("Error: " + err.message);
      }
    }
  };

  const handleDownloadPoster = async () => {
    if (!gridData || !metadata) return;
    
    try {
      const res = await fetch(`${API_URL}/api/pdf_poster`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ grid: gridData, metadata }),
      });

      if (!res.ok) {
        throw new Error("Failed to generate Poster PDF");
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "origami_poster.pdf";
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: unknown) {
      if (err instanceof Error) {
        alert("Error: " + err.message);
      }
    }
  };

  return (
    <div className="min-h-screen bg-white text-black font-sans flex flex-col">
      <header className="border-b-2 border-black p-6">
        <h1 className="text-3xl font-bold tracking-tight uppercase">Origami Relief Generator</h1>
        <p className="text-gray-600 mt-1">Image to 3D Physical Blueprint</p>
      </header>

      <main className="flex-1 flex flex-col md:flex-row">
        {/* Sidebar Controls */}
        <div className="w-full md:w-1/3 p-6 border-r-2 border-black flex flex-col gap-6 overflow-y-auto">
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label className="block text-sm font-bold uppercase mb-2">1. Upload Image</label>
              <input 
                type="file" 
                accept="image/*"
                onChange={handleFileChange}
                className="w-full border-2 border-black p-2 file:mr-4 file:py-2 file:px-4 file:rounded-none file:border-0 file:bg-black file:text-white hover:file:bg-gray-800"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-bold uppercase mb-2">Width (mm)</label>
                <input 
                  type="number" 
                  value={width} 
                  onChange={(e) => {
                    const val = Number(e.target.value);
                    setWidth(val);
                    setHeight(Math.round(val / aspectRatio));
                  }}
                  className="w-full border-2 border-black p-2 focus:outline-none focus:ring-2 focus:ring-gray-300"
                />
              </div>
              <div>
                <label className="block text-sm font-bold uppercase mb-2">Height (mm)</label>
                <input 
                  type="number" 
                  value={height} 
                  onChange={(e) => {
                    const val = Number(e.target.value);
                    setHeight(val);
                    setWidth(Math.round(val * aspectRatio));
                  }}
                  className="w-full border-2 border-black p-2 focus:outline-none focus:ring-2 focus:ring-gray-300"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-bold uppercase mb-2">Min Z (mm)</label>
                <input 
                  type="number" 
                  value={minHeightMm} 
                  onChange={(e) => setMinHeightMm(Number(e.target.value))}
                  className="w-full border-2 border-black p-2 focus:outline-none focus:ring-2 focus:ring-gray-300"
                />
              </div>
              <div>
                <label className="block text-sm font-bold uppercase mb-2">Max Z (mm)</label>
                <input 
                  type="number" 
                  value={maxHeightMm} 
                  onChange={(e) => setMaxHeightMm(Number(e.target.value))}
                  className="w-full border-2 border-black p-2 focus:outline-none focus:ring-2 focus:ring-gray-300"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-bold uppercase mb-2">2. Resolution Mode</label>
              <div className="flex gap-4 mb-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input 
                    type="radio" 
                    name="resMode" 
                    value="count" 
                    checked={resolutionMode === "count"}
                    onChange={() => setResolutionMode("count")}
                    className="accent-black"
                  />
                  <span>Piece Count</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input 
                    type="radio" 
                    name="resMode" 
                    value="size" 
                    checked={resolutionMode === "size"}
                    onChange={() => setResolutionMode("size")}
                    className="accent-black"
                  />
                  <span>Box Size</span>
                </label>
              </div>

              {resolutionMode === "count" ? (
                <div>
                  <label className="block text-xs uppercase mb-1">Target Pieces</label>
                  <input 
                    type="number" 
                    value={targetPieces} 
                    onChange={(e) => setTargetPieces(Number(e.target.value))}
                    className="w-full border-2 border-black p-2 focus:outline-none focus:ring-2 focus:ring-gray-300"
                  />
                </div>
              ) : (
                <div>
                  <label className="block text-xs uppercase mb-1">Min Box Size (mm)</label>
                  <input 
                    type="number" 
                    value={boxSizeMm} 
                    onChange={(e) => setBoxSizeMm(Number(e.target.value))}
                    className="w-full border-2 border-black p-2 focus:outline-none focus:ring-2 focus:ring-gray-300"
                  />
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-bold uppercase mb-2">3. Algorithm Mode</label>
              <div className="flex flex-col gap-2 mb-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input 
                    type="radio" 
                    name="algMode" 
                    value="depth" 
                    checked={algorithm === "depth"}
                    onChange={() => setAlgorithm("depth")}
                    className="accent-black"
                  />
                  <span>Depth Estimation (Sloped & Clustered)</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input 
                    type="radio" 
                    name="algMode" 
                    value="luminance" 
                    checked={algorithm === "luminance"}
                    onChange={() => setAlgorithm("luminance")}
                    className="accent-black"
                  />
                  <span>Luminance (Flat Hexagons)</span>
                </label>
              </div>
            </div>

            <button 
              type="submit" 
              disabled={loading}
              className="w-full bg-black text-white py-3 font-bold uppercase tracking-wider hover:bg-gray-800 disabled:opacity-50 mt-4"
            >
              {loading ? "Processing..." : "Generate 3D Grid"}
            </button>
          </form>

          {error && (
            <div className="p-4 border-2 border-red-500 text-red-700 bg-red-50 font-mono text-sm">
              ERROR: {error}
            </div>
          )}

          {metadata && (
            <div className="mt-4 p-4 border-2 border-black bg-gray-50">
              <h3 className="font-bold mb-2 uppercase border-b border-black pb-1">Result Metadata</h3>
              <ul className="text-sm space-y-1 font-mono">
                <li>Columns: {metadata.num_cols}</li>
                <li>Rows: {metadata.num_rows}</li>
                <li>Pieces: {gridData?.length || metadata.num_cols * metadata.num_rows}</li>
                <li>Box Size: {metadata.box_size_mm} mm</li>
              </ul>

              <button 
                onClick={handleDownloadPDF}
                className="w-full mt-6 bg-white text-black border-2 border-black py-3 font-bold uppercase tracking-wider hover:bg-black hover:text-white transition-colors"
              >
                Download PDF Blueprint
              </button>
              
              <button 
                onClick={handleDownloadPoster}
                className="w-full mt-2 bg-white text-black border-2 border-black py-3 font-bold uppercase tracking-wider hover:bg-black hover:text-white transition-colors"
              >
                Download 1:1 Poster Blueprint
              </button>
              
              <div className="mt-6 border-t border-black pt-4">
                <h3 className="font-bold mb-4 uppercase">3D Viewer Controls</h3>
                
                <div className="mb-4">
                  <label className="block text-xs uppercase mb-1">Explode View: {explodeFactor.toFixed(2)}</label>
                  <input 
                    type="range" 
                    min="0" max="1" step="0.05"
                    value={explodeFactor}
                    onChange={(e) => setExplodeFactor(Number(e.target.value))}
                    className="w-full accent-black"
                  />
                </div>
                
                <div className="mb-4">
                  <label className="block text-xs uppercase mb-1">Sun Azimuth: {sunAzimuth}°</label>
                  <input 
                    type="range" 
                    min="0" max="360" step="1"
                    value={sunAzimuth}
                    onChange={(e) => setSunAzimuth(Number(e.target.value))}
                    className="w-full accent-black"
                  />
                </div>
                
                <div>
                  <label className="block text-xs uppercase mb-1">Sun Elevation: {sunElevation}°</label>
                  <input 
                    type="range" 
                    min="10" max="90" step="1"
                    value={sunElevation}
                    onChange={(e) => setSunElevation(Number(e.target.value))}
                    className="w-full accent-black"
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 3D Visualizer Area */}
        <section className="flex-1 p-6 h-[600px] md:h-auto">
          {gridData && metadata ? (
            <ReliefVisualizer 
              grid={gridData} 
              metadata={metadata} 
              explodeFactor={explodeFactor}
              sunAzimuth={sunAzimuth}
              sunElevation={sunElevation}
            />
          ) : (
            <div className="w-full h-full border-2 border-dashed border-gray-400 flex items-center justify-center text-gray-400 font-mono">
              [ AWAITING INPUT ]
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
