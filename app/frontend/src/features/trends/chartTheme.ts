/** Colours of the trend charts, read from the design tokens (never typed as hex in code). */
export interface ChartTheme {
  /** `--accent`: highlighted sensor lines. */
  accent: string;
  /** `--text-2`: axis text and the wind speed line. */
  text2: string;
  /** `--text-3`: quiet lines and points (graphics only, never text). */
  text3: string;
  /** `--border-1`: grid and tick lines. */
  grid: string;
  /** `--focus`: the cursor line at the current time. */
  focus: string;
}

const readVar = (style: CSSStyleDeclaration, name: string): string =>
  style.getPropertyValue(name).trim();

/**
 * Read the chart colours from the CSS custom properties of `:root`.
 *
 * Call it once at mount: canvas drawing cannot use `var()`, so the resolved colour strings are
 * passed to uPlot.
 *
 * @returns The resolved colours (empty strings when a token is missing).
 */
export function readChartTheme(): ChartTheme {
  const style = getComputedStyle(document.documentElement);
  return {
    accent: readVar(style, "--accent"),
    text2: readVar(style, "--text-2"),
    text3: readVar(style, "--text-3"),
    grid: readVar(style, "--border-1"),
    focus: readVar(style, "--focus"),
  };
}
