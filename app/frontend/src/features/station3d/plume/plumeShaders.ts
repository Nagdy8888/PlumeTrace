/**
 * GLSL of the plume layer. The grid textures hold the backend `log_u8_0.1_1000ppm` bytes
 * (`NearestFilter`, so decoding never mixes two encoded bytes); the shaders decode them to ppm
 * and blend the two key frames with `uMix`. `texture2D` and `gl_FragColor` are the names three.js
 * maps to WebGL 2 for `ShaderMaterial`.
 *
 * `#include <colorspace_fragment>` is the one line added to the plan's fragment code: it makes the
 * output correct on the low tier (no post-processing, direct to screen) and a no-op inside the
 * post-processing chain, so all three tiers show the same colours.
 */

/** Shared decode functions, prefixed to every shader that samples the grid. */
export const DECODE_GLSL = /* glsl */ `
float decodePpm(float b) {
  float v = floor(b * 255.0 + 0.5);
  if (v < 0.5) return 0.0;
  return 0.1 * pow(10.0, (v - 1.0) * 4.0 / 254.0);
}
float gridPpm(sampler2D a, sampler2D b, float m, vec2 uv) {
  return mix(decodePpm(texture2D(a, uv).r), decodePpm(texture2D(b, uv).r), m);
}
`;

/** Heat-map vertex shader: pass the plane's uv. */
export const HEATMAP_VERTEX = /* glsl */ `
varying vec2 vUv;
void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }
`;

/** Heat-map fragment shader: decode, drop below 1 ppm, colour on a log ramp of five tokens. */
export const HEATMAP_FRAGMENT = /* glsl */ `
uniform sampler2D uGridA;
uniform sampler2D uGridB;
uniform float uMix;
uniform vec3 uRamp0; uniform vec3 uRamp1; uniform vec3 uRamp2; uniform vec3 uRamp3; uniform vec3 uRamp4;
varying vec2 vUv;
${DECODE_GLSL}
vec3 ramp(float t) {
  float s = clamp(t, 0.0, 1.0) * 4.0;
  if (s < 1.0) return mix(uRamp0, uRamp1, s);
  if (s < 2.0) return mix(uRamp1, uRamp2, s - 1.0);
  if (s < 3.0) return mix(uRamp2, uRamp3, s - 2.0);
  return mix(uRamp3, uRamp4, s - 3.0);
}
void main() {
  float ppm = gridPpm(uGridA, uGridB, uMix, vUv);
  if (ppm < 1.0) discard;
  float t = clamp(log(ppm) / log(10.0) / 2.0, 0.0, 1.0);
  gl_FragColor = vec4(ramp(t), clamp(0.25 + 0.5 * t, 0.0, 0.75));
  #include <colorspace_fragment>
}
`;

/** Particle vertex shader: advect along the wind, spread by the visual table, gate by the grid. */
export const PARTICLE_VERTEX = /* glsl */ `
attribute vec2 aSeed;
attribute float aOffset;
uniform float uTime;
uniform vec3 uSource;
uniform vec2 uToward;
uniform float uSpeed;
uniform float uMaxDist;
uniform vec2 uSigmaSlope;
uniform sampler2D uGridA;
uniform sampler2D uGridB;
uniform float uMix;
uniform vec4 uGridRect;
uniform float uRateScale;
uniform float uPointSize;
varying float vAlpha;
${DECODE_GLSL}
void main() {
  float life = uMaxDist / max(uSpeed, 0.5);
  float age = fract(uTime / life + aOffset);
  float d = age * uMaxDist;
  vec2 side = vec2(-uToward.y, uToward.x);
  vec3 p = uSource;
  p.xz += uToward * d + side * aSeed.x * uSigmaSlope.x * (d + 2.0);
  p.y = max(0.1, p.y + aSeed.y * uSigmaSlope.y * (d + 2.0));
  vec2 uv = vec2((p.x - uGridRect.x) / uGridRect.z, (-p.z - uGridRect.y) / uGridRect.w);
  float ppm = 0.0;
  if (uv.x >= 0.0 && uv.x <= 1.0 && uv.y >= 0.0 && uv.y <= 1.0) ppm = gridPpm(uGridA, uGridB, uMix, uv);
  float t = clamp(log(max(ppm, 0.01)) / log(10.0) / 2.0, 0.0, 1.0);
  float nearSource = 1.0 - smoothstep(5.0, 15.0, d);
  float fromGrid = ppm >= 1.0 ? 0.15 + 0.45 * t : 0.0;
  vAlpha = uRateScale * max(0.6 * nearSource, fromGrid) * (1.0 - age);
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  gl_PointSize = uPointSize * (300.0 / max(-mv.z, 1.0));
  gl_Position = projectionMatrix * mv;
}
`;

/** Particle fragment shader: a soft round sprite computed from `gl_PointCoord`. */
export const PARTICLE_FRAGMENT = /* glsl */ `
uniform vec3 uColor;
varying float vAlpha;
void main() {
  vec2 c = gl_PointCoord - 0.5;
  float r2 = dot(c, c);
  if (r2 > 0.25 || vAlpha <= 0.001) discard;
  float soft = 1.0 - r2 * 4.0;
  gl_FragColor = vec4(uColor, vAlpha * soft * soft);
  #include <colorspace_fragment>
}
`;
