"""Ingestion and extraction must not contain criteria of their own.

Every selection, preservation and termination criterion belongs to the Research
Specification. This check keeps thresholds, decision names and preservation
levels out of the acquisition and extraction modules, where they would become
invisible policy.
"""

import ast
import unittest
from pathlib import Path

from tests.support import ROOT

PACKAGE = ROOT / "src" / "aether_orbis"

CRITERIA_FREE_MODULES = (
    PACKAGE / "ingestion.py",
    PACKAGE / "extraction.py",
    PACKAGE / "frontier.py",
    PACKAGE / "grouping.py",
)

FORBIDDEN_NAMES = (
    "QUALIFIED",
    "CONDITIONAL",
    "REJECTED",
    "decision_policy",
    "acquired_artifact",
    "derived_knowledge",
    "observation_history",
    "stop_conditions",
    "success_conditions",
    "threshold",
)

FORBIDDEN_IMPORTS = (
    "aether_orbis.evaluation",
    "aether_orbis.preservation",
)


def _code_tokens(path: Path) -> set[str]:
    """Return every identifier, attribute and string literal used as code."""

    tree = ast.parse(path.read_text(encoding="utf-8"))
    tokens: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            tokens.add(node.id)
        elif isinstance(node, ast.Attribute):
            tokens.add(node.attr)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            tokens.add(node.value)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            tokens.add(node.name)
        elif isinstance(node, ast.keyword) and node.arg:
            tokens.add(node.arg)
    return tokens


class CriteriaBoundaryTests(unittest.TestCase):
    def test_acquisition_modules_carry_no_selection_or_preservation_criteria(self):
        for path in CRITERIA_FREE_MODULES:
            tokens = _code_tokens(path)
            for name in FORBIDDEN_NAMES:
                with self.subTest(module=path.name, name=name):
                    self.assertNotIn(
                        name,
                        tokens,
                        f"{path.name} must not decide {name!r}; criteria come from the "
                        "Research Specification",
                    )

    def test_acquisition_modules_do_not_import_the_deciding_stages(self):
        for path in CRITERIA_FREE_MODULES:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module)
                elif isinstance(node, ast.Import):
                    imported.update(alias.name for alias in node.names)
            for module in FORBIDDEN_IMPORTS:
                with self.subTest(module=path.name, imported=module):
                    self.assertNotIn(module, imported)

    def test_numeric_thresholds_appear_only_where_the_policy_is_applied(self):
        for path in CRITERIA_FREE_MODULES:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            comparisons = [
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.Compare)
                and any(
                    isinstance(comparator, ast.Constant)
                    and isinstance(comparator.value, float)
                    for comparator in node.comparators
                )
            ]
            with self.subTest(module=path.name):
                self.assertEqual([], comparisons)


class PortIsolationTests(unittest.TestCase):
    def test_the_runtime_core_imports_nothing_outside_the_standard_library(self):
        allowed = {"aether_orbis"}
        for path in sorted(PACKAGE.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                modules = []
                if isinstance(node, ast.ImportFrom) and node.module:
                    modules.append(node.module)
                elif isinstance(node, ast.Import):
                    modules.extend(alias.name for alias in node.names)
                for module in modules:
                    root = module.split(".")[0]
                    with self.subTest(module=path.name, imported=module):
                        self.assertTrue(
                            root in allowed or _is_standard_library(root),
                            f"{path.name} imports third-party module {module!r}",
                        )


def _is_standard_library(name: str) -> bool:
    import sys

    return name in sys.stdlib_module_names


if __name__ == "__main__":
    unittest.main()
