"""Equipment builders by spec ``type`` (registry used by ``build_station.py``)."""

from collections.abc import Callable
from typing import Any

from scene_setup import BuildContext

from equipment import compressor, vent_stack

BUILDERS: dict[str, Callable[[dict[str, Any], BuildContext], None]] = {
    "recip_compressor": compressor.build,
    "vent_stack": vent_stack.build,
}
