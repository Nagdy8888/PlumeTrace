import { useFrame } from "@react-three/fiber";
import { useMemo, type JSX } from "react";
import type { Object3D } from "three";

import { useStationStore } from "../store";
import type { NodeIndex } from "./nodeIndex";

/** The six fin-fan blade groups; each node's local Y axis is the hub axis. */
const FAN_NAMES = ["E-231", "E-232", "E-233"].flatMap((tag) => [`${tag}__fan_1`, `${tag}__fan_2`]);
const SPEED_RAD_S = 2.0;
const SPEED_REDUCED_RAD_S = 0.5;

/**
 * Spins the fin-fan coolers' fans about their local up axis. One `useFrame`, no allocation: the
 * fan nodes are collected once and the reduced-motion flag is read from the store, not subscribed.
 *
 * @param props - `index`: the station node index.
 * @returns Nothing (the fans are part of the loaded model).
 */
export function AnimatedParts({ index }: { index: NodeIndex }): JSX.Element | null {
  const fans = useMemo(
    () => FAN_NAMES.map((name) => index.get(name)).filter((node): node is Object3D => node !== undefined),
    [index],
  );
  useFrame((_, delta) => {
    const speed = useStationStore.getState().reducedMotion ? SPEED_REDUCED_RAD_S : SPEED_RAD_S;
    for (const fan of fans) fan.rotation.y += delta * speed;
  });
  return null;
}
