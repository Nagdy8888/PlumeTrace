"""Emission-factor tables for the site inventory and for a leaker found by optical gas imaging.

Constants only. Every table is read-only (``MappingProxyType``) and carries its source.
"""

from types import MappingProxyType
from typing import Final

# source: EPA-453/R-95-017 "1995 Protocol for Equipment Leak Emission Estimates", Table 2-4
# "Oil and Gas Production Operations Average Emission Factors", gas service, p. 2-14.
# kg/h/source of TOTAL ORGANIC COMPOUNDS (includes methane and ethane). "others" covers
# compressors, diaphragms, drains, dump arms, hatches, instruments, meters, pressure relief
# valves, polished rods, relief valves and vents (table footnote c).
EPA_1995_AVERAGE_GAS_TOC_KG_H: Final = MappingProxyType(
    {
        "valves": 4.5e-3,
        "pump_seals": 2.4e-3,
        "others": 8.8e-3,
        "connectors": 2.0e-4,
        "flanges": 3.9e-4,
        "open_ended_lines": 2.0e-3,
    }
)

# source: 40 CFR Part 98 Subpart W, Table W-4 "Default Total Hydrocarbon Leaker Emission
# Factors", onshore natural gas transmission compression, gas service, column "If you survey
# using any of the methods in § 98.234(a)(1), (3), or (5)" (optical gas imaging);
# [89 FR 42325, May 14, 2024]; CFR 2025 edition. Units: scf total hydrocarbon / hour / component.
SUBPART_W_W4_LEAKER_THC_SCF_H: Final = MappingProxyType(
    {
        "compressor": MappingProxyType(
            {
                "valve": 24.2,
                "connector": 9.13,
                "open_ended_line": 28.2,
                "pressure_relief_valve": 64.8,
                "meter": 31.6,
                "other": 6.70,
            }
        ),
        "non_compressor": MappingProxyType(
            {
                "valve": 10.5,
                "connector": 9.3,
                "open_ended_line": 18.4,
                "pressure_relief_valve": 3.28,
                "meter": 4.79,
                "other": 6.70,
            }
        ),
    }
)
