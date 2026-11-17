import { afterEach, describe, expect, it, vi } from "vitest";

import { hasWebGL2 } from "./webgl";

afterEach(() => vi.restoreAllMocks());

describe("hasWebGL2", () => {
  it("is false when the context cannot be created", () => {
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
    expect(hasWebGL2()).toBe(false);
  });
  it("is false when getContext throws", () => {
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(hasWebGL2()).toBe(false);
  });
});
