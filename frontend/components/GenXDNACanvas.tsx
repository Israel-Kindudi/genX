"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { Sparkles } from "@react-three/drei";
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";

const HELIX_HEIGHT = 4.4;
const HELIX_RADIUS = 0.85;
const NODE_COUNT = 18;

function pointOnStrand(index: number, offset: number) {
  const angle = index * 0.72 + offset;
  const y = (index / (NODE_COUNT - 1) - 0.5) * HELIX_HEIGHT;
  return new THREE.Vector3(
    Math.sin(angle) * HELIX_RADIUS,
    y,
    Math.cos(angle) * HELIX_RADIUS
  );
}

function Strand({
  offset,
  color,
  emissive,
}: {
  offset: number;
  color: string;
  emissive: string;
}) {
  const points = Array.from({ length: NODE_COUNT * 4 }, (_, index) =>
    pointOnStrand(index / 4, offset)
  );
  const curve = new THREE.CatmullRomCurve3(points);
  const geometry = new THREE.TubeGeometry(curve, 180, 0.018, 8, false);

  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial
        color={color}
        emissive={emissive}
        emissiveIntensity={0.65}
        metalness={0.55}
        roughness={0.3}
      />
    </mesh>
  );
}

function Rung({ index }: { index: number }) {
  const first = pointOnStrand(index, 0);
  const second = pointOnStrand(index, Math.PI);
  const direction = new THREE.Vector3().subVectors(second, first);
  const geometry = new THREE.CylinderGeometry(
    0.014,
    0.014,
    direction.length(),
    8
  );
  const quaternion = new THREE.Quaternion().setFromUnitVectors(
    new THREE.Vector3(0, 1, 0),
    direction.normalize()
  );

  return (
    <mesh
      geometry={geometry}
      position={first.clone().add(second).multiplyScalar(0.5)}
      quaternion={quaternion}
    >
      <meshStandardMaterial
        color={index % 3 === 0 ? "#7c2d12" : "#334155"}
        emissive={index % 3 === 0 ? "#f97316" : "#10b981"}
        emissiveIntensity={index % 3 === 0 ? 0.45 : 0.35}
        metalness={0.6}
        roughness={0.35}
      />
    </mesh>
  );
}

function Helix() {
  const group = useRef<THREE.Group>(null);
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const updatePreference = () => setReducedMotion(preference.matches);
    updatePreference();
    preference.addEventListener("change", updatePreference);
    return () => preference.removeEventListener("change", updatePreference);
  }, []);

  useFrame(({ clock, pointer }) => {
    if (!group.current || reducedMotion) return;
    const time = clock.getElapsedTime();
    
    group.current.rotation.y = Math.sin(time * 0.34) * 0.72;

    const targetRotX = 0.26 + pointer.y * 0.12;
    const targetRotZ = -0.48 - pointer.x * 0.08;

    group.current.rotation.x += (targetRotX - group.current.rotation.x) * 0.025;
    group.current.rotation.z += (targetRotZ - group.current.rotation.z) * 0.025;
  });

  return (
    <group ref={group} rotation={[0.26, 0, -0.48]}>
      <Strand offset={0} color="#064e3b" emissive="#10b981" />
      <Strand offset={Math.PI} color="#7c2d12" emissive="#f97316" />
      {Array.from({ length: NODE_COUNT }, (_, index) => {
        const first = pointOnStrand(index, 0);
        const second = pointOnStrand(index, Math.PI);
        return (
          <group key={index}>
            <Rung index={index} />
            <mesh position={first}>
              <sphereGeometry args={[0.075, 20, 20]} />
              <meshStandardMaterial
                color={index % 4 === 0 ? "#fb923c" : "#34d399"}
                emissive={index % 4 === 0 ? "#f97316" : "#10b981"}
                emissiveIntensity={index % 4 === 0 ? 1.1 : 1.35}
                roughness={0.2}
              />
            </mesh>
            <mesh position={second}>
              <sphereGeometry args={[0.075, 20, 20]} />
              <meshStandardMaterial
                color={index % 4 === 0 ? "#fda4af" : "#a7f3d0"}
                emissive={index % 4 === 0 ? "#ef4444" : "#10b981"}
                emissiveIntensity={index % 4 === 0 ? 0.95 : 1.15}
                roughness={0.2}
              />
            </mesh>
          </group>
        );
      })}
    </group>
  );
}

export default function GenXDNACanvas() {
  return (
    <div
      aria-label="Interactive animated 3D DNA helix with high particle density"
      className="relative h-[24rem] w-full max-w-xl md:h-[32rem]"
      role="img"
    >
      <Canvas
        camera={{ position: [0, 0, 7.2], fov: 38 }}
        dpr={[1, 1.5]}
        gl={{ alpha: true, antialias: true, powerPreference: "low-power" }}
      >
        <ambientLight intensity={0.75} />
        <pointLight position={[3, 2, 4]} intensity={18} color="#34d399" />
        <pointLight position={[-3, -2, 1]} intensity={9} color="#065f46" />
        <pointLight position={[-2, 1, 3]} intensity={7} color="#f97316" />
        <Helix />
        
        <Sparkles
          count={110}
          scale={[6.5, 7.5, 3]}
          size={1.5}
          speed={0.3}
          color="#6ee7b7"
          opacity={0.55}
        />

        <Sparkles
          count={32}
          scale={[5, 6, 2.5]}
          size={3.2}
          speed={0.15}
          color="#fb923c"
          opacity={0.85}
        />
        <Sparkles
          count={18}
          scale={[4.5, 5.5, 2]}
          size={2}
          speed={0.2}
          color="#fda4af"
          opacity={0.45}
        />
      </Canvas>
    </div>
  );
}