import facility from "@/shared/facility/ks07.json";
import type { FacilitySpec } from "@/shared/types/generated/contract";

/** The facility spec as the generated contract type (the JSON import infers looser tuple types). */
export const FACILITY = facility as unknown as FacilitySpec;
