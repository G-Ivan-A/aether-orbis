"""Validate Aether Orbis contract artifacts and reapply decision policies."""

from __future__ import annotations

import json
import operator
from pathlib import Path
from typing import Any, Callable, Iterable

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource


ARTIFACTS = (
    ("configs/directions/*/research-profile.yaml", "research-profile.schema.json"),
    ("configs/runtime/*.yaml", "runtime-configuration.schema.json"),
    ("examples/research-specifications/*.yaml", "research-specification.schema.json"),
)

OPERATORS: dict[str, Callable[[float, float], bool]] = {
    "gte": operator.ge,
    "gt": operator.gt,
    "lte": operator.le,
    "lt": operator.lt,
    "eq": operator.eq,
}


def load_document(path: Path) -> Any:
    """Load a JSON or YAML document from *path*."""

    with path.open(encoding="utf-8") as stream:
        if path.suffix == ".json":
            return json.load(stream)
        return yaml.safe_load(stream)


def load_schema_registry(schema_dir: Path) -> tuple[dict[str, Any], Registry]:
    """Load and statically check every JSON Schema in *schema_dir*."""

    schemas: dict[str, Any] = {}
    resources: list[tuple[str, Resource[Any]]] = []
    for path in sorted(schema_dir.glob("*.schema.json")):
        schema = load_document(path)
        Draft202012Validator.check_schema(schema)
        schemas[path.name] = schema
        resources.append((schema["$id"], Resource.from_contents(schema)))
    return schemas, Registry().with_resources(resources)


def _json_path(parts: Iterable[object]) -> str:
    path = "$"
    for part in parts:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}"
    return path


def format_schema_error(error: ValidationError) -> str:
    """Format a jsonschema error with an unambiguous instance path."""

    return f"{_json_path(error.absolute_path)}: {error.message}"


def _specification_from(document: Any, schema_name: str) -> dict[str, Any] | None:
    if not isinstance(document, dict):
        return None
    if schema_name == "research-specification.schema.json":
        return document
    if schema_name == "research-profile.schema.json":
        specification = document.get("specification")
        return specification if isinstance(specification, dict) else None
    return None


def validate_policy_dimensions(document: Any, schema_name: str) -> list[str]:
    """Validate invariants that relate independently extensible named dimensions."""

    specification = _specification_from(document, schema_name)
    if specification is None:
        return []

    errors: list[str] = []
    prefix = "$.specification" if schema_name == "research-profile.schema.json" else "$"

    evaluation = specification.get("evaluation")
    if isinstance(evaluation, dict):
        dimensions = evaluation.get("dimensions")
        declared = set(dimensions) if isinstance(dimensions, list) else set()
        policy = evaluation.get("decision_policy")
        rules = policy.get("rules", []) if isinstance(policy, dict) else []
        for rule_index, rule in enumerate(rules if isinstance(rules, list) else []):
            conditions = rule.get("all", []) if isinstance(rule, dict) else []
            for condition_index, condition in enumerate(
                conditions if isinstance(conditions, list) else []
            ):
                dimension = condition.get("dimension") if isinstance(condition, dict) else None
                if isinstance(dimension, str) and dimension not in declared:
                    errors.append(
                        f"{prefix}.evaluation.decision_policy.rules[{rule_index}].all"
                        f"[{condition_index}].dimension: {dimension!r} is not declared in "
                        "evaluation.dimensions"
                    )

    termination = specification.get("termination")
    if isinstance(termination, dict):
        dimensions = termination.get("completion_dimensions")
        declared = set(dimensions) if isinstance(dimensions, list) else set()
        conditions = termination.get("success_conditions", [])
        for condition_index, condition in enumerate(
            conditions if isinstance(conditions, list) else []
        ):
            dimension = condition.get("dimension") if isinstance(condition, dict) else None
            if isinstance(dimension, str) and dimension not in declared:
                errors.append(
                    f"{prefix}.termination.success_conditions[{condition_index}].dimension: "
                    f"{dimension!r} is not declared in termination.completion_dimensions"
                )

    if schema_name == "research-profile.schema.json" and isinstance(document, dict):
        outer_model = document.get("acquisition_model")
        inner_model = specification.get("acquisition_model")
        if outer_model is not None and inner_model is not None and outer_model != inner_model:
            errors.append(
                "$.specification.acquisition_model: must match $.acquisition_model "
                f"({outer_model!r})"
            )

    return errors


def validate_document(path: Path, schema_name: str, schema_dir: Path) -> list[str]:
    """Return all schema and cross-field validation errors for one document."""

    document = load_document(path)
    schemas, registry = load_schema_registry(schema_dir)
    if schema_name not in schemas:
        return [f"$: schema {schema_name!r} was not found in {schema_dir}"]

    validator = Draft202012Validator(
        schemas[schema_name], registry=registry, format_checker=FormatChecker()
    )
    errors = [format_schema_error(error) for error in validator.iter_errors(document)]
    errors.extend(validate_policy_dimensions(document, schema_name))
    return sorted(set(errors))


def _as_document(value: Any) -> Any:
    if isinstance(value, (str, Path)):
        return load_document(Path(value))
    return value


def apply_decision_policy(evaluation: Any, policy: Any) -> str:
    """Apply *policy* to a saved EvaluationResult without reevaluating its subject."""

    evaluation_doc = _as_document(evaluation)
    policy_doc = _as_document(policy)
    scores = {
        name: characteristic["score"]
        for name, characteristic in evaluation_doc["characteristics"].items()
    }
    for rule in policy_doc["rules"]:
        if all(
            condition["dimension"] in scores
            and OPERATORS[condition["operator"]](
                scores[condition["dimension"]], condition["value"]
            )
            for condition in rule["all"]
        ):
            return rule["decision"]
    return policy_doc["fallback"]


def iter_repository_artifacts(root: Path) -> Iterable[tuple[Path, str]]:
    """Yield tracked contract artifacts and their schema filenames."""

    for pattern, schema_name in ARTIFACTS:
        for path in sorted(root.glob(pattern)):
            yield path, schema_name


def validate_repository(root: Path) -> list[str]:
    """Validate every repository artifact governed by an executable schema."""

    errors: list[str] = []
    schema_dir = root / "configs" / "schemas"
    for path, schema_name in iter_repository_artifacts(root):
        relative_path = path.relative_to(root)
        errors.extend(
            f"{relative_path}: {error}"
            for error in validate_document(path, schema_name, schema_dir)
        )
    return sorted(errors)
