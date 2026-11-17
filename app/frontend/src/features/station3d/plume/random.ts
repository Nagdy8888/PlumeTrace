/**
 * Small deterministic random generator (mulberry32).
 *
 * @param seed - Integer seed.
 * @returns A function that returns the next number in `[0, 1)`.
 */
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Standard-normal pairs by the Box-Muller method, so particle spread is reproducible.
 *
 * @param n - Number of pairs.
 * @param seed - Seed for {@link mulberry32}.
 * @returns A Float32Array of `2 * n` values, laid out `x0, y0, x1, y1, ...`.
 */
export function gaussianPairs(n: number, seed: number): Float32Array {
  const rand = mulberry32(seed);
  const out = new Float32Array(2 * n);
  for (let i = 0; i < n; i++) {
    const r = Math.sqrt(-2 * Math.log(1 - rand()));
    const phi = 2 * Math.PI * rand();
    out[2 * i] = r * Math.cos(phi);
    out[2 * i + 1] = r * Math.sin(phi);
  }
  return out;
}
