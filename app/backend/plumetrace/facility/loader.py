"""Load and validate the facility spec from YAML."""

from pathlib import Path
from typing import Final

import yaml

from plumetrace.facility.spec import FacilitySpec

DEFAULT_SPEC_PATH: Final[Path] = Path(__file__).parent / "data" / "ks07.yaml"


def load_facility(path: Path = DEFAULT_SPEC_PATH) -> FacilitySpec:
    """Read a facility YAML file and validate it.

    Args:
        path: YAML file to read; defaults to the shipped KS-07 spec.

    Returns:
        The validated facility spec.

    Raises:
        pydantic.ValidationError: If the content breaks a validation rule.
    """
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return FacilitySpec.model_validate(data)
