# Phase 1 Contract Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver versioned, machine-validated Phase 1 contracts, executable AM-1/AM-2 Research Profiles, analytical AM-3…AM-5 examples, and CI-enforced separation from Runtime Configuration.

**Architecture:** JSON Schema Draft 2020-12 files are the contract source of truth and compose through stable `$id` values. A small Python module validates YAML/JSON artifacts, enforces cross-document invariants, and applies data-defined decision policies; `unittest` fixtures prove positive and negative behavior before repository profiles and documentation migrate.

**Tech Stack:** Python 3 standard library, PyYAML 6.x, jsonschema 4.x, JSON Schema Draft 2020-12, YAML, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-09-phase-1-contract-foundation-design.md`

## Global Constraints

- Implement accepted ADR-004, ADR-005, and ADR-006 without modifying their decisions.
- Require the six Research Specification blocks: `objective`, `target`, `scope`, `evaluation`, `preservation`, `termination`.
- Support frontier strategies `enumerate`, `expand`, and `query` in one specification contract.
- Permit only AM-1 and AM-2 as executable Phase 1 profiles; AM-3…AM-5 are analytical examples only.
- Permit only `observation_history: latest_only` in executable Phase 1 profiles; the general contract remains expressive for future values.
- Require explicit `archival` selection for `full_content` and explicit risk acceptance below `evidence_fragments`.
- Preserve provenance/content identity under every preservation policy.
- Forbid universal `confidence`; keep `extraction_confidence`, `evidence_strength`, and `source_authority` distinct.
- Keep Research Profile policy separate from Runtime Configuration models, workers, stores, budgets, and retries.
- Do not implement ingestion, LLM calls, stores, orchestration, provider evaluation, advanced lineage, full history, API, auth, deployment, or production telemetry.

---

## File structure

### Validation and tests

- Create `requirements-dev.txt`: validation dependencies used locally and in CI.
- Create `tools/contract_validation.py`: schema loading, document validation, cross-field checks,
  decision-policy application, and repository artifact discovery.
- Create `tools/validate-contracts.py`: executable CLI returning non-zero with path-qualified errors.
- Create `tests/test_contracts.py`: fixture validation, repository config validation, and policy reuse.
- Create `tests/fixtures/contracts/{valid,invalid}/`: hand-authored contract examples.

### Machine contracts

- Create `configs/schemas/research-specification.schema.json`.
- Create `configs/schemas/research-profile.schema.json`.
- Create `configs/schemas/runtime-configuration.schema.json`.
- Create `configs/schemas/preservation-policy.schema.json`.
- Create `configs/schemas/preserved-record.schema.json`.
- Create `configs/schemas/extraction-result.schema.json`.
- Create `configs/schemas/evaluation-result.schema.json`.
- Create `configs/schemas/decision-policy.schema.json`.
- Create `configs/schemas/qualification-decision.schema.json`.
- Create `configs/schemas/research-run-outcome.schema.json`.
- Create `configs/schemas/research-run.schema.json`.
- Create `configs/schemas/telemetry-event.schema.json`.

### Profiles and examples

- Replace both `configs/directions/*/research-profile.yaml` files with executable Phase 1 profiles.
- Create `configs/runtime/default.yaml` with runtime-only controls.
- Create `examples/research-specifications/am-{1..5}-*.yaml`; AM-1/AM-2 mirror executable use,
  AM-3…AM-5 demonstrate analytical expressibility.

### Normative and project documentation

- Create `docs/standards/research-specification-contract.md` and
  `docs/standards/preservation-contract.md`.
- Rewrite incompatible v1.0 forms in extraction, relevance, sufficiency, telemetry, and glossary.
- Synchronize `docs/architecture.md`, `docs/roadmap.md`, `docs/README.md`, `configs/README.md`,
  `tests/README.md`, `README.md`, and `CHANGELOG.md`.
- Update `.github/workflows/ci.yml` and remove the PR placeholder `.gitkeep`.

---

### Task 1: Establish the failing contract suite

**Files:**

- Create: `requirements-dev.txt`
- Create: `tests/test_contracts.py`
- Create: `tests/fixtures/contracts/valid/*.yaml`
- Create: `tests/fixtures/contracts/invalid/*.yaml`

**Interfaces:**

- Consumes: future `tools.contract_validation` public functions.
- Produces: executable acceptance tests and independent literal fixtures for every issue invariant.

- [ ] **Step 1: Declare development dependencies**

```text
jsonschema[format]>=4.23,<5
PyYAML>=6,<7
```

- [ ] **Step 2: Write tests against the wished-for validator API**

```python
from pathlib import Path
import unittest

from tools.contract_validation import (
    apply_decision_policy,
    validate_document,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "configs" / "schemas"
FIXTURES = ROOT / "tests" / "fixtures" / "contracts"


class ContractFixtureTests(unittest.TestCase):
    def test_valid_fixtures_satisfy_their_contracts(self):
        for path in sorted((FIXTURES / "valid").glob("*.yaml")):
            schema_name, _, _ = path.name.partition("--")
            self.assertEqual([], validate_document(path, schema_name, SCHEMAS), path)

    def test_invalid_fixtures_are_rejected(self):
        for path in sorted((FIXTURES / "invalid").glob("*.yaml")):
            schema_name, _, _ = path.name.partition("--")
            self.assertNotEqual([], validate_document(path, schema_name, SCHEMAS), path)

    def test_saved_evaluation_can_be_redecided_without_reevaluation(self):
        evaluation = FIXTURES / "valid" / "evaluation-result.schema.json--custom.yaml"
        strict = FIXTURES / "valid" / "decision-policy.schema.json--strict.yaml"
        permissive = FIXTURES / "valid" / "decision-policy.schema.json--permissive.yaml"
        self.assertEqual("CONDITIONAL", apply_decision_policy(evaluation, strict))
        self.assertEqual("QUALIFIED", apply_decision_policy(evaluation, permissive))

```

- [ ] **Step 3: Add literal fixtures covering every required behavior**

Use the schema filename, two hyphens, and the case name so tests choose the schema without a
manifest. Required valid cases are:

```text
research-specification.schema.json--am1-enumerate.yaml
research-specification.schema.json--am2-expand.yaml
research-specification.schema.json--am3-query.yaml
research-specification.schema.json--am4-observation.yaml
research-specification.schema.json--am5-discovery.yaml
research-profile.schema.json--phase1-am1.yaml
research-profile.schema.json--phase1-am2.yaml
preservation-policy.schema.json--economical.yaml
preservation-policy.schema.json--archival.yaml
preserved-record.schema.json--identity-with-none.yaml
extraction-result.schema.json--contradicted.yaml
evaluation-result.schema.json--custom.yaml
decision-policy.schema.json--strict.yaml
decision-policy.schema.json--permissive.yaml
qualification-decision.schema.json--qualified.yaml
research-run-outcome.schema.json--sufficient.yaml
research-run-outcome.schema.json--partial.yaml
research-run-outcome.schema.json--zero.yaml
research-run-outcome.schema.json--conflict.yaml
research-run-outcome.schema.json--exhausted.yaml
research-run.schema.json--complete.yaml
runtime-configuration.schema.json--default.yaml
telemetry-event.schema.json--full-evaluation.yaml
```

Required invalid cases remove one specification block, use an unknown frontier strategy, mark AM-3
executable in Phase 1, use `full_history` in a Phase 1 profile, select `full_content` without
`archival`, omit the low-retention risk acceptance, omit preserved content identity, use universal
`confidence` in extraction/evaluation/telemetry, omit `source_group_id`, use an unexplained outcome,
mix runtime keys into a profile, and mix research keys into runtime configuration.

- [ ] **Step 4: Run RED and confirm the expected missing-module failure**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: ERROR importing `tools.contract_validation`; this proves the suite precedes production
validation code.

---

### Task 2: Implement schemas and validation (GREEN)

**Files:**

- Create: `configs/schemas/*.schema.json`
- Create: `tools/__init__.py`
- Create: `tools/contract_validation.py`
- Create: `tools/validate-contracts.py`
- Modify: `tests/test_contracts.py`

**Interfaces:**

- Consumes: YAML/JSON paths, schema filenames, and the schema directory.
- Produces: `validate_document(path, schema_name, schema_dir) -> list[str]`,
  `apply_decision_policy(evaluation, policy) -> str`, and
  `validate_repository(root) -> list[str]`.

- [ ] **Step 1: Add Draft 2020-12 schemas with closed object boundaries**

Each schema must use this identity pattern (shown for Research Specification, with the filename and
title changed to the concrete contract in every other file):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://aether-orbis.dev/schemas/research-specification.schema.json",
  "title": "ResearchSpecification",
  "type": "object",
  "required": [],
  "properties": {},
  "additionalProperties": false
}
```

Populate the exact required fields and enums from the design. Use `if`/`then` in
`preservation-policy.schema.json` for explicit archival and risk acceptance. Use `if`/`then` in
`research-profile.schema.json` to narrow executable Phase 1 profiles. Use `propertyNames` with
`not: {"const": "confidence"}` for open characteristic/metric maps.

- [ ] **Step 2: Implement document and schema loading**

```python
def load_document(path: Path) -> object:
    with path.open(encoding="utf-8") as stream:
        if path.suffix == ".json":
            return json.load(stream)
        return yaml.safe_load(stream)


def load_schema_registry(schema_dir: Path) -> tuple[dict[str, object], Registry]:
    schemas = {}
    resources = []
    for path in sorted(schema_dir.glob("*.schema.json")):
        schema = load_document(path)
        Draft202012Validator.check_schema(schema)
        schemas[path.name] = schema
        resources.append((schema["$id"], Resource.from_contents(schema)))
    return schemas, Registry().with_resources(resources)
```

- [ ] **Step 3: Implement schema errors plus cross-field invariants**

```python
def validate_document(path: Path, schema_name: str, schema_dir: Path) -> list[str]:
    document = load_document(path)
    schemas, registry = load_schema_registry(schema_dir)
    validator = Draft202012Validator(
        schemas[schema_name], registry=registry, format_checker=FormatChecker()
    )
    errors = [format_schema_error(error) for error in validator.iter_errors(document)]
    errors.extend(validate_policy_dimensions(document, schema_name))
    return sorted(errors)
```

`validate_policy_dimensions` must reject policy conditions whose `dimension` is absent from the
specification's declared `evaluation.dimensions`, and EvaluationResult characteristics named
`confidence`. Error messages include the failing property path.

- [ ] **Step 4: Implement deterministic decision-policy reuse**

```python
OPERATORS = {
    "gte": lambda actual, expected: actual >= expected,
    "gt": lambda actual, expected: actual > expected,
    "lte": lambda actual, expected: actual <= expected,
    "lt": lambda actual, expected: actual < expected,
    "eq": lambda actual, expected: actual == expected,
}


def apply_decision_policy(evaluation, policy) -> str:
    evaluation_doc = load_document(Path(evaluation)) if isinstance(evaluation, (str, Path)) else evaluation
    policy_doc = load_document(Path(policy)) if isinstance(policy, (str, Path)) else policy
    scores = {name: value["score"] for name, value in evaluation_doc["characteristics"].items()}
    for rule in policy_doc["rules"]:
        if all(OPERATORS[c["operator"]](scores[c["dimension"]], c["value"])
               for c in rule["all"]):
            return rule["decision"]
    return policy_doc["fallback"]
```

- [ ] **Step 5: Implement repository discovery and CLI**

```python
ARTIFACTS = (
    ("configs/directions/*/research-profile.yaml", "research-profile.schema.json"),
    ("configs/runtime/*.yaml", "runtime-configuration.schema.json"),
    ("examples/research-specifications/*.yaml", "research-specification.schema.json"),
)


def validate_repository(root: Path) -> list[str]:
    errors = []
    for pattern, schema in ARTIFACTS:
        for path in sorted(root.glob(pattern)):
            errors.extend(f"{path.relative_to(root)}: {error}"
                          for error in validate_document(path, schema, root / "configs" / "schemas"))
    return errors
```

The CLI prints each error to stderr and exits 1 when errors exist; otherwise it prints the number of
validated tracked artifacts and exits 0.

- [ ] **Step 6: Run GREEN, then mutation-check the prohibitions**

Run:

```bash
python3 -m unittest discover -s tests -v
python3 tools/validate-contracts.py
```

Expected: all schema-fixture and decision-policy tests pass. Running the repository validation CLI
still reports the two legacy profiles until Task 3.
Temporarily change a valid fixture to `confidence`, `full_history`, and a mixed runtime key one at a
time; confirm the corresponding test fails, then restore each fixture.

---

### Task 3: Migrate executable profiles and add AM-1…AM-5 examples

**Files:**

- Modify: `configs/directions/hub-practice-analysis/research-profile.yaml`
- Modify: `configs/directions/reputation-technologies/research-profile.yaml`
- Create: `configs/runtime/default.yaml`
- Create: `examples/research-specifications/am-1-domain-monitoring.yaml`
- Create: `examples/research-specifications/am-2-entity-relationship.yaml`
- Create: `examples/research-specifications/am-3-question-research.yaml`
- Create: `examples/research-specifications/am-4-market-monitoring.yaml`
- Create: `examples/research-specifications/am-5-open-discovery.yaml`

**Interfaces:**

- Consumes: research-profile, research-specification, preservation, decision-policy, and runtime
  schemas from Task 2.
- Produces: two executable Phase 1 profiles, one runtime-only configuration, and five validated
  expressibility examples.

- [ ] **Step 1: Replace the two flat profiles**

First add the repository-level acceptance test and run it against the legacy profiles:

```python
from tools.contract_validation import validate_repository


def test_tracked_profiles_examples_and_runtime_config_are_valid(self):
    self.assertEqual([], validate_repository(ROOT))
```

Run `python3 -m unittest tests.test_contracts.ContractFixtureTests.test_tracked_profiles_examples_and_runtime_config_are_valid -v`.
Expected: FAIL with path-qualified validation errors for both legacy profiles. Then replace the
profiles and add the remaining tracked artifacts below.

Each profile has this exact outer structure and all six explicit specification blocks:

```yaml
schema_version: "1.0"
profile_id: hub-practice-analysis
profile_version: "1.0"
phase: 1
support: executable
acquisition_model: AM-1-or-AM-2
specification:
  objective: {}
  target: {}
  scope: {}
  evaluation: {}
  preservation: {}
  termination: {}
```

AM-1 uses topics + `enumerate`, monitoring/economical preservation, and window-coverage
termination. AM-2 uses seed entities/relation types + `expand`, graph-oriented derived knowledge,
and neighborhood-completeness/saturation termination. Neither contains runtime controls.

- [ ] **Step 2: Add runtime-only configuration**

```yaml
schema_version: "1.0"
runtime_id: phase-1-default
runtime_version: "1.0"
models:
  extraction: cost-sensitive
  triage: cost-sensitive
  full_evaluation: mid-tier
  knowledge_building: mid-tier
workers:
  concurrency: 4
stores:
  source: object-store
  knowledge: graph-store
  retrieval: vector-index
budgets:
  max_iterations: 3
  max_cost_rub: 150
retries:
  max_attempts: 3
```

- [ ] **Step 3: Add five general-specification examples**

Use the model mappings from the accepted analysis: AM-1=`enumerate` topics; AM-2=`expand` entities;
AM-3=`query` questions; AM-4=`enumerate` observation objects/properties with conceptual
`full_history`; AM-5=`expand` novelty criteria. Mark no example executable; only files under
`configs/directions/` are executable profiles.

- [ ] **Step 4: Validate repository artifacts and focused tests**

Run:

```bash
python3 tools/validate-contracts.py
python3 -m unittest discover -s tests -v
```

Expected: all tracked profiles, runtime configuration, and five examples validate; all contract
tests pass.

- [ ] **Step 5: Commit contracts, validator, tests, configs, and examples atomically**

```bash
git add requirements-dev.txt tools configs tests examples
git commit -m "feat(contracts): add Phase 1 schemas" -m "Refs #35"
```

---

### Task 4: Migrate normative contracts to accepted ADR semantics

**Files:**

- Create: `docs/standards/research-specification-contract.md`
- Create: `docs/standards/preservation-contract.md`
- Modify: `docs/standards/extraction-contract.md`
- Modify: `docs/standards/relevance-gate-contract.md`
- Modify: `docs/standards/sufficiency-gate-contract.md`
- Modify: `docs/standards/telemetry-contract.md`
- Modify: `docs/standards/glossary.md`

**Interfaces:**

- Consumes: accepted ADR text and schemas from Task 2.
- Produces: human-readable normative v1.0 contracts whose examples validate against the schemas.

- [ ] **Step 1: Write Research Specification and Preservation contracts**

Both use RFC 2119 / BCP 14 language, link the glossary and governing ADR, identify provider,
consumer, scope, exclusions, obligations, schema path, valid example, Definition of Done,
escalations, rationale, and related artifacts. Specify general-vs-Phase-1 narrowing explicitly.

- [ ] **Step 2: Rewrite extraction and relevance contracts**

Extraction v1.0 requires content identity, `extraction_confidence`, evidence, and four relation
states including `CONTRADICTED`. Relevance v1.0 defines EvaluationResult separately from
QualificationDecision, requires both triage and full stages, persists rejected evaluation data,
requires `source_group_id`, and documents exact-URL/hash lineage limitations.

- [ ] **Step 3: Rewrite sufficiency and telemetry contracts**

Sufficiency v1.0 uses the five uppercase run outcomes and mandatory explanation fields. Telemetry
v1.0 distinguishes evaluation from decision events, removes universal confidence aggregates, and
reports the five final outcomes.

- [ ] **Step 4: Rewrite glossary terms**

Remove `Confidence`; define Research Specification, Research Run, Research Profile, Runtime
Configuration, Preservation Policy, EvaluationResult, Decision Policy, QualificationDecision,
`source_group_id`, the three distinct confidence/strength/authority dimensions, `CONTRADICTED`, and
all five run outcomes. Ensure contract docs link rather than redefine glossary definitions.

- [ ] **Step 5: Check normative files**

Run:

```bash
bash tools/validate-frontmatter.sh
rg -n '\bconfidence\b|relevant|not_relevant|insufficient|sufficient' docs/standards
git diff --check
```

Expected: frontmatter passes; search hits exist only in explicit migration/prohibition context or
qualified terms such as `extraction_confidence`; no obsolete normative fields remain.

- [ ] **Step 6: Commit normative migration**

```bash
git add docs/standards
git commit -m "docs(contracts)!: align standards with ADRs" -m "BREAKING CHANGE: extraction, relevance, sufficiency, and telemetry contracts use v1.0 ADR-004/005/006 semantics.\n\nRefs #35"
```

---

### Task 5: Synchronize project documentation and CI

**Files:**

- Modify: `docs/architecture.md`
- Modify: `docs/roadmap.md`
- Modify: `docs/README.md`
- Modify: `configs/README.md`
- Modify: `tests/README.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `.github/workflows/ci.yml`
- Delete: `.gitkeep`

**Interfaces:**

- Consumes: implemented contracts, paths, commands, and profile semantics.
- Produces: consistent navigation, Phase 1 status, contributor commands, and enforcing CI.

- [ ] **Step 1: Update architecture and roadmap**

Replace the old three-way sufficiency flow with five explained outcomes; show Research Profile and
Runtime Configuration as separate inputs; link new contracts and schemas; mark P1-A deliverables
without claiming P1-B/P1-C runtime completion. Bump changed knowledge-document versions and
`updated: 2026-09-09`.

- [ ] **Step 2: Update indexes, README files, and changelog**

Document schema locations, validation commands, two executable profiles, five analytical examples,
dependency installation, and the new Phase 1 contract foundation. Remove claims that tests are a
no-op or that only flat direction profiles exist.

- [ ] **Step 3: Make CI execute contract validation**

Replace the inline legacy weight checker and no-op test with:

```yaml
- name: Install test dependencies
  run: python3 -m pip install --user --quiet -r requirements-dev.txt
- name: Validate contract artifacts
  run: python3 tools/validate-contracts.py
- name: Run tests
  run: python3 -m unittest discover -s tests -v
```

Keep existing job timeout values and all three repository validators.

- [ ] **Step 4: Run the complete local CI surface**

```bash
python3 -m pip install --user -r requirements-dev.txt
python3 tools/validate-contracts.py
python3 -m unittest discover -s tests -v
bash tools/validate-file-naming.sh
bash tools/validate-frontmatter.sh
bash tools/validate-repo-boundary.sh
git diff --check
```

Expected: every command exits 0 with no warnings from project code.

- [ ] **Step 5: Commit integration and CI**

```bash
git add .github/workflows/ci.yml CHANGELOG.md README.md configs/README.md docs/README.md docs/architecture.md docs/roadmap.md tests/README.md .gitkeep
git commit -m "ci: enforce Phase 1 contracts" -m "Refs #35"
```

---

### Task 6: Final review, push, PR, and fresh CI

**Files:**

- Review: all files changed from `main`.
- Update externally: PR 38 title and description.

**Interfaces:**

- Consumes: complete branch and GitHub PR state.
- Produces: clean pushed branch, review-ready PR, and fresh CI evidence tied to HEAD.

- [ ] **Step 1: Fetch and merge current default branch if it advanced**

```bash
git fetch origin main
git merge --no-edit origin/main
```

Resolve only in-scope conflicts; rerun the full local CI surface after a merge.

- [ ] **Step 2: Perform self-review**

```bash
git status --short --branch
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
git diff --check origin/main...HEAD
gh pr diff 38 --repo G-Ivan-A/aether-orbis
```

Verify every issue acceptance item has a test/config/schema/doc mapping, accepted ADRs are unchanged,
no unrelated feature was removed, no runtime data or secrets were added, and the tree is clean.

- [ ] **Step 3: Run final verification and push only the prepared branch**

```bash
git branch --show-current
git push origin issue-35-8a44226193b1
```

The branch check must print `issue-35-8a44226193b1` before push.

- [ ] **Step 4: Update PR 38**

Set the title to `contracts: add executable Phase 1 research specifications`. Replace the placeholder
body with: issue link; reproduction of legacy validation gaps; schema/validator/profile/doc summary;
automated test evidence; explicit AM-1/AM-2 vs AM-3…AM-5 scope; breaking contract versions; AI
disclosure; `Closes #35`.

- [ ] **Step 5: Verify fresh CI by timestamp and SHA**

```bash
gh run list --repo G-Ivan-A/aether-orbis --branch issue-35-8a44226193b1 --limit 5 --json databaseId,conclusion,createdAt,headSha,workflowName
```

Confirm the relevant run's `headSha` equals local `HEAD` and its timestamp follows the push. For
every non-passing run, save logs under ignored `ci-logs/`, read them in chunks no larger than 1500
lines, fix the root cause with a reproducing test, recommit, repush, and repeat:

```bash
mkdir -p ci-logs
for run_id in $(gh run list --repo G-Ivan-A/aether-orbis --branch issue-35-8a44226193b1 \
  --limit 5 --json databaseId,conclusion --jq '.[] | select(.conclusion != "success") | .databaseId'); do
  gh run view "$run_id" --repo G-Ivan-A/aether-orbis --log > "ci-logs/ci-$run_id.log"
done
```

- [ ] **Step 6: Mark ready and report**

```bash
gh pr ready 38 --repo G-Ivan-A/aether-orbis
gh pr view 38 --repo G-Ivan-A/aether-orbis --json url,isDraft,mergeable,mergeStateStatus,statusCheckRollup,headRefOid
```

Report the PR URL, commits, focused/full test results, CI run ID/SHA/timestamp, clean working tree,
and any explicitly deferred non-goals.
