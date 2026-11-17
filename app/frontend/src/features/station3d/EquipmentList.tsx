import { useEffect, useMemo, useRef, type JSX } from "react";

import { useSelectionStore } from "@/shared/selection";
import { Panel } from "@/shared/ui/Panel";
import { cn } from "@/shared/lib/cn";

import { AREA_OF_TAG, AREA_ORDER, EQUIPMENT_LABEL, INSTRUMENT_LABEL, SENSOR_AREA } from "./equipmentLabels";
import { FACILITY } from "./model/facility";

interface Item {
  tag: string;
  name: string;
}

/** Equipment and methane sensors of the facility grouped by area, in the fixed area order. */
function groupByArea(): { area: string; items: Item[] }[] {
  const items = (area: string): Item[] =>
    area === SENSOR_AREA
      ? FACILITY.instruments
          .filter((i) => i.kind === "methane_point")
          .map((i) => ({ tag: i.tag, name: INSTRUMENT_LABEL[i.kind] }))
      : FACILITY.equipment
          .filter((e) => AREA_OF_TAG[e.tag] === area)
          .map((e) => ({ tag: e.tag, name: EQUIPMENT_LABEL[e.type] }));
  return AREA_ORDER.map((area) => ({ area, items: items(area) }));
}

/**
 * The Equipment panel: every equipment item and methane sensor of the station as a list of
 * buttons grouped by area. A button selects the tag (the 3D view highlights it and flies there;
 * pressing it again clears the selection) and is marked `aria-pressed` while selected. A tag
 * selected anywhere else (3D view, alarm list) is scrolled into view here. It is the keyboard and
 * screen-reader route to everything the 3D view lets you pick.
 *
 * @returns The Equipment panel.
 */
export function EquipmentList(): JSX.Element {
  const selectedTag = useSelectionStore((s) => s.selectedTag);
  const select = useSelectionStore((s) => s.select);
  const groups = useMemo(groupByArea, []);
  const body = useRef<HTMLDivElement>(null);

  useEffect(() => {
    body.current?.querySelector('[aria-pressed="true"]')?.scrollIntoView({ block: "nearest" });
  }, [selectedTag]);

  return (
    <Panel title="Equipment" className="rounded-none border-0 border-r">
      <div ref={body}>
        {groups.map(({ area, items }) => (
          <section key={area} aria-label={area}>
            <h3 className="sticky top-0 bg-surface-1 px-3 py-1 text-xs font-medium text-text-2">{area}</h3>
            <ul>
              {items.map(({ tag, name }) => (
                <li key={tag}>
                  <button
                    type="button"
                    aria-pressed={selectedTag === tag}
                    onClick={() => select(tag)}
                    className={cn(
                      // scroll-mt clears the sticky area heading; the inset focus outline is not clipped by the scroll area
                      "flex w-full scroll-mt-7 touch-manipulation items-baseline gap-2 border-l-4 border-transparent px-3 py-1.5 text-left text-sm text-text-1 hover:bg-surface-2 focus-visible:outline-offset-[-2px]",
                      selectedTag === tag && "border-accent bg-surface-3 hover:bg-surface-3",
                    )}
                  >
                    <span
                      className={cn("w-16 shrink-0 font-mono text-xs whitespace-nowrap", selectedTag === tag && "font-semibold")}
                    >
                      {tag}
                    </span>{" "}
                    <span className={cn("min-w-0 truncate", selectedTag === tag ? "text-text-1" : "text-text-2")}>{name}</span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </Panel>
  );
}
