"""Input model of the Bayesian source inversion.

``InversionInput`` holds one event's candidates, sensors, window means, wind and error model and
rejects empty or inconsistent input. It lives apart from ``inversion.py`` to keep both modules
small; ``inversion`` re-exports it and the constants below. Pure Python and numpy, no I/O.
"""

import math
from typing import Final, Self

import numpy as np
from pydantic import BaseModel, ConfigDict, model_validator

from plumetrace.engineering.dispersion import CoefficientSet
from plumetrace.engineering.geometry import Candidate, Sensor
from plumetrace.engineering.stability import StabilityClass

NO_SOURCE_ID: Final = "NONE"
DEFAULT_OBS_SIGMA_PPM: Final = 0.1
DEFAULT_MODEL_REL_ERROR: Final = 0.6
MAX_ABS_OBS_PPM: Final = 1.0e6  # pure methane; a mole-fraction difference cannot exceed it


class InversionInput(BaseModel):
    """Everything the inversion needs for one event.

    Attributes:
        candidates: Possible emission points (``C``), ids unique and never ``NONE``.
        sensors: Methane sensors (``S``).
        observed_ppm_above_bg: Window means above background, ``W`` rows of ``S`` values; NaN or
            infinite values are treated as missing. Every finite value must satisfy
            ``abs(value) <= MAX_ABS_OBS_PPM``, otherwise the input is rejected.
        wind_speed_m_s: Mean wind speed per window in m/s; NaN means unknown. A finite value must
            be >= 0, otherwise the input is rejected.
        wind_from_deg: Mean wind "from" bearing per window, degrees clockwise from north.
        stability: Pasquill class per window.
        temp_k: Air temperature in K.
        pressure_pa: Air pressure in Pa.
        obs_sigma_ppm: Observation noise, one sigma, in ppm (> 0).
        model_rel_error: Relative one-sigma error of the plume model (>= 0).
        coeff: Dispersion coefficient set.
        wind_dir_sd_deg: Optional within-window wind-direction standard deviation per window in
            degrees (see ``window_direction_sd_deg``); None (the default) keeps the narrow plume.
            Each finite value must be >= 0; NaN is allowed only where ``wind_from_deg`` is NaN.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    candidates: list[Candidate]
    sensors: list[Sensor]
    observed_ppm_above_bg: list[list[float]]
    wind_speed_m_s: list[float]
    wind_from_deg: list[float]
    stability: list[StabilityClass]
    temp_k: float
    pressure_pa: float
    obs_sigma_ppm: float = DEFAULT_OBS_SIGMA_PPM
    model_rel_error: float = DEFAULT_MODEL_REL_ERROR
    coeff: CoefficientSet = CoefficientSet.BRIGGS_RURAL
    wind_dir_sd_deg: list[float] | None = None

    @model_validator(mode="after")
    def _check(self) -> Self:
        """Reject empty or inconsistent input instead of returning a meaningless posterior."""
        ids = [c.id for c in self.candidates]
        if not ids or not self.sensors:
            raise ValueError("candidates and sensors must not be empty")
        if NO_SOURCE_ID in ids or len(set(ids)) != len(ids):
            raise ValueError(f"candidate ids must be unique and not {NO_SOURCE_ID!r}")
        n = len(self.observed_ppm_above_bg)
        if not (len(self.wind_speed_m_s) == len(self.wind_from_deg) == len(self.stability) == n):
            raise ValueError(
                "wind, stability and observation arrays must have one entry per window"
            )
        if any(len(row) != len(self.sensors) for row in self.observed_ppm_above_bg):
            raise ValueError("every observation row must have one value per sensor")
        obs = np.array(self.observed_ppm_above_bg, dtype=np.float64)
        if np.any(np.abs(obs[np.isfinite(obs)]) > MAX_ABS_OBS_PPM):
            raise ValueError(
                "finite observed_ppm_above_bg values must be within -1e6 and 1e6 ppm "
                "(1e6 ppm is pure methane)"
            )
        speed = np.array(self.wind_speed_m_s, dtype=np.float64)
        if np.any(speed[np.isfinite(speed)] < 0.0):
            raise ValueError("wind_speed_m_s values must be >= 0 or NaN (unknown)")
        self._check_direction_spread()
        positive = (self.obs_sigma_ppm, self.temp_k, self.pressure_pa)
        if not all(v > 0.0 and math.isfinite(v) for v in positive):
            raise ValueError("obs_sigma_ppm, temp_k and pressure_pa must be positive and finite")
        if not (self.model_rel_error >= 0.0 and math.isfinite(self.model_rel_error)):
            raise ValueError("model_rel_error must be >= 0 and finite")
        return self

    def _check_direction_spread(self) -> None:
        """Reject a ``wind_dir_sd_deg`` of wrong length, negative, infinite or NaN where known."""
        if self.wind_dir_sd_deg is None:
            return
        if len(self.wind_dir_sd_deg) != len(self.wind_from_deg):
            raise ValueError("wind_dir_sd_deg must have one entry per window")
        spread = np.array(self.wind_dir_sd_deg, dtype=np.float64)
        known = np.isfinite(np.array(self.wind_from_deg, dtype=np.float64))
        if np.any(np.isinf(spread)) or np.any(spread[~np.isnan(spread)] < 0.0):
            raise ValueError("wind_dir_sd_deg values must be >= 0 and finite (or NaN)")
        if np.any(np.isnan(spread) & known):
            raise ValueError("wind_dir_sd_deg must not be NaN where wind_from_deg is known")
