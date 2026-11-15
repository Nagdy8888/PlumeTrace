import { Pause, Play } from "lucide-react";
import type { JSX } from "react";

import { formatClock, formatUtc } from "@/shared/lib/format";
import { SAMPLE_STEP_S, SPEEDS, useClockStore } from "@/shared/playback";
import { Button } from "@/shared/ui/button";

/** Props of {@link PlaybackBar}. */
export interface PlaybackBarProps {
  /** Whether a scenario is loaded; every control is disabled otherwise. */
  ready: boolean;
  /** Scenario start (ISO-8601 UTC) for the zone-labelled time of day. */
  simStartUtc: string;
  /** Clock times (seconds) at which alarms were raised, drawn as ticks under the track. */
  eventTimesS: number[];
}

/** Half the width of the native slider thumb: ticks are inset by it to line up with the thumb centre. */
const THUMB_INSET = "0.5rem";

function SpeedButtons({ ready }: { ready: boolean }): JSX.Element {
  const speed = useClockStore((s) => s.speed);
  return (
    <div role="radiogroup" aria-label="Playback speed" className="flex gap-1">
      {SPEEDS.map((value) => (
        <Button
          key={value}
          type="button"
          role="radio"
          aria-checked={speed === value}
          disabled={!ready}
          variant={speed === value ? "outline" : "ghost"}
          size="xs"
          className="font-mono"
          onClick={() => useClockStore.getState().setSpeed(value)}
        >
          {`${value}×`}
        </Button>
      ))}
    </div>
  );
}

function Scrubber({ ready, eventTimesS }: Pick<PlaybackBarProps, "ready" | "eventTimesS">): JSX.Element {
  const durationS = useClockStore((s) => s.durationS);
  // Whole minutes only: the slider step is one sample and the thumb needs no finer resolution.
  const minuteS = useClockStore((s) => Math.floor(s.tSeconds / SAMPLE_STEP_S) * SAMPLE_STEP_S);
  return (
    <div className="relative flex min-w-0 flex-1 flex-col justify-center">
      <input
        type="range"
        aria-label="Simulation time"
        aria-valuetext={`Elapsed ${formatClock(minuteS)}`}
        min={0}
        max={durationS}
        step={SAMPLE_STEP_S}
        value={minuteS}
        disabled={!ready}
        onChange={(e) => useClockStore.getState().seek(Number(e.target.value))}
        className="h-4 w-full accent-accent disabled:opacity-50"
      />
      <div
        aria-hidden="true"
        className="relative h-1"
        style={{ marginInline: THUMB_INSET }}
      >
        {durationS > 0
          ? eventTimesS.map((t) => (
              <span
                key={t}
                className="absolute top-0 h-1 w-0.5 -translate-x-1/2 bg-alarm-med"
                style={{ left: `${(t / durationS) * 100}%` }}
              />
            ))
          : null}
      </div>
    </div>
  );
}

function TimeReadout({ simStartUtc }: { simStartUtc: string }): JSX.Element {
  const seconds = useClockStore((s) => Math.floor(s.tSeconds));
  return (
    <span className="shrink-0 font-mono text-xs text-text-1">
      <span className="font-sans text-text-2">Elapsed </span>
      {formatClock(seconds)}
      {simStartUtc === "" ? null : (
        <span className="text-text-2">{` · ${formatUtc(simStartUtc, seconds)}`}</span>
      )}
    </span>
  );
}

/**
 * The playback bar: play and pause, speed, scrubber with alarm ticks, and the time readout.
 *
 * The readout shows elapsed time (`Elapsed +02:01`) and the UTC time of day (`08:01:00 UTC`); a
 * time is never shown without its label. Everything is disabled until a scenario is ready.
 *
 * @param props - See {@link PlaybackBarProps}.
 * @returns The bar.
 */
export function PlaybackBar({ ready, simStartUtc, eventTimesS }: PlaybackBarProps): JSX.Element {
  const playing = useClockStore((s) => s.playing);
  return (
    <div className="flex h-11 items-center gap-4 border-t border-border-1 bg-surface-1 px-3">
      <Button
        type="button"
        variant="outline"
        size="icon-sm"
        aria-label={playing ? "Pause" : "Play"}
        disabled={!ready}
        onClick={() => {
          const clock = useClockStore.getState();
          if (clock.playing) clock.pause();
          else clock.play();
        }}
      >
        {playing ? <Pause size={16} /> : <Play size={16} />}
      </Button>
      <SpeedButtons ready={ready} />
      <Scrubber ready={ready} eventTimesS={eventTimesS} />
      <TimeReadout simStartUtc={simStartUtc} />
    </div>
  );
}
