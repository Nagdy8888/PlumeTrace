import { fireEvent, render } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { useClockStore } from "@/shared/playback";

import { usePlaybackKeys } from "./usePlaybackKeys";

function Harness(): null {
  usePlaybackKeys();
  return null;
}

describe("usePlaybackKeys", () => {
  beforeEach(() => {
    useClockStore.setState(useClockStore.getInitialState());
    useClockStore.getState().reset(21600);
    useClockStore.getState().seek(1000);
  });
  it("Space toggles play and does not scroll", () => {
    render(<Harness />);
    const notCancelled = fireEvent.keyDown(window, { code: "Space" });
    expect(notCancelled).toBe(false);
    expect(useClockStore.getState().playing).toBe(true);
    fireEvent.keyDown(window, { code: "Space" });
    expect(useClockStore.getState().playing).toBe(false);
  });
  it("arrows seek by one minute, Shift by ten", () => {
    render(<Harness />);
    fireEvent.keyDown(window, { code: "ArrowRight" });
    expect(useClockStore.getState().tSeconds).toBe(1060);
    fireEvent.keyDown(window, { code: "ArrowLeft", shiftKey: true });
    expect(useClockStore.getState().tSeconds).toBe(460);
  });
  it("ignores keys typed into inputs and selects", () => {
    render(
      <>
        <Harness />
        <input aria-label="field" />
        <select aria-label="pick" />
      </>,
    );
    fireEvent.keyDown(document.querySelector("input") as HTMLElement, { code: "ArrowRight", bubbles: true });
    fireEvent.keyDown(document.querySelector("select") as HTMLElement, { code: "Space", bubbles: true });
    expect(useClockStore.getState().tSeconds).toBe(1000);
    expect(useClockStore.getState().playing).toBe(false);
  });
  it("leaves Space to a focused button and ignores modified keys", () => {
    render(
      <>
        <Harness />
        <button type="button">b</button>
      </>,
    );
    fireEvent.keyDown(document.querySelector("button") as HTMLElement, { code: "Space", bubbles: true });
    fireEvent.keyDown(window, { code: "ArrowRight", ctrlKey: true });
    expect(useClockStore.getState().playing).toBe(false);
    expect(useClockStore.getState().tSeconds).toBe(1000);
  });
  it("removes the listener on unmount", () => {
    const { unmount } = render(<Harness />);
    unmount();
    fireEvent.keyDown(window, { code: "ArrowRight" });
    expect(useClockStore.getState().tSeconds).toBe(1000);
  });
});
