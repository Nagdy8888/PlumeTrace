import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join, relative, sep } from "node:path";

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

/** POSIX path relative to app/frontend, so the allow-list also works on Windows. */
const rel = (f: string): string => relative(process.cwd(), f).split(sep).join("/");
const TRUTH_NAMES = /keyframes|rate_kg_h|anchor_id/;
const PLUME_DIR = "src/features/station3d/plume/";
/** The only files that may read replay keyframes[].sources: plume-visual code (Owner decisions log 2026-11-16 P4 T9). */
const PLUME_TRUTH_READERS = new Set([
  "src/features/station3d/plume/plumeFrames.ts",
  "src/features/station3d/plume/PlumeParticles.tsx",
]);
/** Files that may import the readers; text, DOM, aria and log sinks are checked in these. */
const PLUME_TRUTH_SCOPE = new Set([
  ...PLUME_TRUTH_READERS,
  "src/features/station3d/plume/usePlumeField.ts",
  "src/features/station3d/plume/PlumeLayer.tsx",
]);
const viewSources = (): string[] => VIEW_DIRS.flatMap(sources);
const read = (path: string): string => readFileSync(join(process.cwd(), path), "utf8");

describe("view guards (Gate 3 display rules)", () => {
  it("no view calls formatRate: a rate is shown only as an interval by a dedicated component (R1-R4)", () => {
    const offenders = VIEW_DIRS.flatMap(sources).filter((f) =>
      readFileSync(f, "utf8").includes("formatRate"),
    );
    expect(offenders).toEqual([]);
  });
  it("no view reads keyframes[].sources (simulation truth for the plume visual only)", () => {
    const offenders = VIEW_DIRS.flatMap(sources)
      // allow-list: Owner decisions log 2026-11-16 P4 T9
      .filter((f) => !PLUME_TRUTH_READERS.has(rel(f)))
      .filter((f) => TRUTH_NAMES.test(readFileSync(f, "utf8")));
    expect(offenders).toEqual([]);
  });
  it("plume truth allow-list is exact: every entry is a plume file that really reads those names", () => {
    for (const path of PLUME_TRUTH_READERS) {
      expect(path.startsWith(PLUME_DIR)).toBe(true);
      expect(existsSync(join(process.cwd(), path))).toBe(true);
      expect(TRUTH_NAMES.test(read(path))).toBe(true);
    }
  });
  it("nothing outside the plume truth scope imports the readers", () => {
    const imports = /["'][^"']*\b(plumeFrames|usePlumeField|PlumeParticles)["']/;
    const offenders = viewSources()
      .filter((f) => !PLUME_TRUTH_SCOPE.has(rel(f)))
      .filter((f) => imports.test(readFileSync(f, "utf8")));
    expect(offenders.map(rel)).toEqual([]);
  });
  it("plume truth scope has no text, DOM or aria sink", () => {
    const sink = /<Html|<Text\b|aria-|title=|alt=|label=|textContent|innerText|innerHTML|dangerouslySetInnerHTML|data-[a-z]|document\./;
    for (const path of PLUME_TRUTH_SCOPE) expect({ path, hit: sink.exec(read(path))?.[0] }).toEqual({ path, hit: undefined });
  });
  it("plume truth scope logs only fixed string literals", () => {
    for (const path of PLUME_TRUTH_SCOPE) {
      const text = read(path);
      const calls = text.match(/console\.\w+\(/g)?.length ?? 0;
      const fixed = text.match(/console\.\w+\(\s*"[^"$\\]*"\s*\)/g)?.length ?? 0;
      expect({ path, calls }).toEqual({ path, calls: fixed });
    }
  });
});
