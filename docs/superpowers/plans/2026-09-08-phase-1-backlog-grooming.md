# Phase 1 Backlog Grooming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace stale Phase 1 issues #3–#8 with a minimal sequential backlog aligned with accepted ADR-004, ADR-005, and ADR-006.

**Architecture:** Treat GitHub issue state as the deliverable. Close the six pre-ADR tickets with traceable explanations, then create three dependency-ordered autonomous blocks: contracts/configuration, acquisition core, and persistence/orchestration/evidence for both Phase 1 acquisition models.

**Tech Stack:** GitHub Issues and Pull Requests via `gh`; Markdown repository documentation; existing shell validators.

**Spec:** [Issue #33](https://github.com/G-Ivan-A/aether-orbis/issues/33)

## Global Constraints

- Work only on Phase 1 from `docs/roadmap.md`; do not move Phase 2+ functionality into the replacement backlog.
- Use accepted ADR-004, ADR-005, and ADR-006 as requirements and link them with absolute URLs.
- Replacement issues must be autonomous, coarse-grained, sequentially executable, and free of intermediate approval gates.
- Preserve Phase 1 decisions: only `AM-1` and `AM-2` receive executable configurations and end-to-end evaluation; `observation_history = latest_only`; `archival` only when explicit; `source_group_id` only by canonical URL or exact content hash.

---

### Task 1: Replace stale Phase 1 tickets

**Files:**
- Modify: GitHub issues `#3` through `#8`

**Interfaces:**
- Consumes: accepted architecture from PRs #30 and #32 and ADR-004/005/006
- Produces: closed legacy issues, each with a concise reason and pointer to issue #33

- [ ] **Step 1: Record the audit baseline**

Read each issue body and verify that #3–#8 remain open immediately before mutation.

- [ ] **Step 2: Close each legacy issue with an explicit reason**

Use `gh issue close <number> --repo G-Ivan-A/aether-orbis --comment '<reason>'` for #3–#8. State whether the ticket is stale, contradicts an accepted ADR, or is being consolidated because its isolated delivery cannot satisfy the end-to-end acceptance criteria.

- [ ] **Step 3: Verify closure and explanations**

Run `gh issue view` for #3–#8 and confirm `state=CLOSED` and a final explanatory comment exists for each.

### Task 2: Create the sequential replacement backlog

**Files:**
- Create: three GitHub issues in `G-Ivan-A/aether-orbis`

**Interfaces:**
- Consumes: the audit and accepted ADR requirements
- Produces: Block A contract/configuration issue; Block B acquisition-core issue blocked by A; Block C persistence/orchestration/evidence issue blocked by B

- [ ] **Step 1: Create Block A — contracts and executable specifications**

The issue must require contract migration implied by ADR-004/005/006, schemas and validation, separation of Research Profile and Runtime Configuration, valid examples for all five models, and executable Phase 1 profiles only for AM-1/AM-2. Its Definition of Done must include contract/config tests and CI validation.

- [ ] **Step 2: Create Block B — acquisition and evaluation core**

The issue must require ingestion/extraction, provenance/content identity, source grouping by canonical URL or exact hash, triage and full `EvaluationResult`, a replayable decision layer, and preservation driven solely by the specification. It must be blocked only by Block A and include unit/integration/contract tests.

- [ ] **Step 3: Create Block C — storage, orchestration, and Phase 1 proof**

The issue must require evidence-led graph/vector persistence, a reproducible graph-store decision and ADR-001 update, Research Run recording, end-to-end orchestration, and automated AM-1/AM-2 scenarios. It must be blocked only by Block B and explicitly defer Phase 2+ model routing, provider evaluation, advanced lineage, history, public API, auth, and deployment.

- [ ] **Step 4: Verify issue shape**

Confirm all three issues are open, have absolute ADR links, have exactly one linear dependency after the first, and contain no intermediate approval requirement or stale `confidence`/binary-only contract.

### Task 3: Update repository traceability and prepare review

**Files:**
- Modify: `docs/roadmap.md`
- Delete: `.gitkeep`
- Modify: PR #34 title and description
- Modify: issue #33 project/status metadata or labels

**Interfaces:**
- Consumes: final replacement issue numbers from Task 2
- Produces: roadmap links that no longer point at closed Phase 1 tickets; review-ready PR #34 and issue #33

- [ ] **Step 1: Add a failing repository check for stale Phase 1 links**

Run a targeted script that asserts `docs/roadmap.md` references the new issue numbers and does not use #3–#8 as active Phase 1 tasks. Confirm it fails before editing the roadmap.

- [ ] **Step 2: Update the Phase 1 roadmap and dependency table**

Replace T1.1–T1.6 with the three autonomous blocks and their new links. Keep Phase 2–5 scope unchanged while updating downstream Phase 2 dependency references to the final Phase 1 block.

- [ ] **Step 3: Run repository validation**

Run `git diff --check`, `bash tools/validate-file-naming.sh`, `bash tools/validate-frontmatter.sh`, and `bash tools/validate-repo-boundary.sh`; rerun the targeted stale-link check and confirm it passes.

- [ ] **Step 4: Commit and push the repository change**

Remove the placeholder `.gitkeep`, commit the roadmap and plan atomically with a clear documentation commit message, and push only `issue-33-6fc95406e78a`.

- [ ] **Step 5: Prepare PR #34 and issue #33 for review**

Replace the WIP PR title/body with the audit, closure list, replacement issue list, scope decisions, and validation evidence. Apply the repository's available review-status mechanism to issue #33; if no project status exists, apply or create the `review` label and document that choice.

- [ ] **Step 6: Final verification**

Inspect `gh pr diff 34`, verify the worktree is clean, verify PR checks are newer than the pushed commit and passing, and run `gh pr ready 34`.
