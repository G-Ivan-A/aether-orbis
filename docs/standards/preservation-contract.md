---
status: proposed
version: 1.0
updated: 2026-09-09
temperature: 0.1
owner: G-Ivan-A
---

# Контракт Preservation

Нормативная лексика по RFC 2119 / BCP 14: **ДОЛЖНО** (MUST), **НЕ ДОЛЖНО** (MUST NOT),
**СЛЕДУЕТ** (SHOULD), **НЕ СЛЕДУЕТ** (SHOULD NOT), **МОЖНО** (MAY). Термины определены в
[`glossary.md`](glossary.md). Решения этого контракта подчиняются
[ADR-004](../adr/2026-09-adr-004-preservation-policy.md).

## Стороны и область

| Сторона | Роль |
| --- | --- |
| Поставщик | Research Specification и компонент acquisition |
| Потребитель | Source Store, Knowledge Store, Research Run и аудит |
| Владелец контракта | G-Ivan-A |

**Область:** декларация того, что сохраняется после получения источника, и минимальная идентичность
контента, сохраняемая при любом выборе.

**Вне области:** конкретная СУБД или object store, сроки физического хранения, дедупликация между
разными URL и полная lineage-модель.

## Обязательства

### O-1. Три независимых измерения

Preservation Policy **ДОЛЖНА** задавать все три измерения независимо:

| Измерение | Допустимые значения |
| --- | --- |
| `acquired_artifact` | `none`, `metadata`, `summary`, `evidence_fragments`, `full_content` |
| `derived_knowledge` | `none`, `claims`, `claims_and_relations`, `full_knowledge_product` |
| `observation_history` | `none`, `latest_only`, `full_history` |

Выбор одного измерения **НЕ ДОЛЖЕН** неявно менять другое.

Payload Preserved Record **ДОЛЖЕН** соответствовать выбранному уровню. `metadata` допускает только
объект metadata; `summary` добавляет summary; `evidence_fragments` включает metadata, summary и
проверяемые fragments; `full_content` содержит metadata, media type и полный content. Аналогично,
`claims`, `claims_and_relations` и `full_knowledge_product` имеют закрытые разные формы. Payload
более высокого уровня **НЕ ДОЛЖЕН** маскироваться политикой более низкого уровня.

### O-2. Инвариант идентичности и провенанса

При любой комбинации, включая три значения `none`, Preserved Record **ДОЛЖЕН** содержать
`source_id`, `canonical_url`, `content_hash`, `retrieved_at`, `published_at`, `parser_version` и
`extractor_version`. Удаление payload **НЕ ДОЛЖНО** удалять эти поля.

### O-3. Экономичный режим и явный риск

`evidence_fragments` — рекомендуемый экономичный уровень приобретённого артефакта. При выборе
`none`, `metadata` или `summary` политика **ДОЛЖНА** содержать
`reproducibility_risk_accepted: true`; иначе конфигурация невалидна.

### O-4. Архивный режим только явно

`full_content` **ДОЛЖЕН** выбираться только вместе с `profile: archival`. Профиль `archival`
**ДОЛЖЕН** означать `full_content`. Система **НЕ ДОЛЖНА** переходить в архивный режим как в
неявный default.

### O-5. Граница Phase 1

Общий контракт выражает `none`, `latest_only` и `full_history`. Исполняемые профили Phase 1
**ДОЛЖНЫ** использовать только `latest_only`. `full_history` остаётся концептуально валидным для
AM-4, но его исполнение требует последующей реализации и тестов lineage/history.

### O-6. Версионирование

Policy и Preserved Record **ДОЛЖНЫ** указывать `schema_version`. Несовместимое изменение значений,
обязательных полей или смысла измерений **ДОЛЖНО** повышать мажорную версию.

## Исполняемая схема и пример

Источники истины:

- [`preservation-policy.schema.json`](../../configs/schemas/preservation-policy.schema.json);
- [`preserved-record.schema.json`](../../configs/schemas/preserved-record.schema.json).

Экономичный вариант показан в
[`preservation-policy.schema.json--economical.yaml`](../../tests/fixtures/contracts/valid/preservation-policy.schema.json--economical.yaml),
архивный — в
[`preservation-policy.schema.json--archival.yaml`](../../tests/fixtures/contracts/valid/preservation-policy.schema.json--archival.yaml),
а инвариант идентичности при `none` — в
[`preserved-record.schema.json--identity-with-none.yaml`](../../tests/fixtures/contracts/valid/preserved-record.schema.json--identity-with-none.yaml).
Связь уровней с payload показана в
[`preserved-record.schema.json--evidence-and-claims.yaml`](../../tests/fixtures/contracts/valid/preserved-record.schema.json--evidence-and-claims.yaml).

## Definition of Done / критерии соответствия

| Критерий | Проверка |
| --- | --- |
| Три измерения обязательны и независимы | schema fixtures |
| Уровни не допускают скрытого over-retention | позитивный и негативный Preserved Record fixture |
| Идентичность сохраняется при `none` | позитивный и негативный Preserved Record fixture |
| Экономия ниже evidence fragments требует принятия риска | негативный fixture |
| `full_content` требует явного `archival` | позитивный и негативный fixtures |
| Phase 1 принимает только `latest_only` | Research Profile schema fixture |
| Общая схема выражает `full_history` | AM-4 example |

## Эскалация и исключения

1. **Источник запрещает хранение текста.** Выбирается допустимый уровень артефакта и явно
   принимается риск воспроизводимости; identity/provenance сохраняются.
2. **Нужен аудит полного контента.** Автор спецификации явно выбирает `archival`; автоматическое
   повышение уровня хранения запрещено.
3. **Нужна история наблюдений в Phase 1.** Исполняемый профиль отклоняется. Требуется отдельная
   реализация `full_history`, миграция и тестирование.
4. **Несовместимое изменение.** Требуются ADR либо изменение принятого ADR и новая мажорная версия.

## Обоснование и связанные артефакты

Три независимых измерения предотвращают ложный выбор «хранить всё или ничего»: проект может
экономить на payload, сохраняя проверяемость результата и требуемый knowledge product. Явный
архивный профиль защищает бюджет от случайного полного хранения.

- [ADR-004](../adr/2026-09-adr-004-preservation-policy.md)
- [ADR-006](../adr/2026-09-adr-006-research-specification.md)
- [`research-specification-contract.md`](research-specification-contract.md)
- [`extraction-contract.md`](extraction-contract.md)
