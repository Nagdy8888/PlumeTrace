import { afterEach, describe, expect, it } from "vitest";

import { readChartTheme } from "./chartTheme";

describe("readChartTheme", () => {
  afterEach(() => {
    document.documentElement.removeAttribute("style");
  });
  it("reads the colours from the CSS custom properties", () => {
    const root = document.documentElement.style;
    root.setProperty("--accent", " #111111 ");
    root.setProperty("--text-2", "#222222");
    root.setProperty("--text-3", "#333333");
    root.setProperty("--border-1", "#444444");
    root.setProperty("--focus", "#555555");
    expect(readChartTheme()).toEqual({
      accent: "#111111",
      text2: "#222222",
      text3: "#333333",
      grid: "#444444",
      focus: "#555555",
    });
  });
  it("returns empty strings when a token is missing", () => {
    expect(readChartTheme().accent).toBe("");
  });
});
