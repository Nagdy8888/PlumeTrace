/** A position as `[x, y, z]` in metres. */
export type Vec3 = readonly [number, number, number];

/**
 * Convert a facility-spec position to three.js scene coordinates.
 *
 * The spec (and Blender) is Z-up: x east, y north, z up. three.js is Y-up. The glTF exporter's
 * +Y-up conversion maps a spec point `(x, y, z)` to `(x, z, -y)`, so the same mapping places
 * everything the real-time layer adds (camera, sun, plume sources) on the baked model.
 *
 * @param position - Spec position `[x, y, z]` in metres.
 * @returns The scene position `[x, z, -y]`.
 */
export function specToScene([x, y, z]: Vec3): [number, number, number] {
  return [x, z, -y];
}
