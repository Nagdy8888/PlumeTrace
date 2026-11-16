import { useGLTF } from "@react-three/drei";
import { useMemo, type JSX, type ReactNode } from "react";
import type { Mesh, Object3D } from "three";

import { FACILITY } from "./facility";
import { StationScene } from "./StationScene";

const MODEL_URL = "/models/ks07.glb";

/**
 * The Blender-baked station (`ks07.glb`, generated from the facility spec) as an interactive
 * scene.
 *
 * Loaded without Draco (its decoder would come from a CDN) and with the bundled meshopt
 * decoder. Every mesh casts and receives the sun's shadow and has a no-op raycast: only the
 * hit proxies of {@link StationScene} are pickable.
 *
 * @param props - `children`: extra scene content that needs the node index (the camera rig).
 * @returns The station scene.
 */
export function StationModel({ children }: { children?: ReactNode }): JSX.Element {
  const { scene } = useGLTF(MODEL_URL, false, true);
  useMemo(() => {
    scene.traverse((node: Object3D) => {
      const mesh = node as Mesh;
      if (mesh.isMesh) {
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        mesh.raycast = () => undefined;
      }
    });
  }, [scene]);
  return (
    <StationScene root={scene} spec={FACILITY}>
      {children}
    </StationScene>
  );
}
