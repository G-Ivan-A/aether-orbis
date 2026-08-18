# configs — конфигурации направлений

Направление исследования задаётся YAML-конфигурацией. Добавление направления **не требует изменений
в коде модулей** — см. [`docs/concept.md`](../docs/concept.md), раздел 6.

| Путь | Назначение |
| --- | --- |
| `directions/<direction>/research-profile.yaml` | тема, критерии релевантности, пороги, бюджеты |
| `schemas/` | JSON Schema контрактов для валидации в CI |

Конфигурации **не содержат** секретов и ключей API: они передаются переменными окружения
`AETHER_ORBIS_*` (см. [ADR-003](../docs/adr/2026-08-adr-003-infrastructure.md)).

Направления MVP: `reputation-technologies`, `hub-practice-analysis`.
