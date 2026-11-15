import { useEffect, useRef, type JSX } from "react";
import type uPlot from "uplot";
import "uplot/dist/uPlot.min.css";

import type { ChartOptions } from "../chartOptions";

/** Props of {@link UPlotChart}. */
export interface UPlotChartProps {
  /** uPlot options without the size; memoise them in the parent (a new object rebuilds the chart). */
  options: ChartOptions;
  /** Aligned data: x values first, then one array per series. */
  data: uPlot.AlignedData;
  /** Text alternative of the chart (the canvas itself has none). */
  ariaLabel: string;
}

/**
 * Thin wrapper around one uPlot instance; it holds no chart logic.
 *
 * The instance is created in an effect and rebuilt only when `options` changes. New `data` goes
 * through `setData(data, false)` and a redraw (the x range stays fixed). A `ResizeObserver` keeps
 * the canvas the size of its container. The instance is destroyed on unmount.
 *
 * @param props - See {@link UPlotChartProps}.
 * @returns A container that fills its nearest positioned ancestor (give the parent `relative`
 *   and a size that does not depend on the chart).
 */
export function UPlotChart({ options, data, ariaLabel }: UPlotChartProps): JSX.Element {
  const host = useRef<HTMLDivElement>(null);
  const plot = useRef<uPlot | null>(null);
  const latest = useRef(data);

  useEffect(() => {
    latest.current = data;
  });

  useEffect(() => {
    const el = host.current;
    if (el === null) return;
    let cancelled = false;
    let observer: ResizeObserver | null = null;
    // uPlot is imported on first use: it needs `matchMedia` at load time and keeps the entry chunk small.
    void import("uplot").then(({ default: UPlot }) => {
      if (cancelled) return;
      const size = (): { width: number; height: number } => ({
        width: el.clientWidth,
        height: el.clientHeight,
      });
      const u = new UPlot({ ...options, ...size() }, latest.current, el);
      plot.current = u;
      if (typeof ResizeObserver !== "undefined") {
        observer = new ResizeObserver(() => u.setSize(size()));
        observer.observe(el);
      }
    });
    return () => {
      cancelled = true;
      observer?.disconnect();
      plot.current?.destroy();
      plot.current = null;
    };
  }, [options]);

  useEffect(() => {
    plot.current?.setData(data, false);
    plot.current?.redraw();
  }, [data]);

  return (
    <div ref={host} role="img" aria-label={ariaLabel} className="absolute inset-0 overflow-hidden" />
  );
}
