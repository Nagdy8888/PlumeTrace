"""Value types of the facility spec: equipment, anchors, piping, instruments, site, operation.

All models are frozen and reject unknown fields, so a typo in ``ks07.yaml`` is an error.
Coordinates are metres: x = east, y = north, z = up, origin = south-west fence corner.
"""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Vec3 = tuple[float, float, float]


class EquipmentType(StrEnum):
    """Kinds of equipment on the station (value equals name)."""

    pig_trap = "pig_trap"
    filter_separator = "filter_separator"
    scrubber = "scrubber"
    recip_compressor = "recip_compressor"
    fin_fan_cooler = "fin_fan_cooler"
    vent_stack = "vent_stack"
    teg_contactor = "teg_contactor"
    teg_regenerator = "teg_regenerator"
    fuel_gas_skid = "fuel_gas_skid"
    storage_tank = "storage_tank"
    vru = "vru"
    knockout_drum = "knockout_drum"
    flare_stack = "flare_stack"
    meter_run = "meter_run"
    building = "building"


class InstrumentKind(StrEnum):
    """Kinds of instrument on the station (value equals name)."""

    methane_point = "methane_point"
    met_mast = "met_mast"
    flow = "flow"
    temperature = "temperature"
    pressure = "pressure"
    thermocouple = "thermocouple"


class _Frozen(BaseModel):
    """Base for all facility models: immutable, no unknown fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class Anchor(_Frozen):
    """A named point on equipment where a leak can be placed.

    Attributes:
        id: Anchor id, ``<equipment tag>.<name>``.
        position_m: Position in site coordinates.
        emission_point: Whether the inversion treats it as a candidate source.
    """

    id: str
    position_m: Vec3
    emission_point: bool


class Equipment(_Frozen):
    """One piece of equipment.

    Attributes:
        tag: Unique equipment tag, for example ``K-202``.
        type: Kind of equipment.
        position_m: Base position in site coordinates.
        rotation_deg: Rotation about the vertical axis in degrees.
        size_m: Bounding box (x, y, z) in metres.
        anchors: Named leak points on this equipment.
        vents_to: Tag of the equipment this one vents to, if any.
        shelter: Whether it sits inside a shelter.
        description: Free-text description.
    """

    tag: str
    type: EquipmentType
    position_m: Vec3
    rotation_deg: float
    size_m: Vec3
    anchors: list[Anchor] = []
    vents_to: str | None = None
    shelter: bool = False
    description: str = ""


class PipeRoute(_Frozen):
    """A pipe route as a polyline.

    Attributes:
        id: Unique route id, for example ``R-250``.
        service: What the pipe carries.
        size_in: Nominal size in inches.
        waypoints_m: Polyline points in site coordinates (at least two).
    """

    id: str
    service: Literal["gas", "vent", "flare", "condensate", "fuel_gas"]
    size_in: float
    waypoints_m: list[Vec3] = Field(min_length=2)


class Instrument(_Frozen):
    """One instrument.

    Attributes:
        tag: Unique instrument tag, for example ``AT-101``.
        kind: Kind of instrument.
        position_m: Position in site coordinates.
        attaches_to: Tag of the equipment it measures, if any.
        noise_ppm: One-sigma noise in ppm (methane sensors only).
    """

    tag: str
    kind: InstrumentKind
    position_m: Vec3
    attaches_to: str | None = None
    noise_ppm: float | None = None


class SiteBounds(_Frozen):
    """Rectangular fence bounds in metres.

    Attributes:
        x_min_m: West edge.
        x_max_m: East edge.
        y_min_m: South edge.
        y_max_m: North edge.
    """

    x_min_m: float
    x_max_m: float
    y_min_m: float
    y_max_m: float

    def contains(self, p: Vec3) -> bool:
        """Tell whether a point is inside the bounds and not below ground.

        Args:
            p: Point in site coordinates.

        Returns:
            True when x and y are within the bounds (inclusive) and ``z >= 0``.
        """
        x, y, z = p
        return self.x_min_m <= x <= self.x_max_m and self.y_min_m <= y <= self.y_max_m and z >= 0


class Site(_Frozen):
    """The site itself.

    Attributes:
        id: Site id, for example ``KS-07``.
        name: Display name.
        fictional: Whether the site is simulated (always true for KS-07).
        bounds: Fence bounds.
        latitude_deg: Latitude used only to fetch weather.
        longitude_deg: Longitude used only to fetch weather.
        elevation_m: Ground elevation in metres.
        ambient_pressure_pa: Ambient pressure in pascals.
    """

    id: str
    name: str
    fictional: bool
    bounds: SiteBounds
    latitude_deg: float
    longitude_deg: float
    elevation_m: float
    ambient_pressure_pa: float


class OperatingConditions(_Frozen):
    """Normal operating conditions of the station.

    Attributes:
        suction_pressure_pa: Compressor suction pressure in pascals.
        discharge_pressure_pa: Compressor discharge pressure in pascals.
        gas_temperature_k: Gas temperature in kelvin.
        throughput_sm3_h: Throughput in standard cubic metres per hour.
    """

    suction_pressure_pa: float
    discharge_pressure_pa: float
    gas_temperature_k: float
    throughput_sm3_h: float
