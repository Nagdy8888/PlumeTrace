import ReactThreeTestRenderer from "@react-three/test-renderer";
import { Group } from "three";
import { beforeEach, describe, expect, it } from "vitest";

import facility from "@/shared/facility/ks07.json";
import { useSelectionStore } from "@/shared/selection";
import type { FacilitySpec } from "@/shared/types/generated/contract";

import { StationScene } from "./StationScene";

function fakeRoot(): Group {
  const root = new Group();
  for (const e of facility.equipment) {
    const g = new Group();
    g.name = e.tag;
    g.position.set(e.position_m[0]!, e.position_m[2]!, -e.position_m[1]!);
    root.add(g);
  }
  return root;
}

describe("StationScene", () => {
  beforeEach(() => useSelectionStore.setState(useSelectionStore.getInitialState()));
  it("creates one hit proxy per equipment item and selects on click", async () => {
    const r = await ReactThreeTestRenderer.create(
      <StationScene root={fakeRoot()} spec={facility as unknown as FacilitySpec} labels={false} />,
    );
    const proxies = r.scene.findAll((n) => n.props.name?.endsWith?.("__hit"));
    expect(proxies).toHaveLength(facility.equipment.length);
    const k202 = proxies.find((p) => p.props.name === "K-202__hit");
    expect(k202).toBeDefined();
    await r.fireEvent(k202!, "onClick");
    expect(useSelectionStore.getState().selectedTag).toBe("K-202");
  });
});
