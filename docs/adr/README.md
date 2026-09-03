---
status: draft
version: 0.2
updated: 2026-09-02
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
| ADR-004 | Preservation Policy: независимые измерения вместо линейной шкалы | product | proposed | [2026-09-adr-004-preservation-policy.md](2026-09-adr-004-preservation-policy.md) |
| ADR-005 | Evaluation Result и отделение decision layer | product | proposed | [2026-09-adr-005-evaluation-result.md](2026-09-adr-005-evaluation-result.md) |
| ADR-006 | Обобщённая Research Specification и состояния исхода прогона | product | proposed | [2026-09-adr-006-research-specification.md](2026-09-adr-006-research-specification.md) |

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

## Проекты ADR концептуального пересмотра (issue [#29](https://github.com/G-Ivan-A/aether-orbis/issues/29))

ADR-004, ADR-005 и ADR-006 подготовлены как **проекты** на основании
[анализа вариативности моделей Acquisition](https://github.com/G-Ivan-A/aether-orbis/blob/main/docs/analysis/2026-09-02-acquisition-models-variation.md).
Изменения контрактов в
[`docs/standards/`](https://github.com/G-Ivan-A/aether-orbis/tree/main/docs/standards)
выполняются отдельной задачей и только после принятия соответствующего ADR.
