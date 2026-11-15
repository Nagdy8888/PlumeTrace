import { afterEach, describe, expect, it, vi } from "vitest";

import { makeReplay } from "@/shared/testing/replayFixture";

import { ReplaySource } from "./ReplaySource";

function respond(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

afterEach(() => vi.unstubAllGlobals());

describe("ReplaySource", () => {
  it("loads a scenario file from /replay", async () => {
    const fetchMock = vi.fn().mockResolvedValue(respond(200, makeReplay()));
    vi.stubGlobal("fetch", fetchMock);
    const s = await new ReplaySource().loadScenario("s1_rod_packing");
    expect(s.title).toBe("Test scenario");
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/replay/scenarios/s1_rod_packing.json");
  });
  it("rejects ids that are not scenario ids without fetching", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    await expect(new ReplaySource().loadScenario("../secrets")).rejects.toMatchObject({ kind: "not_found" });
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("maps 404 to not_found", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(respond(404, {})));
    await expect(new ReplaySource().loadScenario("s9_missing")).rejects.toMatchObject({ kind: "not_found" });
  });
});
