"""Response models of the REST API (health and scenario list)."""

from typing import Literal

from pydantic import BaseModel


class Health(BaseModel):
    """Liveness answer.

    Attributes:
        status: Always ``"ok"`` when the server answers.
        version: The ``plumetrace`` package version.
    """

    status: Literal["ok"]
    version: str


class ScenarioSummary(BaseModel):
    """One scenario in the picker list.

    Attributes:
        id: Scenario id, for example ``s1_rod_packing``.
        title: Display title.
        duration_h: Scenario length in hours.
        is_mvp: Whether the scenario is part of the MVP set (all three are).
    """

    id: str
    title: str
    duration_h: int
    is_mvp: bool
