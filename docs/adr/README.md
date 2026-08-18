---
status: draft
version: 0.1
updated: 2026-08-18
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
