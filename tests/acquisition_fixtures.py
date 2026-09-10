"""Access to the local acquisition example used as the integration fixture.

The wiring lives in ``examples/acquisition/local_acquisition_run.py`` so that the
documented example and the integration expectations cannot drift apart; this
module only loads it as a module.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "acquisition" / "local_acquisition_run.py"

_spec = importlib.util.spec_from_file_location("local_acquisition_run", EXAMPLE)
local_acquisition_run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(local_acquisition_run)

ACQUISITION = local_acquisition_run.ACQUISITION
MODELS = local_acquisition_run.MODELS
build_pipeline = local_acquisition_run.build_pipeline
load_specification = local_acquisition_run.load_specification
run = local_acquisition_run.run
