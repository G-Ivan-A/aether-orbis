"""Import path bootstrap for the test suite.

``unittest discover -s tests`` imports test modules as top-level modules, so the
``tests`` package ``__init__`` is not guaranteed to run first. Every test module
that imports the source package therefore imports this module explicitly, which
keeps the local and CI commands identical and free of an installation step.
"""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
