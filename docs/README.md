---
status: draft
version: 0.1
updated: 2026-08-18
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
| — | [`roadmap.md`](roadmap.md) | фазы 0–5, задачи и зависимости, риски |

## Контракты

| Контракт | Граница |
| --- | --- |
| [`standards/extraction-contract.md`](standards/extraction-contract.md) | Extraction → всё, что ниже |
| [`standards/relevance-gate-contract.md`](standards/relevance-gate-contract.md) | Extraction → Graph / Context Builder |
| [`standards/sufficiency-gate-contract.md`](standards/sufficiency-gate-contract.md) | Context → Analysis |
| [`standards/telemetry-contract.md`](standards/telemetry-contract.md) | все компоненты → наблюдаемость |
| [`standards/glossary.md`](standards/glossary.md) | единый источник истины по терминам |

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
governance-артефакты (ADR, контракты) дополнительно — `owner`, ADR — `decision-type`.
Поле `ai-generated` запрещено. Словари статусов:

| Класс | Допустимые статусы |
| --- | --- |
| Knowledge (vision, concept, architecture, roadmap, analysis) | `draft`, `reviewed`, `canonical`, `superseded` |
| Governance (adr, standards) | `draft`, `proposed`, `accepted`, `rejected`, `deprecated`, `superseded` |
