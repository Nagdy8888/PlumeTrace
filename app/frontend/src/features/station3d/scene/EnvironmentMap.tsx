import { Environment } from "@react-three/drei";
import type { JSX } from "react";

/** Local HDRI (Poly Haven, CC0); it only lights the scene and is never drawn as the sky. */
const HDRI_FILE = "/textures/env/industrial_sunset_puresky_1k.hdr";

/** Environment light strength; the owner ruling C2 allows 0.4 to 0.8 (the ground must not read as snow). */
const ENVIRONMENT_INTENSITY = 0.6;

/**
 * Image-based lighting from the local HDRI plus a hazy grey sky colour.
 *
 * @returns The environment lighting and the scene background.
 */
export function EnvironmentMap(): JSX.Element {
  return (
    <>
      <Environment files={HDRI_FILE} background={false} environmentIntensity={ENVIRONMENT_INTENSITY} />
      <color attach="background" args={["#a9b4bd"]} />
    </>
  );
}
