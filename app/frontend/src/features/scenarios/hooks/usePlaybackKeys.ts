import { useEffect } from "react";

import { useClockStore } from "@/shared/playback";

/** Seek step of ArrowLeft / ArrowRight in seconds; with Shift it is ten times as large. */
const SEEK_STEP_S = 60;
const SEEK_STEP_SHIFT_S = 600;

/** Targets that keep their own keys (typing, native sliders and lists). */
const OWN_KEYS = "input, select, textarea, [contenteditable]";

function handleKey(event: KeyboardEvent): void {
  const target = event.target instanceof Element ? event.target : null;
  if (event.ctrlKey || event.metaKey || event.altKey) return;
  if (target?.closest(OWN_KEYS)) return;
  const clock = useClockStore.getState();
  if (event.code === "Space") {
    // On a focused button Space already activates it; handling it here too would toggle twice.
    if (target?.closest("button")) return;
    event.preventDefault();
    if (clock.playing) clock.pause();
    else clock.play();
  } else if (event.code === "ArrowLeft" || event.code === "ArrowRight") {
    const step = event.shiftKey ? SEEK_STEP_SHIFT_S : SEEK_STEP_S;
    event.preventDefault();
    clock.seek(clock.tSeconds + (event.code === "ArrowRight" ? step : -step));
  }
}

/**
 * Keyboard control of the clock, mounted once in the shell.
 *
 * Space toggles play and pause (and does not scroll the page); ArrowLeft and ArrowRight seek by
 * 60 s, 600 s with Shift. Keys are ignored inside `input`, `select`, `textarea` and
 * `[contenteditable]` elements and with Ctrl, Alt or Meta held. The listener is removed on unmount.
 */
export function usePlaybackKeys(): void {
  useEffect(() => {
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);
}
