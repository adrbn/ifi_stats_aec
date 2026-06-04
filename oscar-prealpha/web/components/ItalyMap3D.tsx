"use client";

import { Canvas } from "@react-three/fiber";
import { Html, OrbitControls, Line } from "@react-three/drei";
import { useMemo } from "react";
import * as THREE from "three";
import type { AntennaRow, Antenna } from "@/lib/types";
import { formatInt } from "@/lib/format";

// Geographic projection → scene XZ plane (north = -z).
const LNG0 = 12.5;
const LAT0 = 42;
const SCALE = 0.85;
function project(lat: number, lng: number): [number, number] {
  return [(lng - LNG0) * SCALE, -(lat - LAT0) * SCALE];
}

interface Pin {
  code: string;
  name: string;
  color: string;
  x: number;
  z: number;
  height: number;
  value: number;
}

function Bar({ pin }: { pin: Pin }) {
  return (
    <group position={[pin.x, 0, pin.z]}>
      <mesh position={[0, pin.height / 2, 0]} castShadow>
        <cylinderGeometry args={[0.12, 0.12, pin.height, 24]} />
        <meshStandardMaterial
          color={pin.color}
          emissive={pin.color}
          emissiveIntensity={0.45}
          roughness={0.35}
          metalness={0.1}
        />
      </mesh>
      <mesh position={[0, 0.01, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[0.22, 32]} />
        <meshStandardMaterial color={pin.color} transparent opacity={0.35} />
      </mesh>
      <Html position={[0, pin.height + 0.35, 0]} center distanceFactor={8} occlude={false}>
        <div
          style={{
            fontFamily: "var(--font-sans)",
            background: "rgba(255,255,255,0.95)",
            border: "1px solid var(--neutral-200)",
            borderRadius: 6,
            boxShadow: "0 4px 6px -1px rgba(15,23,42,0.1)",
            padding: "4px 8px",
            whiteSpace: "nowrap",
            transform: "translateY(-4px)",
          }}
        >
          <div style={{ fontSize: 11, fontWeight: 700, color: pin.color }}>{pin.code}</div>
          <div style={{ fontSize: 11, fontVariantNumeric: "tabular-nums", color: "var(--neutral-700)" }}>
            {formatInt(pin.value)}
          </div>
        </div>
      </Html>
    </group>
  );
}

function Scene({ rows, antennas }: { rows: AntennaRow[]; antennas: Antenna[] }) {
  const pins: Pin[] = useMemo(() => {
    const max = Math.max(...rows.map((r) => r.inscriptions), 1);
    return rows
      .map((r) => {
        const a = antennas.find((x) => x.code === r.code);
        if (!a?.lat || !a?.lng) return null;
        const [x, z] = project(a.lat, a.lng);
        return {
          code: r.code,
          name: r.name,
          color: r.color,
          x,
          z,
          height: 0.5 + (r.inscriptions / max) * 3.2,
          value: r.inscriptions,
        };
      })
      .filter(Boolean) as Pin[];
  }, [rows, antennas]);

  const center: [number, number, number] = [0, 0, 0];

  return (
    <>
      <ambientLight intensity={0.7} />
      <directionalLight position={[4, 8, 4]} intensity={0.8} />
      <pointLight position={[-4, 4, -4]} intensity={0.4} color="#3B82F6" />

      {/* base */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 0]} receiveShadow>
        <planeGeometry args={[16, 16]} />
        <meshStandardMaterial color="#0f172a" roughness={1} />
      </mesh>
      <gridHelper args={[16, 32, "#1e293b", "#1e293b"]} position={[0, 0, 0]} />

      {/* connection arcs from each antenna to the IFI centroid */}
      {pins.map((p) => (
        <Line
          key={`arc-${p.code}`}
          points={[
            [p.x, 0.05, p.z],
            [(p.x + center[0]) / 2, 1.4, (p.z + center[2]) / 2],
            center,
          ]}
          color={p.color}
          lineWidth={1.2}
          transparent
          opacity={0.5}
        />
      ))}

      {/* IFI hub */}
      <mesh position={[0, 0.1, 0]}>
        <sphereGeometry args={[0.16, 24, 24]} />
        <meshStandardMaterial color="#3B82F6" emissive="#3B82F6" emissiveIntensity={0.6} />
      </mesh>

      {pins.map((p) => (
        <Bar key={p.code} pin={p} />
      ))}

      <OrbitControls
        enablePan={false}
        minDistance={5}
        maxDistance={14}
        maxPolarAngle={Math.PI / 2.2}
        autoRotate
        autoRotateSpeed={0.6}
      />
    </>
  );
}

export default function ItalyMap3D({
  rows,
  antennas,
}: {
  rows: AntennaRow[];
  antennas: Antenna[];
}) {
  return (
    <div className="h-[420px] w-full overflow-hidden rounded-md border border-neutral-200 bg-[#0f172a]">
      <Canvas
        shadows
        camera={{ position: [3.5, 6.5, 8], fov: 42 }}
        gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping }}
        dpr={[1, 2]}
      >
        <Scene rows={rows} antennas={antennas} />
      </Canvas>
    </div>
  );
}
