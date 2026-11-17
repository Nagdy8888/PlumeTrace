import type { JSX } from "react";

import { AlarmList } from "@/features/alarms";
import { EquipmentList } from "@/features/station3d";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/ui/tabs";
import type { ReplayScenario } from "@/shared/types/generated/contract";

/** Props of {@link LeftColumn}. */
export interface LeftColumnProps {
  /** The active scenario, or null while nothing is loaded. */
  scenario: ReplayScenario | null;
}

const TRIGGER =
  "h-full flex-none touch-manipulation rounded-none border-0 border-b-2 border-transparent px-4 text-sm text-text-2 transition-none hover:text-text-1 data-[state=active]:border-accent data-[state=active]:bg-transparent data-[state=active]:text-text-1";

/**
 * The left column: two tabs, `Alarms` (the alarm list) and `Equipment` (every item the 3D view
 * can select). The column is the target of the skip link (`#alarms-panel`). The tabs follow the
 * WAI-ARIA tabs pattern (Radix): arrow keys move between them, Tab enters the panel below.
 * Only the active tab's panel is mounted.
 *
 * @param props - See {@link LeftColumnProps}.
 * @returns The tabbed column.
 */
export function LeftColumn({ scenario }: LeftColumnProps): JSX.Element {
  return (
    <div id="alarms-panel" tabIndex={-1} className="flex min-h-0 flex-col border-r border-border-1">
      <Tabs defaultValue="alarms" className="min-h-0 flex-1 gap-0">
        <TabsList variant="line" className="h-8 w-full shrink-0 justify-start gap-0 border-b border-border-1 bg-surface-1 p-0">
          <TabsTrigger value="alarms" className={TRIGGER}>
            Alarms
          </TabsTrigger>
          <TabsTrigger value="equipment" className={TRIGGER}>
            Equipment
          </TabsTrigger>
        </TabsList>
        <TabsContent value="alarms" className="grid min-h-0 grid-rows-[minmax(0,1fr)]">
          <AlarmList scenario={scenario} />
        </TabsContent>
        <TabsContent value="equipment" className="grid min-h-0 grid-rows-[minmax(0,1fr)]">
          <EquipmentList />
        </TabsContent>
      </Tabs>
    </div>
  );
}
