"""Repository test suite.

``unittest discover`` runs from the repository root, so ``tools`` is importable
but the source package is not: ``src`` is added to the import path here instead
of installing the package, keeping the local and CI commands identical.
"""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
