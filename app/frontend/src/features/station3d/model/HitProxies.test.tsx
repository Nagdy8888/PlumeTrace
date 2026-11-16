import ReactThreeTestRenderer from "@react-three/test-renderer";
import { BoxGeometry, Group, Mesh } from "three";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useSelectionStore } from "@/shared/selection";

import { FACILITY } from "./facility";
import { HitProxies } from "./HitProxies";
import { buildNodeIndex } from "./nodeIndex";

/** K-202 (4 x 6 x 2 m box at x 10) and K-201 (a bare group, so a 1 m box). */
function station(): Group {
  const root = new Group();
  const k202 = new Group();
  k202.name = "K-202";
  k202.position.set(10, 0, -20);
  const body = new Mesh(new BoxGeometry(1, 1, 1));
  body.scale.set(4, 6, 2);
  body.position.set(0, 3, 0);
  k202.add(body);
  const k201 = new Group();
  k201.name = "K-201";
  k201.position.set(-5, 0, 5);
  root.add(k202, k201);
  return root;
}

async function render(): Promise<Awaited<ReturnType<typeof ReactThreeTestRenderer.create>>> {
  const index = buildNodeIndex(station(), FACILITY);
  return ReactThreeTestRenderer.create(<HitProxies index={index} />);
}

describe("HitProxies", () => {
  beforeEach(() => {
    useSelectionStore.setState(useSelectionStore.getInitialState());
    document.body.style.cursor = "";
  });
  afterEach(() => {
    document.body.style.cursor = "";
  });

  it("renders one proxy per tag present in the scene, sized and placed from the tag box", async () => {
    const r = await render();
    const proxies = r.scene.findAll((n) => n.props.name?.endsWith?.("__hit"));
    expect(proxies.map((p) => p.props.name).sort()).toEqual(["K-201__hit", "K-202__hit"]);
    const k202 = proxies.find((p) => p.props.name === "K-202__hit")!;
    expect(k202.props.position).toEqual([10, 3, -20]);
    expect(k202.props.scale).toEqual([4, 6, 2]);
    await r.unmount();
  });

  it("hover sets the hovered tag and the pointer cursor, and stops propagation", async () => {
    const r = await render();
    const k202 = r.scene.find((n) => n.props.name === "K-202__hit");
    const stopPropagation = vi.fn();
    await r.fireEvent(k202, "onPointerOver", { stopPropagation });
    expect(useSelectionStore.getState().hoveredTag).toBe("K-202");
    expect(document.body.style.cursor).toBe("pointer");
    expect(stopPropagation).toHaveBeenCalledTimes(1);
    await r.unmount();
  });

  it("pointer out clears the hovered tag, resets the cursor and stops propagation", async () => {
    const r = await render();
    const k202 = r.scene.find((n) => n.props.name === "K-202__hit");
    await r.fireEvent(k202, "onPointerOver", { stopPropagation: vi.fn() });
    const stopPropagation = vi.fn();
    await r.fireEvent(k202, "onPointerOut", { stopPropagation });
    expect(useSelectionStore.getState().hoveredTag).toBeNull();
    expect(document.body.style.cursor).toBe("");
    expect(stopPropagation).toHaveBeenCalledTimes(1);
    await r.unmount();
  });

  it("moving from one proxy to another leaves the second one hovered", async () => {
    const r = await render();
    const k202 = r.scene.find((n) => n.props.name === "K-202__hit");
    const k201 = r.scene.find((n) => n.props.name === "K-201__hit");
    await r.fireEvent(k202, "onPointerOver", { stopPropagation: vi.fn() });
    await r.fireEvent(k202, "onPointerOut", { stopPropagation: vi.fn() });
    await r.fireEvent(k201, "onPointerOver", { stopPropagation: vi.fn() });
    expect(useSelectionStore.getState().hoveredTag).toBe("K-201");
    await r.unmount();
  });

  it("a click selects the tag and stops propagation; a second click clears it", async () => {
    const r = await render();
    const k202 = r.scene.find((n) => n.props.name === "K-202__hit");
    const stopPropagation = vi.fn();
    await r.fireEvent(k202, "onClick", { stopPropagation });
    expect(useSelectionStore.getState().selectedTag).toBe("K-202");
    expect(stopPropagation).toHaveBeenCalledTimes(1);
    await r.fireEvent(k202, "onClick", { stopPropagation });
    expect(useSelectionStore.getState().selectedTag).toBeNull();
    await r.unmount();
  });
});
