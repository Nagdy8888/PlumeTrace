import { describe, expect, it } from "vitest";

import vercel from "../../vercel.json";

const headersFor = (source: string): Map<string, string> => {
  const block = vercel.headers.find((h) => h.source === source);
  if (!block) throw new Error(`no headers block for ${source}`);
  return new Map(block.headers.map((h) => [h.key, h.value]));
};

describe("vercel.json security headers", () => {
  const h = headersFor("/(.*)");

  it("sets a strict content security policy", () => {
    const csp = h.get("Content-Security-Policy") ?? "";
    for (const part of [
      "default-src 'self'",
      "script-src 'self' 'wasm-unsafe-eval'",
      "worker-src 'self' blob:",
      "connect-src 'self'",
      "img-src 'self' data: blob:",
      "style-src 'self' 'unsafe-inline'",
      "font-src 'self'",
      "frame-ancestors 'none'",
    ]) {
      expect(csp).toContain(part);
    }
  });

  it("sets the other security headers", () => {
    expect(h.get("X-Content-Type-Options")).toBe("nosniff");
    expect(h.get("Referrer-Policy")).toBe("strict-origin-when-cross-origin");
    expect(h.get("Permissions-Policy")).toBe("camera=(), microphone=(), geolocation=()");
    expect(h.get("Strict-Transport-Security")).toBe("max-age=63072000; includeSubDomains");
  });

  it("rewrites unknown paths to the SPA entry", () => {
    expect(vercel.rewrites).toEqual([{ source: "/(.*)", destination: "/index.html" }]);
  });
});
