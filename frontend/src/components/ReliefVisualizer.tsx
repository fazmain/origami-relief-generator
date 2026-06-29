"use client";

import { Canvas } from "@react-three/fiber";
import { OrbitControls, Grid } from "@react-three/drei";
import * as THREE from "three";
import { useMemo } from "react";

export type CellData = {
  id: string;
  color: string;
  height_mm: number;
  exterior_coords: [number, number][];
  top_vertices_z: number[];
  is_cluster?: boolean;
};

type ReliefVisualizerProps = {
  grid: CellData[];
  metadata: {
    num_cols: number;
    num_rows: number;
    box_size_mm: number;
    R: number;
  };
  explodeFactor?: number;
  sunAzimuth?: number;
  sunElevation?: number;
  taper?: number;
};

function PolygonPrism({ cell, offsetX, offsetZ, explodeFactor = 0, taper = 0 }: { cell: CellData; offsetX: number; offsetZ: number; explodeFactor?: number; taper?: number }) {
  const { geometry, centroidX, centroidZ } = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    const coords = cell.exterior_coords;
    if (!coords || coords.length < 3) return { geometry: geo, centroidX: 0, centroidZ: 0 };

    const num_sides = coords.length;

    let cx = 0, cy = 0;
    for(let i = 0; i < num_sides; i++) {
        cx += coords[i][0];
        cy += coords[i][1];
    }
    cx /= num_sides;
    cy /= num_sides;

    const gapScale = 0.97;
    const scaledCoords = coords.map(p => [
        cx + (p[0] - cx) * gapScale,
        cy + (p[1] - cy) * gapScale
    ]);

    const contour = scaledCoords.map(p => new THREE.Vector2(p[0], p[1]));
    const triangles = THREE.ShapeUtils.triangulateShape(contour, []);

    const vertices: number[] = [];
    const indices: number[] = [];

    for(let i = 0; i < num_sides; i++) {
        vertices.push(scaledCoords[i][0] - offsetX, 0, scaledCoords[i][1] - offsetZ);
    }

    const topScale = 1.0 - taper;
    for(let i = 0; i < num_sides; i++) {
        const tx = cx + (scaledCoords[i][0] - cx) * topScale;
        const tz = cy + (scaledCoords[i][1] - cy) * topScale;
        vertices.push(tx - offsetX, cell.top_vertices_z[i], tz - offsetZ);
    }

    // Hex verts go CW in XZ from above → triangulateShape produces CW triangles → -Y normals.
    // Bottom cap: -Y normal (pointing down) = CW = use triangles as-is.
    for(let i = 0; i < triangles.length; i++) {
        indices.push(triangles[i][0], triangles[i][1], triangles[i][2]);
    }
    // Top cap: +Y normal (pointing up) = CCW = reverse each triangle.
    for(let i = 0; i < triangles.length; i++) {
        indices.push(triangles[i][0] + num_sides, triangles[i][2] + num_sides, triangles[i][1] + num_sides);
    }
    // Side walls: (b1, t2, b2) winding gives outward normals for CW hex verts.
    for(let i = 0; i < num_sides; i++) {
        const next = (i + 1) % num_sides;
        indices.push(i, next + num_sides, next);
        indices.push(i, i + num_sides, next + num_sides);
    }

    geo.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    geo.setIndex(indices);
    geo.computeVertexNormals();

    return { geometry: geo, centroidX: cx - offsetX, centroidZ: cy - offsetZ };
  }, [cell, offsetX, offsetZ, taper]); // explodeFactor excluded — position computed separately

  const meshPosition: [number, number, number] = [
    centroidX * explodeFactor,
    0,
    centroidZ * explodeFactor,
  ];

  return (
    <mesh geometry={geometry} position={meshPosition} castShadow receiveShadow>
      <meshStandardMaterial color={cell.color} roughness={0.8} metalness={0} side={THREE.FrontSide} />
    </mesh>
  );
}

export default function ReliefVisualizer({ grid, metadata, explodeFactor = 0, sunAzimuth = 45, sunElevation = 45, taper = 0 }: ReliefVisualizerProps) {
  const { num_cols, num_rows, R } = metadata;

  // Staggered layout offsets
  const scale_x = 1.5 * R;
  const scale_y = Math.sqrt(3) * R;

  const offsetX = (num_cols * scale_x) / 2;
  const offsetZ = (num_rows * scale_y) / 2;
  
  // Calculate sun position from spherical coordinates
  const azRad = sunAzimuth * (Math.PI / 180);
  const elRad = sunElevation * (Math.PI / 180);
  const dist = 500;
  
  const sunX = Math.cos(elRad) * Math.sin(azRad) * dist;
  const sunY = Math.sin(elRad) * dist;
  const sunZ = Math.cos(elRad) * Math.cos(azRad) * dist;

  return (
    <div className="w-full h-full bg-gray-100 border border-black relative">
      <Canvas shadows={{ type: THREE.PCFShadowMap }} camera={{ position: [0, 300, 300], fov: 45, near: 0.1, far: 10000 }}>
        <ambientLight intensity={0.4} />
        <directionalLight 
          position={[sunX, sunY, sunZ]} 
          intensity={1.2} 
          castShadow 
          shadow-mapSize-width={2048} 
          shadow-mapSize-height={2048}
          shadow-camera-far={2000}
          shadow-camera-left={-500}
          shadow-camera-right={500}
          shadow-camera-top={500}
          shadow-camera-bottom={-500}
        />
        
        {/* Floor to receive shadows */}
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.1, 0]} receiveShadow>
          <planeGeometry args={[2000, 2000]} />
          <shadowMaterial opacity={0.4} />
        </mesh>
        
        {grid.map((cell) => (
          <PolygonPrism key={cell.id} cell={cell} offsetX={offsetX} offsetZ={offsetZ} explodeFactor={explodeFactor} taper={taper} />
        ))}

        <Grid 
          infiniteGrid 
          fadeDistance={2000}
          sectionColor="#000"
          cellColor="#555"
          position={[0, -0.2, 0]} 
        />
        <OrbitControls makeDefault />
      </Canvas>
    </div>
  );
}
