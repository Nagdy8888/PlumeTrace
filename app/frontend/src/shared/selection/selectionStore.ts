import { create } from "zustand";

/** State and actions of the equipment selection (shared by the 3D scene and the panels). */
export interface SelectionState {
  /** Tag of the selected equipment, for example `K-202`, or null. */
  selectedTag: string | null;
  /** Tag of the equipment under the pointer, or null. */
  hoveredTag: string | null;
  /** Select a tag; selecting the already-selected tag (or null) clears the selection. */
  select: (tag: string | null) => void;
  /** Set or clear the hovered tag. */
  hover: (tag: string | null) => void;
}

/** Which equipment tag is selected or hovered. Business-neutral: it stores tags only. */
export const useSelectionStore = create<SelectionState>()((set) => ({
  selectedTag: null,
  hoveredTag: null,
  select: (tag) => set((s) => ({ selectedTag: s.selectedTag === tag ? null : tag })),
  hover: (tag) => set({ hoveredTag: tag }),
}));
