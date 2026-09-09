# Phase 1 Contract Foundation Design

**Issue:** [#35 — P1-A: contracts and executable Research Specifications](https://github.com/G-Ivan-A/aether-orbis/issues/35)

**Status:** Approved by the issue's autonomous-execution instruction

## Goal

Create the machine-validated contract foundation for Phase 1. The result must express all five
representative Acquisition Models through one Research Specification, provide executable Research
Profiles for AM-1 and AM-2, and keep research policy separate from runtime configuration.

## Governing decisions

This design implements the accepted decisions without changing them:

- [ADR-004](../../adr/2026-09-adr-004-preservation-policy.md): preservation is three independent
  dimensions; provenance and content identity are invariant; Phase 1 permits only `latest_only`;
  `archival` is explicit.
- [ADR-005](../../adr/2026-09-adr-005-evaluation-result.md): EvaluationResult contains extensible
  named characteristics; a reusable decision policy produces `QUALIFIED`, `CONDITIONAL`, or
  `REJECTED`; universal `confidence` is forbidden.
- [ADR-006](../../adr/2026-09-adr-006-research-specification.md): every specification contains
  `objective`, `target`, `scope`, `evaluation`, `preservation`, and `termination`; frontier strategy
  is `enumerate`, `expand`, or `query`; run outcomes are explicit and explained; Research Profile
  and Runtime Configuration are separate classes.

## Chosen approach

JSON Schema Draft 2020-12 is the contract source of truth. Schemas use stable `$id` values and
compose through a local registry. A Python validator loads YAML or JSON, validates format-bearing
fields, and applies repository-level checks that JSON Schema cannot express cleanly, such as
matching a decision policy's dimension references to the declared evaluation dimensions.

This is preferred to Python domain models because P1-A defines contracts rather than runtime
entities. It is preferred to documentation-only schemas and shell checks because the Definition of
Done requires positive and negative fixtures, composed validation, and reliable rejection of mixed
configuration classes.

## Contract and file architecture

`configs/schemas/` will contain composable schemas for:

- Research Specification, executable Research Profile, and Runtime Configuration;
- Preservation Policy and preserved records;
- ExtractionResult;
- EvaluationResult, QualificationDecision, and data-defined Decision Policy;
- Research Run Outcome and Research Run;
- TelemetryEvent.

The general Research Specification schema expresses AM-1 through AM-5. It requires the six policy
blocks and supports all accepted preservation values, including conceptual future values. The
Research Profile schema wraps a specification with profile identity and support metadata. For
`phase: 1` and `support: executable`, it restricts `acquisition_model` to AM-1/AM-2 and
`observation_history` to `latest_only`. Analytical examples for AM-3 through AM-5 validate against
the general specification but are not installed as executable profiles.

`configs/directions/` will retain two direction directories but replace their flat mixed YAML with:

- `hub-practice-analysis`: executable AM-1 Domain Monitoring;
- `reputation-technologies`: executable AM-2 Entity / Relationship Extraction.

Both files contain only research policy. `configs/runtime/default.yaml` contains only models,
workers, stores, budgets, and retry policy. Both schemas set `additionalProperties: false`, and the
validator also selects schemas by repository path, so moving runtime keys into a Research Profile
or research keys into Runtime Configuration fails CI.

## Data semantics

### Research Specification

The six blocks have these responsibilities:

- `objective`: statement and expected knowledge product;
- `target`: one of topics, entities/relations, questions, observation objects/properties, or novelty
  criteria;
- `scope`: one frontier strategy plus strategy-specific seeds/queries and optional source/time
  constraints;
- `evaluation`: declared named dimensions and a reusable ordered decision policy;
- `preservation`: explicit independent dimensions and optional named preset;
- `termination`: model-specific completion dimensions and rules, without runtime resource limits.

Runtime budgets are intentionally absent from `termination`; termination may name budget exhaustion
as an outcome condition, but the numeric ceilings belong to Runtime Configuration as required by
ADR-006.

### Evaluation and decision

EvaluationResult stores the evaluated subject, `source_group_id`, stage (`triage` or `full`), named
characteristics with scores and rationales, timestamps, and specification identity. Characteristics
are an open map, so direction-specific dimensions remain possible. The reserved universal property
`confidence` is forbidden.

Decision Policy is configuration data, not evaluation output. It contains ordered rules over named
dimensions and a fallback. QualificationDecision records the selected status, policy identity and
version, EvaluationResult identity, matched rule, rationale, and decision time. Tests apply two
different policies to one saved EvaluationResult to demonstrate reuse without reevaluation.

### Preservation

The general policy supports all values accepted by ADR-004. Phase 1 executable profiles narrow
history to `latest_only`. A policy below `evidence_fragments` must explicitly acknowledge the
reproducibility risk. Selecting `full_content` requires the explicit named profile `archival`.

A preserved-record schema requires `source_id`, `canonical_url`, `content_hash`, `retrieved_at`,
`published_at`, `parser_version`, and `extractor_version` for every policy combination. Fixtures
exercise both economical and minimal policies so identity cannot disappear when artifact or
knowledge retention is `none`.

### Extraction, sufficiency, and telemetry

ExtractionResult replaces universal `confidence` with `extraction_confidence`, adds
`CONTRADICTED`, and requires content identity and provenance fields. Evidence evaluation uses
`evidence_strength`; source evaluation uses `source_authority`.

Research Run Outcome permits exactly `SUFFICIENT`, `PARTIAL`, `ZERO`, `CONFLICT`, and `EXHAUSTED`.
Every outcome includes coverage, gaps, conflicts, a rationale, and recommended expansion; arrays
may be empty only when their semantics allow it. Research Run records specification/config/model
versions, processed content identities, decisions with rationales, expansion iterations, consumed
budget, and the final outcome.

Telemetry removes universal confidence aggregates, distinguishes triage/full evaluation events,
records named characteristics and separate qualification decisions, and reports one of the five
run outcomes.

## Normative documentation and compatibility

New normative documents describe Research Specification and Preservation. Existing extraction,
relevance, sufficiency, telemetry, and glossary documents are migrated from their incompatible
pre-ADR forms. Each incompatible contract is versioned `1.0`; cross-links and examples point to the
machine schema instead of maintaining a divergent inline source of truth.

Architecture, roadmap, repository/config/test indexes, root README, and changelog will be updated so
they no longer describe flat profiles, binary evaluation output, universal confidence, or the old
three-state sufficiency result. Accepted ADR text is not modified.

## Validation and tests

The implementation follows red-green-refactor:

1. Add contract tests and fixtures before schemas/validator behavior. The initial run must fail
   because the schemas and validation entry point do not exist.
2. Add the validator and schemas minimally until positive and negative fixture tests pass.
3. Add repository configuration/example validation, then migrate profiles and examples until it
   passes.
4. Update normative documentation and indexes, then run all repository checks.

Fixtures cover:

- the six specification blocks and all three frontier strategies;
- AM-1…AM-5 expressibility, with only AM-1/AM-2 accepted as executable Phase 1 profiles;
- all three preservation dimensions, the Phase 1 history restriction, explicit `archival`, risk
  acknowledgement, and invariant provenance/content identity;
- extensible EvaluationResult characteristics and absence of universal `confidence`;
- decision-policy reapplication;
- all five explained run outcomes;
- rejection of mixed Research Profile/Runtime Configuration and other invalid Phase 1 configs.

CI installs the development validation dependencies, runs `unittest`, validates tracked configs and
examples, and retains the existing naming, frontmatter, and repository-boundary checks. Test and CI
timeouts remain bounded by the existing job timeouts; no arbitrary wait is introduced.

## Non-goals

No ingestion, LLM invocation, persistence engine, graph/vector runtime, orchestration, end-to-end
run, provider evaluation, advanced source lineage, `full_history` implementation, public API, auth,
deployment, or production telemetry is added in P1-A.

## Acceptance mapping

Every issue requirement maps to a schema, executable/analytical example, fixture assertion,
normative contract update, or CI check. No default or embedded component code owns selection,
preservation, or termination criteria; they remain configuration data. The branch is complete only
when the focused contract suite, all repository validators, and fresh PR CI pass.
