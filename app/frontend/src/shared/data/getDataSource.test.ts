import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as dataApi from "./index";
import { getDataSource, resetDataSourceForTests } from "./getDataSource";

beforeEach(() => resetDataSourceForTests());
afterEach(() => {
  vi.unstubAllEnvs();
  resetDataSourceForTests();
});

describe("getDataSource", () => {
  it("returns the live source in a normal build", async () => {
    expect((await getDataSource()).mode).toBe("live");
  });
  it("returns the replay source in replay mode and memoises it", async () => {
    vi.stubEnv("MODE", "replay");
    const first = await getDataSource();
    expect(first.mode).toBe("replay");
    expect(await getDataSource()).toBe(first);
  });
  it("does not export the source classes (they load only through getDataSource)", () => {
    expect(Object.keys(dataApi)).not.toContain("LiveSource");
    expect(Object.keys(dataApi)).not.toContain("ReplaySource");
  });
});
