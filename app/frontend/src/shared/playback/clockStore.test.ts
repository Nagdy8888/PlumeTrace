import { beforeEach, describe, expect, it } from "vitest";

import { useClockStore } from "./clockStore";

describe("clockStore", () => {
  beforeEach(() => useClockStore.setState(useClockStore.getInitialState()));

  it("advances by real time times speed and stops at the end", () => {
    const c = useClockStore.getState();
    c.reset(600);
    c.setSpeed(60);
    c.play();
    useClockStore.getState().tick(0.5);
    expect(useClockStore.getState().tSeconds).toBe(30);
    for (let i = 0; i < 40; i += 1) useClockStore.getState().tick(0.5);
    expect(useClockStore.getState().tSeconds).toBe(600);
    expect(useClockStore.getState().playing).toBe(false);
  });
  it("ignores long gaps (sleeping tab) and clamps seeks", () => {
    const c = useClockStore.getState();
    c.reset(600);
    c.play();
    useClockStore.getState().tick(5);
    expect(useClockStore.getState().tSeconds).toBe(0);
    useClockStore.getState().seek(9999);
    expect(useClockStore.getState().tSeconds).toBe(600);
  });
  it("does not play an empty timeline", () => {
    useClockStore.getState().play();
    expect(useClockStore.getState().playing).toBe(false);
  });
});
