import { useGLTF } from "@react-three/drei";
import { useMemo, type JSX } from "react";
import type { Mesh, Object3D } from "three";

const MODEL_URL = "/models/ks07.glb";

/**
 * The Blender-baked station (`ks07.glb`, generated from the facility spec).
 *
 * Loaded without Draco (its decoder would come from a CDN) and with the bundled meshopt
 * decoder. Every mesh casts and receives the sun's shadow.
 *
 * @returns The model as a primitive that outlives this component (`dispose={null}`).
 */
export function StationModel(): JSX.Element {
  const { scene } = useGLTF(MODEL_URL, false, true);
  useMemo(() => {
    scene.traverse((node: Object3D) => {
      const mesh = node as Mesh;
      if (mesh.isMesh) {
        mesh.castShadow = true;
        mesh.receiveShadow = true;
      }
    });
  }, [scene]);
  return <primitive object={scene} dispose={null} />;
}
