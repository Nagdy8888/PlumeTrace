/**
 * Which tag each overlay shows. The hover overlay is dropped when the hovered tag is the selected
 * one, so a selected item never gets a second, weaker outline or a second label.
 *
 * @param hovered - Tag under the pointer, or null.
 * @param selected - Selected tag, or null.
 * @returns The tag for the hover overlay and the tag for the selected overlay (null = hidden).
 */
export function overlayTags(
  hovered: string | null,
  selected: string | null,
): { hover: string | null; selected: string | null } {
  return { hover: hovered === selected ? null : hovered, selected };
}
