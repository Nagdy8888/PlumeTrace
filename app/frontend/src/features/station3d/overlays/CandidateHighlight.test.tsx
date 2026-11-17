import ReactThreeTestRenderer from "@react-three/test-renderer";
import { MeshStandardMaterial, Object3D, type Mesh } from "three";
import { describe, expect, it } from "vitest";

import { NodeIndexContext, type NodeIndex } from "../model/nodeIndex";
import { CandidateHighlight, type Candidate } from "./CandidateHighlight";

function fakeIndex(): NodeIndex {
  const place = (x: number, y: number, z: number): Object3D => {
    const o = new Object3D();
    o.position.set(x, y, z);
    o.updateMatrixWorld(true);
    return o;
  };
  const nodes = new Map([
    ["VS-250.tip", place(85, 12, -115)],
    ["K-202.packing", place(60, 1, -90)],
  ]);
  return { get: (name) => nodes.get(name), equipmentTags: [], missing: [] };
}

async function render(candidates: Candidate[]): Promise<Awaited<ReturnType<typeof ReactThreeTestRenderer.create>>> {
  return ReactThreeTestRenderer.create(
    <NodeIndexContext.Provider value={fakeIndex()}>
      <CandidateHighlight candidates={candidates} labels={false} />
    </NodeIndexContext.Provider>,
  );
}

const spheres = (r: Awaited<ReturnType<typeof render>>): Mesh[] =>
  r.scene.findAll((n) => n.props.name?.startsWith?.("candidate-")).map((n) => n.instance as Mesh);

describe("CandidateHighlight", () => {
  it("draws one sphere per known candidate with a glow that follows the probability", async () => {
    const r = await render([
      { anchorId: "VS-250.tip", label: "VS-250 tip", probability: 0.87 },
      { anchorId: "K-202.packing", label: "K-202 packing", probability: 0.1 },
    ]);
    const found = spheres(r);
    expect(found).toHaveLength(2);
    const glow = found.map((m) => (m.material as MeshStandardMaterial).emissiveIntensity);
    expect(glow[0]).toBeCloseTo(3.61, 6);
    expect(glow[1]).toBeCloseTo(1.3, 6);
    expect(found[0]!.position.toArray()).toEqual([85, 12, -115]);
    expect((found[0]!.material as MeshStandardMaterial).toneMapped).toBe(false);
    await r.unmount();
  });

  it("skips an unknown anchor without throwing", async () => {
    const r = await render([
      { anchorId: "XX-999.tip", label: "nowhere", probability: 0.5 },
      { anchorId: "VS-250.tip", label: "VS-250 tip", probability: 0.5 },
    ]);
    expect(spheres(r)).toHaveLength(1);
    await r.unmount();
  });

  it("draws nothing for an empty list", async () => {
    const r = await render([]);
    expect(spheres(r)).toHaveLength(0);
    await r.unmount();
  });
});
