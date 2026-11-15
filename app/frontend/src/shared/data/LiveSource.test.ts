import { afterEach, describe, expect, it, vi } from "vitest";

import { LiveSource } from "./LiveSource";

afterEach(() => vi.unstubAllGlobals());

describe("LiveSource", () => {
  it("reports an unreachable backend when fetch fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(new LiveSource().listScenarios()).rejects.toMatchObject({ kind: "unreachable" });
  });
  it("treats a proxy 502 as unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", { status: 502 })));
    await expect(new LiveSource().listScenarios()).rejects.toMatchObject({ kind: "unreachable" });
  });
  it("calls the relative API path", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([{ id: "s1_rod_packing", title: "A", duration_h: 6, is_mvp: true }]), {
        status: 200,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    await new LiveSource().listScenarios();
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/scenarios");
  });
});
