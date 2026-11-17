import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useLayoutEffect, useMemo, useRef, type JSX } from "react";
import {
  BoxGeometry,
  Color,
  CylinderGeometry,
  InstancedMesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  Object3D,
  TorusGeometry,
} from "three";

import { EVENT_WINDOW_S, visibleEvents } from "@/features/alarms";
import { SAMPLE_STEP_S, useSampleIndex } from "@/shared/playback";
import { useSelectionStore } from "@/shared/selection";
import type { ReplayScenario } from "@/shared/types/generated/contract";

import { readTokenColor } from "../plume/plumeColors";
import { specToScene } from "../scene/coords";
import { useStationStore } from "../store";

/** A sensor shows the "recent event" colour for this long after its alarm is raised (simulation seconds). */
const RECENT_S = 30 * 60;
const RING_RADIUS_M = 1.2;
const RING_SECONDS = 0.6;
const RING_START_SCALE = 0.6;
const HEAD_M = 0.25;
const hit = { geometry: new BoxGeometry(1, 1, 1), material: new MeshBasicMaterial({ colorWrite: false, depthWrite: false }) };
const dummy = new Object3D();
const none = () => undefined;

type Sensors = ReplayScenario["sensors"];

/** Ids of sensors whose alarm was raised within the last 30 simulated minutes before `tSeconds`. */
function recentSensors(scenario: ReplayScenario, tSeconds: number): Set<string> {
  const recent = visibleEvents(scenario, tSeconds).filter(
    (e) => tSeconds - (e.window_start_s + EVENT_WINDOW_S) <= RECENT_S,
  );
  return new Set(recent.map((e) => e.sensor_id));
}

function place(mesh: InstancedMesh, i: number, x: number, y: number, z: number, sy: number, s: number): void {
  dummy.position.set(x, y, z);
  dummy.scale.set(s, sy, s);
  dummy.updateMatrix();
  mesh.setMatrixAt(i, dummy.matrix);
}

/**
 * Methane sensors as small posts: one instanced mesh of posts and one of heads (two draw calls),
 * coloured per instance (`--text-2` normal, `--alarm-med` with a recent alarm, `--accent` when
 * selected), a flat ring under each sensor with a recent alarm (a one-shot 0.6 s scale-in, none
 * with reduced motion) and one invisible hit box per sensor that selects its tag. Colours update
 * only when the sample index or the selection changes. An alarm is always shown by the colour and
 * by the Alarms list; the ring is the marker in the scene.
 *
 * @param props - `scenario`: the loaded replay scenario (sensor positions and events).
 * @returns The markers.
 */
export function SensorMarkers({ scenario }: { scenario: ReplayScenario }): JSX.Element {
  const sensors: Sensors = scenario.sensors;
  const sampleIndex = useSampleIndex();
  const selected = useSelectionStore((s) => s.selectedTag);
  const invalidate = useThree((s) => s.invalidate);
  const posts = useRef<InstancedMesh>(null);
  const heads = useRef<InstancedMesh>(null);
  const rings = useRef<InstancedMesh>(null);
  /** Seconds since each ring appeared; -1 while the sensor has no recent alarm. */
  const ringAge = useRef<Float64Array>(new Float64Array(0));
  const ringAt = useRef<Float64Array>(new Float64Array(0));
  const animating = useRef(false);
  const shared = useMemo(
    () => ({
      post: new CylinderGeometry(0.05, 0.05, 1, 8),
      head: new BoxGeometry(HEAD_M, HEAD_M, HEAD_M),
      ring: new TorusGeometry(RING_RADIUS_M, 0.06, 6, 32).rotateX(Math.PI / 2),
      material: new MeshStandardMaterial({ roughness: 0.6 }),
      ringMaterial: new MeshBasicMaterial({ color: readTokenColor("--alarm-med"), transparent: true, opacity: 0.85 }),
      normal: readTokenColor("--text-2"),
      alarm: readTokenColor("--alarm-med"),
      accent: readTokenColor("--accent"),
    }),
    [],
  );
  useEffect(
    () => () => Object.values(shared).forEach((r) => !(r instanceof Color) && r.dispose()),
    [shared],
  );
  const recent = useMemo(() => recentSensors(scenario, sampleIndex * SAMPLE_STEP_S), [scenario, sampleIndex]);

  useLayoutEffect(() => {
    sensors.forEach((s, i) => {
      const [x, y, z] = specToScene([s.x_m, s.y_m, s.z_m]);
      if (posts.current) place(posts.current, i, x, y / 2, z, s.z_m, 1);
      if (heads.current) place(heads.current, i, x, y, z, 1, 1);
    });
    for (const mesh of [posts.current, heads.current]) if (mesh) mesh.instanceMatrix.needsUpdate = true;
    ringAge.current = new Float64Array(sensors.length).fill(-1);
    // ring x and z, kept so the frame loop allocates nothing
    ringAt.current = Float64Array.from(sensors.flatMap((s) => specToScene([s.x_m, s.y_m, s.z_m]).filter((_, k) => k !== 1)));
    invalidate();
  }, [sensors, invalidate]);

  useLayoutEffect(() => {
    sensors.forEach((s, i) => {
      const colour = s.id === selected ? shared.accent : recent.has(s.id) ? shared.alarm : shared.normal;
      posts.current?.setColorAt(i, colour);
      heads.current?.setColorAt(i, colour);
      const age = ringAge.current;
      if (!recent.has(s.id)) age[i] = -1;
      else if ((age[i] ?? -1) < 0) age[i] = useStationStore.getState().reducedMotion ? RING_SECONDS : 0;
    });
    for (const mesh of [posts.current, heads.current]) if (mesh?.instanceColor) mesh.instanceColor.needsUpdate = true;
    animating.current = true;
    invalidate(); // a paused canvas renders on demand
  }, [sensors, recent, selected, shared, invalidate]);

  useFrame((_, delta) => {
    const mesh = rings.current;
    const age = ringAge.current;
    if (!mesh || !animating.current) return;
    const at = ringAt.current;
    let running = false;
    for (let i = 0; i < age.length; i++) {
      const seconds = age[i] ?? -1;
      if (seconds >= 0) age[i] = seconds + delta;
      const f = Math.min(1, Math.max(0, (seconds + delta) / RING_SECONDS));
      const scale = seconds < 0 ? 0 : RING_START_SCALE + (1 - RING_START_SCALE) * f;
      running ||= seconds >= 0 && f < 1;
      place(mesh, i, at[2 * i] ?? 0, 0.08, at[2 * i + 1] ?? 0, scale, scale);
    }
    mesh.instanceMatrix.needsUpdate = true;
    animating.current = running;
    if (running) invalidate();
  });

  return (
    <>
      <instancedMesh key={`post${sensors.length}`} ref={posts} name="sensor-posts" args={[shared.post, shared.material, sensors.length]} raycast={none} />
      <instancedMesh key={`head${sensors.length}`} ref={heads} name="sensor-heads" args={[shared.head, shared.material, sensors.length]} raycast={none} />
      <instancedMesh key={`ring${sensors.length}`} ref={rings} name="sensor-rings" args={[shared.ring, shared.ringMaterial, sensors.length]} raycast={none} />
      {sensors.map((s) => {
        const [x, , z] = specToScene([s.x_m, s.y_m, s.z_m]);
        return (
          <mesh
            key={s.id}
            name={`${s.id}__hit`}
            geometry={hit.geometry}
            material={hit.material}
            visible={false}
            position={[x, s.z_m, z]}
            scale={[1, 2.5, 1]}
            onPointerOver={(e) => {
              e.stopPropagation();
              useSelectionStore.getState().hover(s.id);
              document.body.style.cursor = "pointer";
            }}
            onPointerOut={(e) => {
              e.stopPropagation();
              useSelectionStore.getState().hover(null);
              document.body.style.cursor = "";
            }}
            onClick={(e) => {
              e.stopPropagation();
              useSelectionStore.getState().select(s.id);
            }}
          />
        );
      })}
    </>
  );
}
