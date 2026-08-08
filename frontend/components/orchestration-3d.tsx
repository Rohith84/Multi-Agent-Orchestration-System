/**
 * Orchestration3D — Interactive Three.js visualization of the MultiAgent core.
 *
 * Renders a central core sphere surrounded by 5 orbiting agent nodes
 * connected by animated data-path lines. Hover reveals agent tooltips.
 *
 * Uses vanilla Three.js via canvas ref (no R3F dependency).
 */

"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import * as THREE from "three";

interface AgentNode {
  name: string;
  color: string;
  angle: number;
  radius: number;
  speed: number;
  mesh?: THREE.Mesh;
}

const AGENTS: AgentNode[] = [
  { name: "Planner", color: "#DFFF00", angle: 0, radius: 3.0, speed: 0.3 },
  { name: "Researcher", color: "#22D3EE", angle: (Math.PI * 2 / 5), radius: 3.2, speed: 0.25 },
  { name: "Coder", color: "#8B5CF6", angle: (Math.PI * 2 / 5) * 2, radius: 2.8, speed: 0.35 },
  { name: "Tester", color: "#FBBF24", angle: (Math.PI * 2 / 5) * 3, radius: 3.1, speed: 0.28 },
  { name: "Reviewer", color: "#4ADE80", angle: (Math.PI * 2 / 5) * 4, radius: 3.0, speed: 0.32 },
];

interface TooltipState {
  visible: boolean;
  x: number;
  y: number;
  name: string;
  color: string;
}

export function Orchestration3D() {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const frameRef = useRef<number>(0);
  const mouseRef = useRef(new THREE.Vector2(-999, -999));
  const raycasterRef = useRef(new THREE.Raycaster());
  const agentMeshesRef = useRef<THREE.Mesh[]>([]);
  const [tooltip, setTooltip] = useState<TooltipState>({
    visible: false, x: 0, y: 0, name: "", color: "",
  });

  const initScene = useCallback(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    const width = container.clientWidth;
    const height = container.clientHeight;

    // Renderer
    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    rendererRef.current = renderer;

    // Scene
    const scene = new THREE.Scene();
    sceneRef.current = scene;

    // Camera
    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 100);
    camera.position.set(0, 2, 8);
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
    scene.add(ambientLight);

    const pointLight = new THREE.PointLight(0xdfff00, 1.5, 20);
    pointLight.position.set(0, 3, 5);
    scene.add(pointLight);

    const pointLight2 = new THREE.PointLight(0x8b5cf6, 0.8, 15);
    pointLight2.position.set(-3, -1, 3);
    scene.add(pointLight2);

    // Central Core
    const coreGeometry = new THREE.IcosahedronGeometry(0.8, 2);
    const coreMaterial = new THREE.MeshPhongMaterial({
      color: 0xdfff00,
      emissive: 0xdfff00,
      emissiveIntensity: 0.3,
      wireframe: false,
      transparent: true,
      opacity: 0.9,
    });
    const coreMesh = new THREE.Mesh(coreGeometry, coreMaterial);
    scene.add(coreMesh);

    // Core wireframe overlay
    const coreWireGeometry = new THREE.IcosahedronGeometry(0.85, 1);
    const coreWireMaterial = new THREE.MeshBasicMaterial({
      color: 0xdfff00,
      wireframe: true,
      transparent: true,
      opacity: 0.25,
    });
    const coreWireMesh = new THREE.Mesh(coreWireGeometry, coreWireMaterial);
    scene.add(coreWireMesh);

    // Orbit ring
    const ringGeometry = new THREE.RingGeometry(2.9, 3.0, 64);
    const ringMaterial = new THREE.MeshBasicMaterial({
      color: 0x333333,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.3,
    });
    const ring = new THREE.Mesh(ringGeometry, ringMaterial);
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = -0.2;
    scene.add(ring);

    // Agent nodes
    const meshes: THREE.Mesh[] = [];
    AGENTS.forEach((agent) => {
      const geo = new THREE.SphereGeometry(0.25, 16, 16);
      const mat = new THREE.MeshPhongMaterial({
        color: new THREE.Color(agent.color),
        emissive: new THREE.Color(agent.color),
        emissiveIntensity: 0.2,
      });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.userData = { name: agent.name, color: agent.color };
      scene.add(mesh);
      meshes.push(mesh);
      agent.mesh = mesh;
    });
    agentMeshesRef.current = meshes;

    // Connection lines (core to each agent)
    AGENTS.forEach((agent) => {
      const lineGeo = new THREE.BufferGeometry();
      const positions = new Float32Array(6);
      lineGeo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
      const lineMat = new THREE.LineBasicMaterial({
        color: new THREE.Color(agent.color),
        transparent: true,
        opacity: 0.2,
      });
      const line = new THREE.Line(lineGeo, lineMat);
      line.userData = { agentName: agent.name };
      scene.add(line);
    });

    // Animation loop
    let time = 0;
    const animate = () => {
      frameRef.current = requestAnimationFrame(animate);
      time += 0.01;

      // Rotate core
      coreMesh.rotation.y += 0.005;
      coreMesh.rotation.x += 0.002;
      coreWireMesh.rotation.y -= 0.003;
      coreWireMesh.rotation.z += 0.002;

      // Core breathing
      const scale = 1 + Math.sin(time * 2) * 0.05;
      coreMesh.scale.setScalar(scale);

      // Update agent positions
      AGENTS.forEach((agent, i) => {
        const a = agent.angle + time * agent.speed;
        const x = Math.cos(a) * agent.radius;
        const z = Math.sin(a) * agent.radius;
        const y = Math.sin(time * 1.5 + i) * 0.3 - 0.2;

        if (agent.mesh) {
          agent.mesh.position.set(x, y, z);

          // Subtle pulse
          const s = 1 + Math.sin(time * 3 + i) * 0.1;
          agent.mesh.scale.setScalar(s);
        }
      });

      // Update connection lines
      scene.children.forEach((child) => {
        if (child instanceof THREE.Line && child.userData.agentName) {
          const agent = AGENTS.find((a) => a.name === child.userData.agentName);
          if (agent?.mesh) {
            const positions = child.geometry.attributes.position;
            if (positions) {
              const arr = positions.array as Float32Array;
              arr[0] = 0; arr[1] = 0; arr[2] = 0;
              arr[3] = agent.mesh.position.x;
              arr[4] = agent.mesh.position.y;
              arr[5] = agent.mesh.position.z;
              positions.needsUpdate = true;
            }
          }
        }
      });

      // Raycasting for hover
      raycasterRef.current.setFromCamera(mouseRef.current, camera);
      const intersects = raycasterRef.current.intersectObjects(meshes);

      if (intersects.length > 0) {
        const hit = intersects[0].object;
        const { name, color } = hit.userData;
        const projected = hit.position.clone().project(camera);
        const px = (projected.x * 0.5 + 0.5) * width;
        const py = (-projected.y * 0.5 + 0.5) * height;
        setTooltip({ visible: true, x: px, y: py - 40, name, color });
      } else {
        setTooltip((prev) => (prev.visible ? { ...prev, visible: false } : prev));
      }

      renderer.render(scene, camera);
    };

    animate();
  }, []);

  // Handle resize
  useEffect(() => {
    initScene();

    const handleResize = () => {
      const container = containerRef.current;
      if (!container || !rendererRef.current || !cameraRef.current) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      rendererRef.current.setSize(w, h);
      cameraRef.current.aspect = w / h;
      cameraRef.current.updateProjectionMatrix();
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
      rendererRef.current?.dispose();
    };
  }, [initScene]);

  // Mouse tracking
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const container = containerRef.current;
    if (!container) return;
    const rect = container.getBoundingClientRect();
    mouseRef.current.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    mouseRef.current.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
  }, []);

  const handleMouseLeave = useCallback(() => {
    mouseRef.current.set(-999, -999);
    setTooltip((prev) => ({ ...prev, visible: false }));
  }, []);

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full min-h-[350px]"
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      <canvas ref={canvasRef} className="w-full h-full block" />

      {/* Hover Tooltip */}
      {tooltip.visible && (
        <div
          className="absolute pointer-events-none z-10 animate-fade-in"
          style={{
            left: tooltip.x,
            top: tooltip.y,
            transform: "translate(-50%, -100%)",
          }}
        >
          <div
            className="px-3 py-1.5 border-2 text-center"
            style={{
              borderColor: tooltip.color,
              background: "var(--bg-surface)",
              boxShadow: `2px 2px 0px 0px ${tooltip.color}`,
            }}
          >
            <span
              className="text-caption font-bold uppercase"
              style={{ color: tooltip.color }}
            >
              {tooltip.name}
            </span>
            <span
              className="block text-caption mt-0.5"
              style={{ color: "var(--fg-secondary)" }}
            >
              ONLINE
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
