import type { Page } from "@playwright/test";

/** Per-frame render statistics of one displayed frame (every render pass of the frame summed). */
export interface FrameStats {
  /** Sum of `gl.info.render.calls` over all `renderer.render` calls of the frame (shadow, scene, post). */
  calls: number;
  /** Sum of `gl.info.render.triangles` over the same calls. */
  triangles: number;
  /** Raw WebGL draw calls counted at the context (cross-check of `calls`). */
  glDraws: number;
}

/** Summary of {@link sampleFrames}: the worst frame and the median over frames that rendered. */
export interface FrameSummary {
  /** Frames that rendered at least one draw call. */
  frames: number;
  /** Highest per-frame sum of draw calls. */
  maxCalls: number;
  /** Median per-frame sum of draw calls. */
  medianCalls: number;
  /** Highest per-frame raw GL draw count. */
  maxGlDraws: number;
  /** Median triangles per frame. */
  medianTriangles: number;
  /** Highest triangles per frame. */
  maxTriangles: number;
  /** Textures the renderer reports (`gl.info.memory.textures`). */
  textures: number;
  /** Geometries the renderer reports (`gl.info.memory.geometries`). */
  geometries: number;
  /** Bytes of live 2D textures allocated through `texStorage2D` (incl. mip levels, shadow map, post targets). */
  textureBytes: number;
  /** Formats seen in `texStorage2D` that the byte table does not know (their bytes are not in `textureBytes`). */
  unmappedFormats: number[];
}

/**
 * Install, before the page loads, the hooks that make the three.js renderer measurable from outside:
 * a `__THREE_DEVTOOLS__` listener that captures the `WebGLRenderer` (with `info.autoReset` off, so
 * the per-frame sum over all render passes is ours to read and reset) and counters on the WebGL 2
 * context (draw calls and live `texStorage2D` bytes). Nothing in the app is changed.
 *
 * @param page - The Playwright page; call before `page.goto`.
 */
export async function installGpuProbe(page: Page): Promise<void> {
  await page.addInitScript(() => {
    interface Info {
      autoReset: boolean;
      render: { calls: number; triangles: number };
      memory: { textures: number; geometries: number };
      reset: () => void;
    }
    interface Probe {
      info: Info | null;
      glDraws: number;
      frames: { calls: number; triangles: number; glDraws: number }[];
      sizes: Map<unknown, number>;
      unmapped: Set<number>;
    }
    const probe: Probe = { info: null, glDraws: 0, frames: [], sizes: new Map(), unmapped: new Set() };
    (window as unknown as { __probe: Probe }).__probe = probe;

    const devtools = new EventTarget();
    devtools.addEventListener("observe", (event) => {
      const detail = (event as CustomEvent<{ isWebGLRenderer?: boolean; info: Info }>).detail;
      if (detail.isWebGLRenderer === true) {
        probe.info = detail.info;
        detail.info.autoReset = false;
      }
    });
    (window as unknown as { __THREE_DEVTOOLS__: EventTarget }).__THREE_DEVTOOLS__ = devtools;

    const proto = WebGL2RenderingContext.prototype;
    for (const name of ["drawElements", "drawArrays", "drawElementsInstanced", "drawArraysInstanced", "drawRangeElements"] as const) {
      const original = proto[name] as (...args: unknown[]) => void;
      (proto as unknown as Record<string, unknown>)[name] = function (this: WebGL2RenderingContext, ...args: unknown[]) {
        probe.glDraws += 1;
        return original.apply(this, args);
      };
    }

    // Bytes per texel of the internal formats three.js uses with `texStorage2D`.
    const BYTES: Record<number, number> = {
      0x8058: 4, 0x8c43: 4, 0x881a: 8, 0x8814: 16, 0x8229: 1, 0x822b: 2, 0x822d: 2, 0x822e: 4, 0x822f: 4,
      0x8051: 3, 0x8c3a: 4, 0x81a5: 2, 0x81a6: 4, 0x8cac: 4, 0x88f0: 4, 0x8059: 4, 0x8d48: 1,
    };
    const bound = new Map<number, unknown>();
    const bind = proto.bindTexture;
    proto.bindTexture = function (this: WebGL2RenderingContext, target: number, texture: WebGLTexture | null) {
      bound.set(target, texture);
      return bind.call(this, target, texture);
    };
    const storage = proto.texStorage2D;
    proto.texStorage2D = function (this: WebGL2RenderingContext, target: number, levels: number, format: number, width: number, height: number) {
      const bytesPerTexel = BYTES[format];
      if (bytesPerTexel === undefined) probe.unmapped.add(format);
      let texels = 0;
      for (let l = 0; l < levels; l += 1) texels += Math.max(1, width >> l) * Math.max(1, height >> l);
      probe.sizes.set(bound.get(target), texels * (bytesPerTexel ?? 0));
      return storage.call(this, target, levels, format, width, height);
    };
    const del = proto.deleteTexture;
    proto.deleteTexture = function (this: WebGL2RenderingContext, texture: WebGLTexture | null) {
      probe.sizes.delete(texture);
      return del.call(this, texture);
    };
  });
}

/**
 * Sample `count` consecutive animation frames and summarise the draw calls and triangles per frame.
 * Each sample is what the renderer accumulated since the previous sample, so a frame with several
 * render passes (shadow map, scene, bloom, SMAA) is one sample, summed. Needs {@link installGpuProbe}.
 *
 * @param page - The Playwright page showing the playing scene.
 * @param count - Number of animation frames to sample.
 * @returns The summary; `frames` is 0 when no renderer was captured.
 */
export async function sampleFrames(page: Page, count: number): Promise<FrameSummary> {
  return page.evaluate(
    (n) =>
      new Promise<FrameSummary>((resolve) => {
        interface Probe {
          info: {
            render: { calls: number; triangles: number };
            memory: { textures: number; geometries: number };
            reset: () => void;
          } | null;
          glDraws: number;
          sizes: Map<unknown, number>;
          unmapped: Set<number>;
        }
        const probe = (window as unknown as { __probe: Probe }).__probe;
        const samples: { calls: number; triangles: number; glDraws: number }[] = [];
        let first = true;
        let ticks = 0;
        const tick = (): void => {
          const info = probe.info;
          ticks += 1;
          if (info !== null) {
            // the first tick only clears what accumulated before sampling started
            if (!first) samples.push({ calls: info.render.calls, triangles: info.render.triangles, glDraws: probe.glDraws });
            first = false;
            info.reset();
            probe.glDraws = 0;
          }
          // no renderer after n + 600 frames means the page has no WebGL scene: resolve with 0 frames
          if (samples.length < n && ticks < n + 600) {
            requestAnimationFrame(tick);
            return;
          }
          const rendered = samples.filter((s) => s.calls > 0);
          const sortedCalls = rendered.map((s) => s.calls).sort((a, b) => a - b);
          const sortedTris = rendered.map((s) => s.triangles).sort((a, b) => a - b);
          const mid = (v: number[]): number => v[Math.floor(v.length / 2)] ?? 0;
          resolve({
            frames: rendered.length,
            maxCalls: Math.max(0, ...sortedCalls),
            medianCalls: mid(sortedCalls),
            maxGlDraws: Math.max(0, ...rendered.map((s) => s.glDraws)),
            medianTriangles: mid(sortedTris),
            maxTriangles: Math.max(0, ...sortedTris),
            textures: info?.memory.textures ?? 0,
            geometries: info?.memory.geometries ?? 0,
            textureBytes: [...probe.sizes.values()].reduce((a, b) => a + b, 0),
            unmappedFormats: [...probe.unmapped],
          });
        };
        requestAnimationFrame(tick);
      }),
    count,
  );
}

/**
 * Name the graphics hardware (the unmasked WebGL renderer string) and the Chromium version that
 * ran a WebGL test. It cannot tell the headless shell from the full Chromium: the `Desktop Chrome`
 * device sets a plain user agent and `executablePath()` always names the full build. Which binary
 * ran is read from the process list (see the phase evidence file).
 *
 * @param page - The Playwright page (a throw-away canvas is created in it).
 * @param version - `browser.version()`.
 * @returns Strings for logs and the evidence file.
 */
export async function describeGpu(page: Page, version: string): Promise<string> {
  const gpu = await page.evaluate(() => {
    const gl = document.createElement("canvas").getContext("webgl2");
    const ext = gl?.getExtension("WEBGL_debug_renderer_info");
    return gl !== null && ext != null ? String(gl.getParameter(ext.UNMASKED_RENDERER_WEBGL)) : "unknown (no WebGL 2)";
  });
  return `GPU: ${gpu}; Chromium ${version}`;
}
