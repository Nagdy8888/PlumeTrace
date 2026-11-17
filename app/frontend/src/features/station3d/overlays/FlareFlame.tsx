import { Billboard } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useEffect, useMemo, type JSX } from "react";
import { Color, ShaderMaterial, Vector3 } from "three";

import { useClockStore } from "@/shared/playback";

import { useNodeIndex } from "../model/nodeIndex";
import { useQualityTier, useStationStore } from "../store";

const TIP_NAME = "FL-601.tip";
const WIDTH_M = 1.2;
const HEIGHT_M = 2.4;
const CORE = "#ffb347";
/** The colour is scaled above 1 so it passes the bloom threshold; without bloom (low tier) it stays at 1. */
const BLOOM_GAIN = 4;
const REDUCED_MOTION_SCALE = 0.25;
const tip = new Vector3();

const VERTEX = /* glsl */ `
varying vec2 vUv;
void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }
`;

/** A teardrop from the plane's uv: wide at the base, a point at the top, brighter in the core. */
const FRAGMENT = /* glsl */ `
uniform vec3 uColor;
uniform float uTime;
uniform float uGain;
varying vec2 vUv;
void main() {
  float flicker = 0.85 + 0.15 * sin(uTime * 13.0 + sin(uTime * 7.0));
  float width = 0.5 * pow(1.0 - vUv.y, 0.7) * (0.6 + 0.4 * smoothstep(0.0, 0.25, vUv.y));
  float edge = smoothstep(width, width * 0.35, abs(vUv.x - 0.5));
  float core = 1.0 - 0.45 * vUv.y;
  float alpha = edge * (1.0 - vUv.y) * flicker;
  if (alpha < 0.02) discard;
  gl_FragColor = vec4(uColor * uGain * core * flicker, alpha);
  #include <colorspace_fragment>
}
`;

/**
 * The flare flame at the tip of `FL-601`: a billboard plane with a flickering teardrop shader.
 * The pilot is lit in every MVP scenario, so the flame is always drawn. On high and medium its
 * colour is above 1 so the bloom pass picks it up; the flicker time advances only while the clock
 * plays and at a quarter speed with reduced motion. Nothing is drawn if the model has no tip node.
 *
 * @returns The billboard, or nothing when the tip node is missing.
 */
export function FlareFlame(): JSX.Element | null {
  const index = useNodeIndex();
  const tier = useQualityTier();
  const node = index.get(TIP_NAME);
  const material = useMemo(
    () =>
      new ShaderMaterial({
        vertexShader: VERTEX,
        fragmentShader: FRAGMENT,
        uniforms: { uColor: { value: new Color(CORE) }, uTime: { value: 0 }, uGain: { value: 1 } },
        transparent: true,
        depthWrite: false,
        toneMapped: false,
      }),
    [],
  );
  useEffect(() => () => material.dispose(), [material]);
  useEffect(() => {
    material.uniforms.uGain!.value = tier === "low" ? 1 : BLOOM_GAIN;
  }, [material, tier]);
  useFrame((_, delta) => {
    if (!useClockStore.getState().playing) return;
    material.uniforms.uTime!.value += delta * (useStationStore.getState().reducedMotion ? REDUCED_MOTION_SCALE : 1);
  });
  if (node === undefined) return null;
  node.getWorldPosition(tip);
  return (
    <Billboard name="flare-flame" position={[tip.x, tip.y + HEIGHT_M / 2, tip.z]} lockX lockZ>
      <mesh material={material} raycast={() => undefined}>
        <planeGeometry args={[WIDTH_M, HEIGHT_M]} />
      </mesh>
    </Billboard>
  );
}
