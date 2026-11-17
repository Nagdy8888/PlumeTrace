import { Color } from "three";

/** Colour used only when a design token cannot be read (a test without the stylesheet). */
const TOKEN_FALLBACK = "#ffffff";

/**
 * Read a colour token from the page once; the 3D layer has no second palette.
 * `Color.setStyle` converts the sRGB hex to the linear working colour space.
 *
 * @param token - CSS custom property, for example `--ch4-0`.
 * @returns A new `Color`.
 */
export function readTokenColor(token: string): Color {
  const value = getComputedStyle(document.documentElement).getPropertyValue(token).trim();
  return new Color().setStyle(value === "" ? TOKEN_FALLBACK : value);
}

/** The five methane ramp tokens, low to high (`--ch4-0` to `--ch4-4`). */
export const RAMP_TOKENS = ["--ch4-0", "--ch4-1", "--ch4-2", "--ch4-3", "--ch4-4"] as const;
