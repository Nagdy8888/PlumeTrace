"""Geometry value types shared by the engineering core.

Coordinates are metres: x = east, y = north, z = up, origin = south-west fence corner.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Point3:
    """A point in site coordinates.

    Attributes:
        x_m: Easting in metres.
        y_m: Northing in metres.
        z_m: Height above ground in metres.
    """

    x_m: float
    y_m: float
    z_m: float


@dataclass(frozen=True)
class Candidate:
    """A possible emission point the inversion may pick as the source.

    Attributes:
        id: Anchor id, for example ``VS-250.tip``.
        position: Where the emission would leave the equipment.
    """

    id: str
    position: Point3


@dataclass(frozen=True)
class Sensor:
    """A fixed methane point sensor.

    Attributes:
        id: Instrument tag, for example ``AT-101``.
        position: Sensor position.
        noise_ppm: One-sigma measurement noise in ppm.
    """

    id: str
    position: Point3
    noise_ppm: float
