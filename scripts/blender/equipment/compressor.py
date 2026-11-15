"""Reciprocating compressor skid K-202 (geometry table of the Phase 4 Task 5 spike)."""

from typing import Any

from layout import to_local
from parts import mesh_ops
from parts.flange import flange
from parts.handrail import handrail
from parts.skid import skid
from parts.vessel import horizontal_vessel
from scene_setup import BuildContext
from spec_loader import anchors_of

CYL_X_M = (-2.5, -0.5)
CYL_Y_M = (-1.9, 1.9)
CYL_Z_M = 1.2


def _anchor_local(item: dict[str, Any], suffix: str) -> tuple[float, float, float]:
    """Item-local position of the anchor ``<tag>.<suffix>``."""
    wanted = f"{item['tag']}.{suffix}"
    for anchor_id, world in anchors_of(item):
        if anchor_id == wanted:
            return to_local(item, world)
    raise ValueError(f"anchor {wanted} missing from the spec")


def _engine(ctx: BuildContext, item: dict[str, Any]) -> None:
    """Gas engine block, exhaust stack, coupling guard."""
    tag = item["tag"]
    block = mesh_ops.box(f"{tag}_engine", (4.0, 2.0, 2.2), (3.5, 0.0, 1.45))
    mesh_ops.bevel_edges(block, 0.04)
    ctx.add_part(tag, block, "paint_grey")
    ex, ey, top = _anchor_local(item, "engine_exhaust")
    base = 2.55
    stack = mesh_ops.cylinder(f"{tag}_exhaust", 0.18, top - base, (ex, ey, (top + base) / 2))
    ctx.add_part(tag, stack, "paint_dark")
    guard = mesh_ops.half_cylinder(f"{tag}_guard", 0.35, 1.0, (1.0, 0.0, CYL_Z_M))
    ctx.add_part(tag, guard, "safety_yellow")


def _crank_end(ctx: BuildContext, tag: str) -> None:
    """Crankcase, four cylinders and four distance pieces."""
    crank = mesh_ops.box(f"{tag}_crankcase", (3.0, 1.6, 1.0), (-1.5, 0.0, 0.85))
    mesh_ops.bevel_edges(crank, 0.03)
    ctx.add_part(tag, crank, "paint_grey")
    for i, (x, y) in enumerate((x, y) for x in CYL_X_M for y in CYL_Y_M):
        cyl = mesh_ops.cylinder(f"{tag}_cyl_{i}", 0.35, 1.6, (x, y, CYL_Z_M), axis="Y")
        ctx.add_part(tag, cyl, "paint_grey")
        sign = 1 if y > 0 else -1
        dist = mesh_ops.cylinder(f"{tag}_dist_{i}", 0.16, 0.3, (x, sign * 0.95, CYL_Z_M), axis="Y")
        ctx.add_part(tag, dist, "paint_dark")


def _bottles_and_vent(ctx: BuildContext, item: dict[str, Any]) -> None:
    """Suction and discharge bottles, the packing vent manifold and riser (with flanges)."""
    tag = item["tag"]
    horizontal_vessel(ctx, tag, f"{tag}_suction", 0.9, 5.0, (-1.5, -1.9, 2.5))
    horizontal_vessel(ctx, tag, f"{tag}_discharge", 0.8, 5.0, (-1.5, 1.9, 2.5))
    px, py, pz = _anchor_local(item, "packing")
    manifold = mesh_ops.cylinder(f"{tag}_manifold", 0.05, 1.2, (px, py, pz), axis="X")
    ctx.add_part(tag, manifold, "paint_dark")
    riser_top = 2.0
    riser = mesh_ops.cylinder(
        f"{tag}_riser", 0.04, riser_top - pz, (px, py, (pz + riser_top) / 2), segments=12
    )
    ctx.add_part(tag, riser, "paint_dark")
    flange(ctx, tag, f"{tag}_riser_flange", 0.04, (px, py, riser_top))


def build(item: dict[str, Any], ctx: BuildContext) -> None:
    """Build K-202: pad, skid, engine, crank end, bottles, vent line and south handrail.

    Args:
        item: Spec item (``type`` ``recip_compressor``).
        ctx: Build context.
    """
    tag = item["tag"]
    ctx.new_root(item)
    pad = mesh_ops.box(f"{tag}_pad", (13.0, 6.4, 0.3), (0.0, 0.0, -0.15))
    ctx.add_part(tag, pad, "concrete", tile_m=3.0)
    skid(ctx, tag, 12.0, 4.0)
    _engine(ctx, item)
    _crank_end(ctx, tag)
    _bottles_and_vent(ctx, item)
    handrail(ctx, tag, 12.0, -3.0, 0.0)
