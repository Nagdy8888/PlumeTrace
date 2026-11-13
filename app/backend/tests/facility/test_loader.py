"""Tests for loading the real KS-07 spec."""

from pathlib import Path

import pytest

from plumetrace.facility.candidates import methane_sensors
from plumetrace.facility.loader import DEFAULT_SPEC_PATH, load_facility


def test_real_spec_loads_with_expected_counts() -> None:
    """KS-07 has 24 equipment items, 15 pipe routes, 18 instruments and 8 methane sensors."""
    spec = load_facility()
    assert spec.site.id == "KS-07"
    assert spec.site.fictional is True
    assert len(spec.equipment) == 24
    assert len(spec.piping) == 15
    assert len(spec.instruments) == 18
    assert len(methane_sensors(spec)) == 8


def test_compressors_vent_to_shared_stack() -> None:
    """S1 relies on all three packing vents being routed to VS-250."""
    spec = load_facility()
    for tag in ("K-201", "K-202", "K-203"):
        assert spec.equipment_by_tag(tag).vents_to == "VS-250"


def test_unknown_tag_lookup_raises() -> None:
    """Looking up a missing tag names the tag."""
    with pytest.raises(KeyError, match="K-999"):
        load_facility().equipment_by_tag("K-999")


def test_gas_composition_sums_to_one() -> None:
    """The KS-07 gas composition is normalised."""
    assert abs(sum(load_facility().gas_composition.values()) - 1.0) < 1e-9


def test_loader_reads_utf8(tmp_path: Path) -> None:
    """Non-ASCII text in the YAML loads on every OS (explicit UTF-8)."""
    text = DEFAULT_SPEC_PATH.read_text(encoding="utf-8").replace(
        "description: Control room}", 'description: "Control room – ambient ≈ 25 °C"}'
    )
    path = tmp_path / "ks07.yaml"
    path.write_text(text, encoding="utf-8")
    spec = load_facility(path)
    assert spec.equipment_by_tag("CR-901").description == "Control room – ambient ≈ 25 °C"
