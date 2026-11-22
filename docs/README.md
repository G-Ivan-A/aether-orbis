---
status: draft
version: 0.6
updated: 2026-10-23
temperature: 0.1
---

# Документация AetherOrbis

Индекс артефактов. Уровни соответствуют постановке подготовительного R&D (L1 — видение, L2 —
концепция и архитектура, L3 — структура репозитория, L4 — ADR и контракты).

| Уровень | Документ | Назначение |
| --- | --- | --- |
| L1 | [`vision.md`](vision.md) | миссия, цель, позиционирование в экосистеме, границы |
| L2 | [`concept.md`](concept.md) | компоненты, контракты, gates, конфигурируемость |
| L2 | [`architecture.md`](architecture.md) | диаграммы Mermaid, потоки данных, зоны ответственности |
| L4 | [`adr/README.md`](adr/README.md) | реестр архитектурных решений |
| L4 | [`standards/`](standards/) | контракты границ компонентов |
| L2 | [`analysis/`](analysis/) | аналитические документы, обосновывающие изменения контрактов |
| L4 | [`rfc/`](rfc/) | предложения с открытыми альтернативами и межрепозиторными последствиями |
| — | [`running-locally.md`](running-locally.md) | точные команды локального прогона и границы фазы 1 |
| — | [`roadmap.md`](roadmap.md) | фазы 0–5, задачи и зависимости, риски |

Ключевые документы, обосновывающие изменения контрактов:

- [`analysis/2026-09-02-acquisition-models-variation.md`](analysis/2026-09-02-acquisition-models-variation.md)
  — анализ вариативности моделей Acquisition.
- [`adr/2026-09-adr-004-preservation-policy.md`](adr/2026-09-adr-004-preservation-policy.md) —
  Preservation Policy.
- [`adr/2026-09-adr-005-evaluation-result.md`](adr/2026-09-adr-005-evaluation-result.md) —
  Evaluation Result и Decision Policy.
- [`adr/2026-09-adr-006-research-specification.md`](adr/2026-09-adr-006-research-specification.md) —
  Research Specification и исходы прогона.
- [`rfc/2026-10-multi-project-vps-platform.md`](rfc/2026-10-multi-project-vps-platform.md) —
  общая платформа нескольких ИИ-проектов на одном VPS (proposed), решения —
  [`adr/2026-10-adr-007-multi-project-deployment-topology.md`](adr/2026-10-adr-007-multi-project-deployment-topology.md)
  и [`adr/2026-10-adr-008-inter-project-api-contract.md`](adr/2026-10-adr-008-inter-project-api-contract.md);
  доказательная база — [`analysis/2026-10-22-multi-project-vps-constraints.md`](analysis/2026-10-22-multi-project-vps-constraints.md).
- [`rfc/2026-10-lean-global-compliance.md`](rfc/2026-10-lean-global-compliance.md) — Lean Global
  Compliance: правовой анализ 152-ФЗ / GDPR / CCPA для публичных профессиональных данных, гибрид
  «узел РФ + зарубежные вычисления» и анонимизация на границе (proposed), решение —
  [`adr/2026-10-adr-009-edge-anonymization-and-lean-hybrid.md`](adr/2026-10-adr-009-edge-anonymization-and-lean-hybrid.md);
  доказательная база — [`analysis/2026-10-23-lean-global-compliance-research.md`](analysis/2026-10-23-lean-global-compliance-research.md).

## Контракты

| Контракт | Граница |
| --- | --- |
| [`standards/research-specification-contract.md`](standards/research-specification-contract.md) | постановка Research Run и разделение profile/runtime |
| [`standards/preservation-contract.md`](standards/preservation-contract.md) | acquired artifact, derived knowledge и observation history |
| [`standards/extraction-contract.md`](standards/extraction-contract.md) | Extraction → всё, что ниже |
| [`standards/relevance-gate-contract.md`](standards/relevance-gate-contract.md) | EvaluationResult → QualificationDecision |
| [`standards/sufficiency-gate-contract.md`](standards/sufficiency-gate-contract.md) | Research Run → объяснимый outcome |
| [`standards/telemetry-contract.md`](standards/telemetry-contract.md) | все компоненты → наблюдаемость |
| [`standards/glossary.md`](standards/glossary.md) | единый источник истины по терминам |

Машиночитаемый источник полей контрактов — [`configs/schemas/`](../configs/schemas/). Валидируемые
примеры общей Research Specification для `AM-1`…`AM-5` находятся в
[`examples/research-specifications/`](../examples/research-specifications/); только профили `AM-1`
и `AM-2` в [`configs/directions/`](../configs/directions/) исполняемы в Phase 1.

## Правила именования файлов

Наследуются из `standards/file-naming.md` Хаба
([hybrid-Intelligence-lab](https://github.com/G-Ivan-A/hybrid-Intelligence-lab)):

| Каталог | Формат |
| --- | --- |
| `docs/analysis/` | `YYYY-MM-DD-name.md` |
| `docs/rfc/` | `YYYY-MM-name.md` или `YYYY-name.md` |
| `docs/adr/` | `YYYY-MM-adr-NNN-name.md` |

Проверяется скриптом [`tools/validate-file-naming.sh`](../tools/validate-file-naming.sh) в CI.

## Frontmatter

Каждый активный markdown-артефакт содержит `status`, `version`, `updated`, `temperature`;
governance-артефакты (ADR, RFC, контракты) дополнительно — `owner`, ADR — `decision-type`,
RFC — `rfc-scope`.
Поле `ai-generated` запрещено. Словари статусов:

| Класс | Допустимые статусы |
| --- | --- |
| Knowledge (vision, concept, architecture, roadmap, analysis) | `draft`, `reviewed`, `canonical`, `superseded` |
| Governance (adr, rfc, standards) | `draft`, `proposed`, `accepted`, `rejected`, `deprecated`, `superseded` |
