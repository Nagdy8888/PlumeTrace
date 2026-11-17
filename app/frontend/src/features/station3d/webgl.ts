/**
 * Whether this browser can create a WebGL 2 context.
 *
 * Creates a throw-away canvas, asks for a `webgl2` context and releases it again
 * (`WEBGL_lose_context`) when the extension exists. Any exception counts as "no WebGL 2".
 *
 * @returns True when a WebGL 2 context could be created.
 */
export function hasWebGL2(): boolean {
  try {
    const ctx = document.createElement("canvas").getContext("webgl2");
    ctx?.getExtension("WEBGL_lose_context")?.loseContext();
    return !!ctx;
  } catch {
    return false;
  }
}
