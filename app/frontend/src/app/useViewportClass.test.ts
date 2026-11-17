import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useViewportClass } from "./useViewportClass";

function mockMedia(matches: Record<string, boolean>, width: number): void {
  vi.stubGlobal("innerWidth", width);
  vi.stubGlobal("matchMedia", (q: string) => ({
    matches: matches[q] ?? false,
    media: q,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  }));
}

afterEach(() => vi.unstubAllGlobals());

describe("useViewportClass", () => {
  it("treats narrow screens as mobile", () => {
    mockMedia({ "(max-width: 767px)": true }, 390);
    expect(renderHook(() => useViewportClass()).result.current).toBe("mobile");
  });
  it("treats a coarse pointer under 1024 px as mobile", () => {
    mockMedia({ "(pointer: coarse)": true }, 900);
    expect(renderHook(() => useViewportClass()).result.current).toBe("mobile");
  });
  it("keeps large touch screens on desktop", () => {
    mockMedia({ "(pointer: coarse)": true }, 1366);
    expect(renderHook(() => useViewportClass()).result.current).toBe("desktop");
  });
});
