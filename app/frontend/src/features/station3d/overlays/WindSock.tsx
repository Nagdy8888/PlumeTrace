import { useEffect, useMemo, type JSX } from "react";
import { CylinderGeometry, DoubleSide, MeshStandardMaterial } from "three";

import { useSampleIndex } from "@/shared/playback";
import type { ReplayScenario } from "@/shared/types/generated/contract";

import { FACILITY } from "../model/facility";
import { windTowardScene } from "../plume/plumeMath";
import { specToScene } from "../scene/coords";

const MAST_TAG = "MET-01";
const SOCK_LENGTH_M = 1.4;
const MAX_PITCH_DEG = 60;
/** Wind speed at which the sock flies level, m/s. */
const LEVEL_SPEED_M_S = 7;
const RED = "#8c2a22";
const WHITE = "#e6e2da";

/** Pitch below horizontal in radians: 60 degrees when calm, level from 7 m/s. */
function pitchRad(speedMS: number): number {
  return (MAX_PITCH_DEG * (Math.PI / 180)) * (1 - Math.min(speedMS, LEVEL_SPEED_M_S) / LEVEL_SPEED_M_S);
}

/**
 * Windsock on the met mast `MET-01`: a mast pole and an open two-band cone that points the way the
 * wind blows (from the sample's wind direction) and droops more the lighter the wind. It updates
 * once per sample index, not per frame, and has no animation, so reduced motion needs no case.
 * The mast position comes from the facility spec.
 *
 * @param props - `scenario`: the loaded replay scenario (wind per sample), or null.
 * @returns The mast and sock, or nothing without a scenario or a mast in the spec.
 */
export function WindSock({ scenario }: { scenario: ReplayScenario | null }): JSX.Element | null {
  const sampleIndex = useSampleIndex();
  const mast = FACILITY.instruments.find((i) => i.tag === MAST_TAG);
  const parts = useMemo(() => {
    const half = SOCK_LENGTH_M / 2;
    const band = (r0: number, r1: number, offset: number): CylinderGeometry =>
      new CylinderGeometry(r1, r0, half, 16, 1, true).rotateZ(-Math.PI / 2).translate(offset, 0, 0);
    return {
      pole: new CylinderGeometry(0.05, 0.05, 1, 8),
      red: band(0.25, 0.185, half / 2),
      white: band(0.185, 0.12, half + half / 2),
      redMaterial: new MeshStandardMaterial({ color: RED, side: DoubleSide, roughness: 0.8 }),
      whiteMaterial: new MeshStandardMaterial({ color: WHITE, side: DoubleSide, roughness: 0.8 }),
      poleMaterial: new MeshStandardMaterial({ color: WHITE, roughness: 0.6 }),
    };
  }, []);
  useEffect(() => () => Object.values(parts).forEach((p) => p.dispose()), [parts]);
  if (scenario === null || mast === undefined) return null;
  const [x, y, z] = specToScene(mast.position_m);
  const [toX, toZ] = windTowardScene(scenario.wind_from_deg[sampleIndex] ?? 0);
  const pitch = pitchRad(scenario.wind_speed_m_s[sampleIndex] ?? 0);
  return (
    <group name="windsock" position={[x, 0, z]}>
      <mesh geometry={parts.pole} material={parts.poleMaterial} position={[0, y / 2, 0]} scale={[1, y, 1]} raycast={() => undefined} />
      <group position={[0, y, 0]} rotation={[0, Math.atan2(-toZ, toX), 0]}>
        <group rotation={[0, 0, -pitch]}>
          <mesh geometry={parts.red} material={parts.redMaterial} raycast={() => undefined} />
          <mesh geometry={parts.white} material={parts.whiteMaterial} raycast={() => undefined} />
        </group>
      </group>
    </group>
  );
}
