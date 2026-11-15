import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchJson } from "./fetchJson";

afterEach(() => vi.unstubAllGlobals());

describe("fetchJson", () => {
  it("sends an Accept header and returns the parsed body", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('{"a":1}', { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(fetchJson("/x")).resolves.toEqual({ a: 1 });
    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({ headers: { Accept: "application/json" } });
  });
  it("re-throws an abort unchanged", async () => {
    const abort = new DOMException("aborted", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(abort));
    await expect(fetchJson("/x")).rejects.toBe(abort);
  });
  it("maps 404 to not_found and other statuses to unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", { status: 404 })));
    await expect(fetchJson("/x")).rejects.toMatchObject({ kind: "not_found" });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", { status: 500 })));
    await expect(fetchJson("/x")).rejects.toMatchObject({ kind: "unreachable" });
  });
  it("maps a body that is not JSON to invalid", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("<html>", { status: 200 })));
    await expect(fetchJson("/x")).rejects.toMatchObject({ kind: "invalid" });
  });
});
