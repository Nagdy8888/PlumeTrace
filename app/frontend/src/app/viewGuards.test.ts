import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

/** Source files (not tests) under a folder, recursively. */
function sources(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const path = join(dir, e.name);
    if (e.isDirectory()) return sources(path);
    return /\.tsx?$/.test(e.name) && !/\.test\.tsx?$/.test(e.name) ? [path] : [];
  });
}

const VIEW_DIRS = [join(process.cwd(), "src", "features"), join(process.cwd(), "src", "app")];

describe("view guards (Gate 3 display rules)", () => {
  it("no view calls formatRate: a rate is shown only as an interval by a dedicated component (R1-R4)", () => {
    const offenders = VIEW_DIRS.flatMap(sources).filter((f) =>
      readFileSync(f, "utf8").includes("formatRate"),
    );
    expect(offenders).toEqual([]);
  });
  it("no view reads keyframes[].sources (simulation truth for the plume visual only)", () => {
    const offenders = VIEW_DIRS.flatMap(sources).filter((f) =>
      /keyframes|rate_kg_h|anchor_id/.test(readFileSync(f, "utf8")),
    );
    expect(offenders).toEqual([]);
  });
});
