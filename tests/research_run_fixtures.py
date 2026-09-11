"""Access to the end-to-end example used as the Research Run fixture.

The wiring lives in ``examples/research-runs/local_research_run.py`` so that the
documented one-command run and the end-to-end expectations cannot drift apart;
this module only loads it as a module.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "research-runs" / "local_research_run.py"

_spec = importlib.util.spec_from_file_location("local_research_run", EXAMPLE)
local_research_run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(local_research_run)

COMPLETION_MEASURES = local_research_run.COMPLETION_MEASURES
build_orchestrator = local_research_run.build_orchestrator
load_runtime_configuration = local_research_run.load_runtime_configuration
run = local_research_run.run
