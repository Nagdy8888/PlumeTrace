# Procedural equipment

The station is built entirely in code from the facility spec. No downloaded models (only CC0
textures and one HDRI from Poly Haven).

**Who uses this file:** in the chosen approach B, the bpy generator in `scripts/blender/` builds
these parts and equipment in Blender (then bakes and exports). In fallback A, the same designs
become R3F components under `features/station3d/{parts,equipment,instanced}/`. The look, the parts
and the anchors below are the same either way; only the implementation language differs.

## From spec to scene
1. `SiteLayout.tsx` reads the spec and maps each item through `equipmentRegistry.ts`
   (`type -> component`). Unknown types render a labelled placeholder box and log a warning — never
   crash.
2. Each equipment component receives its spec item (`tag`, `position_m`, `rotation_deg`,
   dimensions in metres, nozzle points) and builds itself from **parts**.
3. Units: the scene uses **1 unit = 1 metre**, Y up, origin at the station's survey point,
   north = −Z. Keep real dimensions (a recip compressor skid ≈ 12 × 4 × 3 m, a flare stack
   ≈ 30–40 m) so plumes and distances look right.

## Parts library (`parts/`)
Small parametric components reused across equipment:
- `Vessel` — cylinder shell + 2:1 elliptical heads (lathe geometry), horizontal or vertical,
  `diameter_m`, `length_m`; optional saddles or skirt.
- `Nozzle` — short pipe + flange at a spec nozzle point; feeds instanced flanges.
- `Platform`, `Ladder`, `Handrail` — steel access structures; posts/rungs are instanced.
- `Skid` — base frame of I-beams (merged geometry).
Parts accept dimensions and a material key; they never read the store.

## Equipment notes (what makes each look real)
- **Reciprocating compressor:** skid, crankcase block, 2–4 horizontal cylinders with distance
  pieces (the rod packing vent sits here — a named anchor for S1), suction/discharge bottles,
  gas engine driver block, coupling guard, small vent lines up to a safe height.
- **Fin-fan aftercooler:** elevated bundle frame, fan rings with slowly spinning blades
  (rotation in `useFrame`), headers.
- **Scrubber / separator:** vertical/horizontal vessel, level gauge column, PSV on top.
- **TEG contactor + regenerator:** tall contactor column with trays implied by banding,
  reboiler with still column and vent (S-scenario anchor).
- **Tanks:** cylindrical tanks with roof, **thief hatch** as a named anchor (S2), stair, VRU skid.
- **Flare stack:** guyed or self-supporting stack, knock-out drum, pilot; flame is an effect
  (see plume-and-effects), off when the pilot is out (S3).
- **Pipe runs and racks:** tubes along spec waypoints with elbows at corners; racks are merged
  steel frames; supports instanced.
- **Shelters / buildings:** simple boxes with roof overhang and louvers via texture or
  instanced slats; the control room has lit windows at night.

## Materials and look (`materials/`)
- PBR `MeshStandardMaterial` (or `MeshPhysicalMaterial` only where needed): painted steel
  (roughness 0.5–0.7, metalness 0.2–0.4), galvanised grating, concrete, insulation cladding,
  safety yellow for handrails, piping colour bands per service (gas, fuel gas, condensate).
- All materials created once in `materials.ts`, keyed by name; colours come from `palette.ts`
  (shared tokens with the 2D UI).
- Image-based lighting from a **local** HDR in `public/` plus one directional sun; time of day
  changes sun angle/colour and exposure. Night mode: emissive area lights on buildings and
  equipment beacons.
- Subtle realism: ambient occlusion via postprocessing (N8AO/SSAO) on "high" only; slight
  grime/edge wear via a small tiling roughness texture; no heavy texture sets.

## Detail levels
- **High:** full parts, bolts/flanges instanced, AO, shadows.
- **Medium:** no bolts, simplified nozzles, shadows on.
- **Low:** merged silhouettes per equipment, no shadows, no AO.
Use drei `Detailed` (LOD) for compressors and buildings when the camera is far.

## Anchors for the story
Each equipment component exposes named anchor points (`rodPackingVent`, `thiefHatch`, `flareTip`,
`stillVent`, flange ids) through the store, so the plume source, candidate highlight, camera
fly-to and tag labels attach to the exact component the agents name.
