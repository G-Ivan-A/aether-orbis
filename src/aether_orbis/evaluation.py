"""Evaluation and qualification.

Measurement and decision are two separate artifacts: Evaluation stores an
immutable ``EvaluationResult`` and a versioned Decision Policy then produces a
``QualificationDecision`` (``relevance-gate-contract.md`` O-1, O-4). A stored
EvaluationResult can be re-decided by another policy without calling Evaluation
again (O-5), which is why the policy interpreter below only reads scores.
"""

from __future__ import annotations

import operator
from hashlib import sha256
from typing import Any, Callable, Mapping

from aether_orbis.errors import SpecificationError
from aether_orbis.model import Measurement, NormalizedSource

STAGES = ("triage", "full")

OPERATORS: dict[str, Callable[[float, float], bool]] = {
    "gte": operator.ge,
    "gt": operator.gt,
    "lte": operator.le,
    "lt": operator.lt,
    "eq": operator.eq,
}


def declared_dimensions(specification: Mapping[str, Any]) -> tuple[str, ...]:
    """Return the characteristic names declared by the specification."""

    evaluation = specification.get("evaluation")
    dimensions = evaluation.get("dimensions") if isinstance(evaluation, dict) else None
    if not isinstance(dimensions, list) or not dimensions:
        raise SpecificationError("specification.evaluation.dimensions is required")
    return tuple(dimensions)


def decision_policy(specification: Mapping[str, Any]) -> dict[str, Any]:
    """Return the Decision Policy declared by the specification."""

    evaluation = specification.get("evaluation")
    policy = evaluation.get("decision_policy") if isinstance(evaluation, dict) else None
    if not isinstance(policy, dict):
        raise SpecificationError("specification.evaluation.decision_policy is required")
    return policy


def evaluation_id_for(source: NormalizedSource, stage: str, evaluated_at: str) -> str:
    digest = sha256(
        f"{source.source_id}\n{stage}\n{evaluated_at}".encode("utf-8")
    ).hexdigest()
    return f"eval-{digest[:16]}"


def decision_id_for(evaluation_id: str, policy: Mapping[str, Any], decided_at: str) -> str:
    digest = sha256(
        f"{evaluation_id}\n{policy['policy_id']}\n{policy['policy_version']}\n{decided_at}".encode(
            "utf-8"
        )
    ).hexdigest()
    return f"dec-{digest[:16]}"


def build_evaluation_result(
    source: NormalizedSource,
    specification: Mapping[str, Any],
    measurements: Mapping[str, Measurement],
    *,
    stage: str,
    evaluated_at: str,
) -> dict[str, Any]:
    """Return a stored EvaluationResult for *source*.

    Every measured characteristic must be declared by the specification; an
    undeclared name is a configuration error rather than a silent default
    (``relevance-gate-contract.md`` escalation rule 1).
    """

    if stage not in STAGES:
        raise SpecificationError(f"evaluation_stage must be one of {STAGES}, got {stage!r}")
    if not measurements:
        raise SpecificationError("evaluation produced no characteristics")

    declared = set(declared_dimensions(specification))
    undeclared = sorted(set(measurements) - declared)
    if undeclared:
        raise SpecificationError(
            "characteristics are not declared in evaluation.dimensions: "
            + ", ".join(undeclared)
        )
    if "confidence" in measurements:
        raise SpecificationError("the generic characteristic 'confidence' is forbidden")

    return {
        "schema_version": "1.0",
        "evaluation_id": evaluation_id_for(source, stage, evaluated_at),
        "specification_id": specification["specification_id"],
        "subject": {
            "source_id": source.source_id,
            "source_group_id": source.source_group_id,
            "canonical_url": source.canonical_url,
            "content_hash": source.content_hash,
        },
        "evaluation_stage": stage,
        "characteristics": {
            name: {
                "score": measurement.score,
                "rationale": measurement.rationale,
            }
            for name, measurement in measurements.items()
        },
        "evaluated_at": evaluated_at,
    }


def match_decision_rule(
    evaluation: Mapping[str, Any], policy: Mapping[str, Any]
) -> tuple[str, int | None]:
    """Return the decision of *policy* for *evaluation* and the matched rule index.

    The index is ``None`` when the ordered rules did not match and the fallback
    applied. A rule whose condition names a characteristic that was not measured
    never matches; no default score is substituted.
    """

    scores = {
        name: characteristic["score"]
        for name, characteristic in evaluation["characteristics"].items()
    }
    for index, rule in enumerate(policy["rules"]):
        if all(
            condition["dimension"] in scores
            and OPERATORS[condition["operator"]](
                scores[condition["dimension"]], condition["value"]
            )
            for condition in rule["all"]
        ):
            return rule["decision"], index
    return policy["fallback"], None


def apply_decision_policy(
    evaluation: Mapping[str, Any], policy: Mapping[str, Any]
) -> str:
    """Apply *policy* to a stored EvaluationResult without reevaluating it."""

    return match_decision_rule(evaluation, policy)[0]


def build_qualification_decision(
    evaluation: Mapping[str, Any],
    policy: Mapping[str, Any],
    *,
    decided_at: str,
) -> dict[str, Any]:
    """Return the explainable QualificationDecision for a stored evaluation."""

    decision, matched_rule = match_decision_rule(evaluation, policy)
    evaluation_id = evaluation["evaluation_id"]
    if matched_rule is None:
        rationale = (
            f"No rule of policy {policy['policy_id']} {policy['policy_version']} matched "
            f"the {evaluation['evaluation_stage']} characteristics; fallback {decision} "
            "applied."
        )
    else:
        rationale = (
            f"Rule {matched_rule} of policy {policy['policy_id']} "
            f"{policy['policy_version']} matched the {evaluation['evaluation_stage']} "
            f"characteristics: {_conditions_text(policy['rules'][matched_rule], evaluation)}."
        )
    return {
        "schema_version": "1.0",
        "decision_id": decision_id_for(evaluation_id, policy, decided_at),
        "evaluation_id": evaluation_id,
        "policy_id": policy["policy_id"],
        "policy_version": policy["policy_version"],
        "decision": decision,
        "matched_rule": matched_rule,
        "rationale": rationale,
        "decided_at": decided_at,
    }


def _conditions_text(rule: Mapping[str, Any], evaluation: Mapping[str, Any]) -> str:
    characteristics = evaluation["characteristics"]
    return ", ".join(
        f"{condition['dimension']}={characteristics[condition['dimension']]['score']} "
        f"{condition['operator']} {condition['value']}"
        for condition in rule["all"]
    )


def qualification_telemetry(decision: Mapping[str, Any]) -> dict[str, Any]:
    """Return the telemetry ``qualification`` block for a decision."""

    return {
        "decision": decision["decision"],
        "policy_id": decision["policy_id"],
        "policy_version": decision["policy_version"],
        "matched_rule": decision["matched_rule"],
    }


def evaluation_telemetry(evaluation: Mapping[str, Any]) -> dict[str, Any]:
    """Return the telemetry ``evaluation`` block for a stored evaluation."""

    return {
        "stage": evaluation["evaluation_stage"],
        "characteristics": {
            name: characteristic["score"]
            for name, characteristic in evaluation["characteristics"].items()
        },
    }
