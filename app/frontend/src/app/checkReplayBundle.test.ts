import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { afterEach, beforeEach, describe, expect, it } from "vitest";

const SCRIPT = join(process.cwd(), "scripts", "check-replay-bundle.mjs");

function run(dir: string): { status: number | null; out: string } {
  const r = spawnSync(process.execPath, [SCRIPT, dir], { encoding: "utf8" });
  return { status: r.status, out: `${r.stdout}${r.stderr}` };
}

describe("check-replay-bundle", () => {
  let dir: string;
  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), "bundle-"));
  });
  afterEach(() => {
    rmSync(dir, { recursive: true, force: true });
  });

  it("passes a replay bundle: ReplaySource present, no live API path", () => {
    writeFileSync(join(dir, "ReplaySource-x.js"), 'fetch("/replay/scenarios/index.json")');
    const r = run(dir);
    expect(r.status).toBe(0);
    expect(r.out).toContain("replay bundle OK");
  });
  it("negative control: a non-replay build (live API path) fails", () => {
    writeFileSync(join(dir, "LiveSource-x.js"), 'fetch("/api/scenarios")');
    writeFileSync(join(dir, "index-x.js"), "/replay/scenarios");
    const r = run(dir);
    expect(r.status).toBe(1);
    expect(r.out).toContain("live API code in replay bundle");
  });
  it("is not vacuous: a bundle without ReplaySource fails", () => {
    writeFileSync(join(dir, "index-x.js"), "console.log(1)");
    const r = run(dir);
    expect(r.status).toBe(1);
    expect(r.out).toContain("no ReplaySource");
  });
  it("ignores the R3F documentation URL in its error text", () => {
    writeFileSync(
      join(dir, "StationCanvas-x.js"),
      '"See: https://docs.pmnd.rs/react-three-fiber/api/objects#using-3rd-party-objects-declaratively"',
    );
    writeFileSync(join(dir, "ReplaySource-x.js"), 'fetch("/replay/scenarios/index.json")');
    const r = run(dir);
    expect(r.status).toBe(0);
    expect(r.out).toContain("replay bundle OK");
  });
  it("negative control: a live API path next to the R3F URL still fails", () => {
    writeFileSync(
      join(dir, "StationCanvas-x.js"),
      '"https://docs.pmnd.rs/react-three-fiber/api/objects";fetch("/api/scenarios")',
    );
    writeFileSync(join(dir, "ReplaySource-x.js"), 'fetch("/replay/scenarios/index.json")');
    const r = run(dir);
    expect(r.status).toBe(1);
    expect(r.out).toContain("live API code in replay bundle: StationCanvas-x.js");
  });
  it("fails when the folder is missing", () => {
    expect(run(join(dir, "missing")).status).toBe(1);
  });
});
