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
  const { geometry, meshPosition } = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    const coords = cell.exterior_coords;
    if (!coords || coords.length < 3) return { geometry: geo, meshPosition: [0, 0, 0] as [number, number, number] };

    const num_sides = coords.length;

    // Scale slightly towards centroid for physical gap effect
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

    // Base vertices (index 0 to num_sides - 1), Y = 0
    for(let i = 0; i < num_sides; i++) {
        vertices.push(scaledCoords[i][0] - offsetX, 0, scaledCoords[i][1] - offsetZ);
    }

    // Top vertices scaled toward centroid by taper (1.0 = fully pointed)
    const topScale = 1.0 - taper;
    for(let i = 0; i < num_sides; i++) {
        const tx = cx + (scaledCoords[i][0] - cx) * topScale;
        const tz = cy + (scaledCoords[i][1] - cy) * topScale;
        vertices.push(tx - offsetX, cell.top_vertices_z[i], tz - offsetZ);
    }

    // Indices for Bottom Face (normals pointing down)
    for(let i = 0; i < triangles.length; i++) {
        // Reverse winding to point down
        indices.push(triangles[i][0], triangles[i][2], triangles[i][1]);
    }

    // Indices for Top Face (normals pointing up)
    for(let i = 0; i < triangles.length; i++) {
        indices.push(triangles[i][0] + num_sides, triangles[i][1] + num_sides, triangles[i][2] + num_sides);
    }

    // Indices for Side Walls
    for(let i = 0; i < num_sides; i++) {
        const next = (i + 1) % num_sides;
        const b1 = i;
        const b2 = next;
        const t1 = i + num_sides;
        const t2 = next + num_sides;

        // normal points out
        indices.push(b1, t2, b2);
        indices.push(b1, t1, t2);
    }

    geo.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    geo.setIndex(indices);
    geo.computeVertexNormals();
    
    // Exploded view offset
    const worldCx = cx - offsetX;
    const worldCz = cy - offsetZ;
    const meshPosition = [worldCx * explodeFactor, 0, worldCz * explodeFactor] as [number, number, number];

    return { geometry: geo, meshPosition };
  }, [cell, offsetX, offsetZ, explodeFactor, taper]);

  return (
    <mesh geometry={geometry} position={meshPosition} castShadow receiveShadow>
      <meshStandardMaterial color={cell.color} roughness={0.7} side={THREE.DoubleSide} />
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
      <Canvas shadows camera={{ position: [0, 300, 300], fov: 45, near: 0.1, far: 10000 }}>
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
