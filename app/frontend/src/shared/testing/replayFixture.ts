import type { ReplayScenario } from "@/shared/types/generated/contract";

/**
 * Build a small valid replay scenario (10 one-minute samples) for tests.
 *
 * @param overrides - Fields to replace.
 * @returns A replay scenario that passes `parseReplayScenario`.
 */
export function makeReplay(overrides: Partial<ReplayScenario> = {}): ReplayScenario {
  const n = 10;
  return {
    schema_version: 1,
    scenario_id: "s1_rod_packing",
    title: "Test scenario",
    sim_start_utc: "2025-07-15T06:00:00Z",
    duration_s: n * 60,
    step_s: 60,
    sensors: [{ id: "AT-101", x_m: 10, y_m: 20, z_m: 1.5 }],
    series: { "AT-101": Array.from({ length: n }, (_, i) => 2 + i * 0.1) },
    units: { "AT-101": "ppm" },
    wind_speed_m_s: Array(n).fill(3.5),
    wind_from_deg: Array(n).fill(250),
    stability: Array(n).fill("D"),
    events: [],
    log: [],
    grid: { x0_m: 0, y0_m: 0, dx_m: 5, dy_m: 5, nx: 40, ny: 30, encoding: "log_u8_0.1_1000ppm" },
    keyframes: [],
    attribution: "Weather: Open-Meteo (CC BY 4.0)",
    simulated: true,
    ...overrides,
  };
}
