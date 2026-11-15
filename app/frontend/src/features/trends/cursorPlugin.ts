import type uPlot from "uplot";

/**
 * uPlot plugin that draws a 1 px vertical line at the current simulation time.
 *
 * The line sits on the start of the current sample (the chart shows history up to that sample),
 * and never past the last x value. It runs in `hooks.draw`, so it is repainted with every chart
 * redraw (once per simulated minute), not per animation frame.
 *
 * @param color - Line colour (the resolved `--focus` token).
 * @param getTimeS - Returns the current simulation time in seconds.
 * @param stepS - Length of one sample in seconds.
 * @returns The plugin.
 */
export function cursorPlugin(color: string, getTimeS: () => number, stepS: number): uPlot.Plugin {
  return {
    hooks: {
      draw: (u) => {
        const xs = u.data[0];
        const last = xs?.[xs.length - 1];
        if (last === undefined) return;
        const t = Math.min(Math.floor(getTimeS() / stepS) * stepS, last);
        const x = Math.round(u.valToPos(t, "x", true));
        const { ctx, bbox } = u;
        ctx.save();
        ctx.strokeStyle = color;
        ctx.lineWidth = Math.max(1, Math.round(devicePixelRatio));
        ctx.beginPath();
        ctx.moveTo(x, bbox.top);
        ctx.lineTo(x, bbox.top + bbox.height);
        ctx.stroke();
        ctx.restore();
      },
    },
  };
}
