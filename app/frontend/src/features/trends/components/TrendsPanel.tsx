import { useMemo, useState, type JSX, type ReactNode } from "react";
import type uPlot from "uplot";

import { SAMPLE_STEP_S, useClockStore, useSampleIndex } from "@/shared/playback";
import { useSelectionStore } from "@/shared/selection";
import { Panel } from "@/shared/ui/Panel";
import type { ReplayScenario } from "@/shared/types/generated/contract";

import { highlightedSensors, highlightLast, methaneData, windData } from "../chartData";
import { methaneOptions, windOptions } from "../chartOptions";
import { readChartTheme } from "../chartTheme";
import { UPlotChart } from "./UPlotChart";

const currentTimeS = (): number => useClockStore.getState().tSeconds;

/** Props of {@link TrendsPanel}. */
export interface TrendsPanelProps {
  /** The active scenario, or null while nothing is loaded. */
  scenario: ReplayScenario | null;
}

function ChartBlock({ title, children }: { title: string; children: ReactNode }): JSX.Element {
  return (
    <div className="flex min-w-0 flex-1 flex-col border-border-1 not-first:border-l">
      <h3 className="flex items-baseline justify-between px-3 pt-1 text-xs text-text-2">
        <span>{title}</span>
        <span>x axis: elapsed time</span>
      </h3>
      <div className="relative min-h-0 flex-1">{children}</div>
    </div>
  );
}

function Charts({
  scenario,
  highlighted,
}: {
  scenario: ReplayScenario;
  highlighted: string[];
}): JSX.Element {
  const theme = useState(readChartTheme)[0];
  const sampleIndex = useSampleIndex();
  const methane = useMemo(
    () => highlightLast(methaneData(scenario, sampleIndex), highlighted),
    [scenario, sampleIndex, highlighted],
  );
  const wind = useMemo(() => windData(scenario, sampleIndex), [scenario, sampleIndex]);
  const ids = methane.ids.join("|");
  const methaneOpts = useMemo(
    () => methaneOptions(theme, ids.split("|"), highlighted, currentTimeS, scenario.step_s),
    [theme, ids, highlighted, scenario.step_s],
  );
  const windOpts = useMemo(
    () => windOptions(theme, currentTimeS, scenario.step_s),
    [theme, scenario.step_s],
  );
  const methaneAligned = useMemo<uPlot.AlignedData>(
    () => [methane.x, ...methane.series],
    [methane],
  );
  const windAligned = useMemo<uPlot.AlignedData>(
    () => [wind.x, wind.speed, wind.fromDeg],
    [wind],
  );

  return (
    <div className="flex h-full">
      <ChartBlock title="Methane (ppm)">
        <UPlotChart
          options={methaneOpts}
          data={methaneAligned}
          ariaLabel={`Methane trend per sensor, ${highlighted.length} highlighted`}
        />
      </ChartBlock>
      <ChartBlock title="Wind (m/s, °)">
        <UPlotChart options={windOpts} data={windAligned} ariaLabel="Wind speed and direction trend" />
      </ChartBlock>
    </div>
  );
}

/**
 * The Trends panel: methane per sensor and wind, history up to the current sample.
 *
 * Highlighted sensors (the selected one and every sensor with a visible alarm) are listed in the
 * header and drawn in the accent colour. Colours come from the design tokens at mount.
 *
 * @param props - See {@link TrendsPanelProps}.
 * @returns The Trends panel.
 */
export function TrendsPanel({ scenario }: TrendsPanelProps): JSX.Element {
  const minuteS = useClockStore((s) => Math.floor(s.tSeconds / SAMPLE_STEP_S) * SAMPLE_STEP_S);
  const selectedTag = useSelectionStore((s) => s.selectedTag);
  // A string key keeps the array identity stable between minutes, so the charts are not rebuilt.
  const key =
    scenario === null ? "" : highlightedSensors(scenario, minuteS, selectedTag).join("|");
  const shown = useMemo(() => (key === "" ? [] : key.split("|")), [key]);
  return (
    <Panel
      title="Trends"
      className="rounded-none border-0 border-t"
      actions={
        shown.length > 0 ? (
          <span className="font-mono text-xs text-text-2">{`Highlighted: ${shown.join(" ")}`}</span>
        ) : null
      }
    >
      {scenario === null ? (
        <p className="px-3 py-2 text-sm text-text-2">No scenario loaded.</p>
      ) : (
        <Charts scenario={scenario} highlighted={shown} />
      )}
    </Panel>
  );
}
