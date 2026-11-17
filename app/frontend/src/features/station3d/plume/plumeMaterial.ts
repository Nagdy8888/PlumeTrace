import {
  NormalBlending,
  ShaderMaterial,
  Vector2,
  Vector3,
  type DataTexture,
  type IUniform,
  type Vector4,
} from "three";

import { readTokenColor } from "./plumeColors";
import { MAX_PLUME_DIST_M } from "./plumeMath";
import { PARTICLE_FRAGMENT, PARTICLE_VERTEX } from "./plumeShaders";

/** The uniforms the frame loop writes (the others are set once). */
export interface ParticleUniforms {
  uTime: IUniform<number>;
  uSource: IUniform<Vector3>;
  uToward: IUniform<Vector2>;
  uSpeed: IUniform<number>;
  uSigmaSlope: IUniform<Vector2>;
  uMix: IUniform<number>;
  uRateScale: IUniform<number>;
}

/**
 * Material of one plume particle cloud. Colour is the `--plume-tint` token (methane is invisible;
 * the cloud is a labelled visualisation). The grid uniforms share the textures of the plume field.
 *
 * @param texA - Grid of the earlier key frame.
 * @param texB - Grid of the later key frame.
 * @param rect - Grid rectangle `(x0, y0, width, height)` in spec metres.
 * @param pointSize - Base point size (1.6 on high, 2.0 on medium and low).
 * @returns The material (the caller disposes it) and its frame-loop uniforms.
 */
export function createParticleMaterial(
  texA: DataTexture,
  texB: DataTexture,
  rect: Vector4,
  pointSize: number,
): { material: ShaderMaterial; uniforms: ParticleUniforms } {
  const uniforms: ParticleUniforms = {
    uTime: { value: 0 },
    uSource: { value: new Vector3() },
    uToward: { value: new Vector2(1, 0) },
    uSpeed: { value: 3 },
    uSigmaSlope: { value: new Vector2(0.08, 0.06) },
    uMix: { value: 0 },
    uRateScale: { value: 1 },
  };
  const material = new ShaderMaterial({
    vertexShader: PARTICLE_VERTEX,
    fragmentShader: PARTICLE_FRAGMENT,
    uniforms: {
      ...uniforms,
      uMaxDist: { value: MAX_PLUME_DIST_M },
      uGridA: { value: texA },
      uGridB: { value: texB },
      uGridRect: { value: rect },
      uPointSize: { value: pointSize },
      uColor: { value: readTokenColor("--plume-tint") },
    },
    transparent: true,
    depthWrite: false,
    blending: NormalBlending,
  });
  return { material, uniforms };
}
