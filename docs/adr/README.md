---
status: draft
version: 0.5
updated: 2026-10-23
temperature: 0.1
---

# ADR Registry — AetherOrbis

Реестр архитектурных решений. Именование файлов и структура документов соответствуют стандартам Хаба
`standards/file-naming.md` и `standards/adr-structure-standard.md`
([hybrid-Intelligence-lab](https://github.com/G-Ivan-A/hybrid-Intelligence-lab)):
`YYYY-MM-adr-NNN-short-title.md`, стабильный идентификатор — `ADR-NNN`.

| ID | Решение | Тип | Статус | Файл |
| --- | --- | --- | --- | --- |
| ADR-001 | Технологический стек | product | proposed | [2026-08-adr-001-tech-stack.md](2026-08-adr-001-tech-stack.md) |
| ADR-002 | Маршрутизация моделей по ролям операций | product | proposed | [2026-08-adr-002-model-routing.md](2026-08-adr-002-model-routing.md) |
| ADR-003 | Инфраструктура: serverless-first с VPS fallback | runtime | proposed | [2026-08-adr-003-infrastructure.md](2026-08-adr-003-infrastructure.md) |
| ADR-004 | Preservation Policy: независимые измерения вместо линейной шкалы | product | accepted | [2026-09-adr-004-preservation-policy.md](2026-09-adr-004-preservation-policy.md) |
| ADR-005 | Evaluation Result и отделение decision layer | product | accepted | [2026-09-adr-005-evaluation-result.md](2026-09-adr-005-evaluation-result.md) |
| ADR-006 | Обобщённая Research Specification и состояния исхода прогона | product | accepted | [2026-09-adr-006-research-specification.md](2026-09-adr-006-research-specification.md) |
| ADR-007 | Топология развёртывания нескольких проектов на одном хосте, изоляция и суверенитет данных | runtime | proposed | [2026-10-adr-007-multi-project-deployment-topology.md](2026-10-adr-007-multi-project-deployment-topology.md) |
| ADR-008 | Межпроектный API-контракт: асинхронный Job API, переносимый на брокер | runtime | proposed | [2026-10-adr-008-inter-project-api-contract.md](2026-10-adr-008-inter-project-api-contract.md) |
| ADR-009 | Анонимизация на границе и дешёвый гибрид «узел РФ + зарубежные вычисления» для ПДн из публичных источников | runtime | proposed | [2026-10-adr-009-edge-anonymization-and-lean-hybrid.md](2026-10-adr-009-edge-anonymization-and-lean-hybrid.md) |

## Соответствие исходной постановке задачи

Issue [#1](https://github.com/G-Ivan-A/aether-orbis/issues/1) называет файлы как `001-tech-stack.md`,
`002-model-routing.md`, `003-infrastructure.md`. Та же issue требует строить структуру по стандартам
Хаба, а `standards/file-naming.md` предписывает для Spoke-репозиториев хронологический префикс.
Приоритет отдан стандарту Хаба; соответствие имён:

| Имя из issue | Фактический файл |
| --- | --- |
| `docs/adr/001-tech-stack.md` | [`2026-08-adr-001-tech-stack.md`](2026-08-adr-001-tech-stack.md) |
| `docs/adr/002-model-routing.md` | [`2026-08-adr-002-model-routing.md`](2026-08-adr-002-model-routing.md) |
| `docs/adr/003-infrastructure.md` | [`2026-08-adr-003-infrastructure.md`](2026-08-adr-003-infrastructure.md) |

## Принятые ADR концептуального пересмотра (issue [#29](https://github.com/G-Ivan-A/aether-orbis/issues/29))

ADR-004, ADR-005 и ADR-006 приняты после review на основании
[анализа вариативности моделей Acquisition](https://github.com/G-Ivan-A/aether-orbis/blob/main/docs/analysis/2026-09-02-acquisition-models-variation.md).
Исполняемые изменения контрактов в
[`docs/standards/`](https://github.com/G-Ivan-A/aether-orbis/tree/main/docs/standards)
выполняются в рамках Phase 1 P1-A.

## Предложенные ADR мульти-проектной платформы (issue [#44](https://github.com/G-Ivan-A/aether-orbis/issues/44))

ADR-007 и ADR-008 предложены на основании
[RFC: Общая платформа развёртывания нескольких ИИ-проектов](../rfc/2026-10-multi-project-vps-platform.md)
и [анализа конфликтов](../analysis/2026-10-22-multi-project-vps-constraints.md). При принятии они
частично замещают ADR-003 (пункты 1–4 и раздел миграции) и уточняют ADR-001 (observability);
конфликты аннотированы в тексте этих ADR, решения ADR-003 и ADR-001 до принятия не меняются.

## Предложенный ADR Lean Global Compliance (issue [#46](https://github.com/G-Ivan-A/aether-orbis/issues/46))

ADR-009 предложен на основании
[RFC: Lean Global Compliance](../rfc/2026-10-lean-global-compliance.md) и
[правовой и ценовой доказательной базы](../analysis/2026-10-23-lean-global-compliance-research.md).
При принятии он уточняет класс D2 и S-5 ADR-007 подклассами D2-V / D2-R / D2-P / D1-A, допускает для
AetherOrbis гибрид H1 на ступени 0 и уточняет ADR-003 п. 3 и ADR-002 (граница анонимизации до вызова
LLM). Конфликты аннотированы в тексте ADR-007 и ADR-003; их решения до принятия не меняются.
