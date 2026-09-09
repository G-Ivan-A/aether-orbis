---
status: proposed
version: 1.0
updated: 2026-09-09
temperature: 0.1
owner: G-Ivan-A
---

# Контракт телеметрии

Нормативная лексика по RFC 2119 / BCP 14: **ДОЛЖНО** (MUST), **НЕ ДОЛЖНО** (MUST NOT),
**СЛЕДУЕТ** (SHOULD), **НЕ СЛЕДУЕТ** (SHOULD NOT), **МОЖНО** (MAY). Термины определены в
[`glossary.md`](glossary.md); оценка и решение согласованы с
[ADR-005](../adr/2026-09-adr-005-evaluation-result.md).

## Стороны и область

| Сторона | Роль |
| --- | --- |
| Поставщик | компоненты Research Run |
| Потребитель | оператор, cost control, evaluation и аудит |
| Владелец контракта | G-Ivan-A |

**Область:** переносимая форма события, роли операций, стоимость, именованные оценки, решения и
финальный Research Run Outcome.

**Вне области:** выбор observability backend, production deployment, retention телеметрии и
направленные бизнес-метрики. Phase 1 создаёт контракт, а не production telemetry runtime.

## Обязательства

### O-1. Базовое событие

Каждый наблюдаемый шаг **ДОЛЖЕН** фиксировать `schema_version`, `event_id`, `run_id`, `profile_id`,
`component`, `operation_role`, `started_at`, `finished_at`, `latency_ms` и `status`. События
**ДОЛЖНЫ** коррелироваться с Research Run и исполняемым профилем.

### O-2. Роли операций

`operation_role` **ДОЛЖНА** быть одной из `discovery`, `parsing`, `extraction`, `triage`,
`full_evaluation`, `qualification`, `knowledge_building`, `run_outcome`. Роль определяет допустимый
payload: `extraction`, `triage`, `full_evaluation`, `qualification` и `run_outcome` **ДОЛЖНЫ**
содержать одноимённый доменный payload и **НЕ ДОЛЖНЫ** переносить payload другой роли. `triage` и
`full_evaluation` **НЕ ДОЛЖНЫ** агрегироваться как одна неразличимая стадия.

### O-3. Вызовы моделей

Если шаг вызывает модель, `model_call` **ДОЛЖЕН** фиксировать `provider`, `model`, `tokens_in`,
`tokens_out`, `cached_tokens`, `cost_rub` и `batch`. Стоимость измеряется в рублях, латентность — в
миллисекундах, токены — в единицах провайдера; разные единицы **НЕ ДОЛЖНЫ** смешиваться в поле.

### O-4. Раздельные extraction-метрики

Extraction-событие **ДОЛЖНО** содержать extraction payload и **МОЖЕТ** фиксировать в нём число
entities/relations/claims,
`mean_extraction_confidence` и `mean_evidence_strength`. Универсальный агрегат `confidence`
**НЕ ДОЛЖЕН** существовать.

### O-5. Evaluation отдельно от Qualification

Evaluation-событие **ДОЛЖНО** фиксировать `stage` и открытую карту именованных `characteristics`.
Qualification-событие **ДОЛЖНО** отдельно фиксировать `decision`, `policy_id`, `policy_version` и
`matched_rule`. `matched_rule` **ДОЛЖЕН** быть `null` при fallback. Измерение и решение **НЕ
ДОЛЖНЫ** сливаться в единый score/threshold.

### O-6. Итог прогона

Финальное событие **ДОЛЖНО** использовать тот же Research Run Outcome с одним из `SUFFICIENT`,
`PARTIAL`, `ZERO`, `CONFLICT`, `EXHAUSTED`, включая coverage, gaps, conflicts,
recommended expansion и rationale. Телеметрия **НЕ ДОЛЖНА** заменять сохраняемый Research Run.

### O-7. Безопасность и хранение

События **НЕ ДОЛЖНЫ** содержать API keys, credentials, персональные данные или полный текст
источников. Runtime-артефакты телеметрии **НЕ ДОЛЖНЫ** коммититься в git.

### O-8. Ошибки и версии

При `status: error` **СЛЕДУЕТ** указывать стабильный `error_code`; молчаливая потеря события
**НЕ ДОЛЖНА** считаться успешным шагом. Несовместимое изменение обязательных полей или семантики
**ДОЛЖНО** повышать мажорную версию.

## Исполняемая схема и пример

Источник истины —
[`telemetry-event.schema.json`](../../configs/schemas/telemetry-event.schema.json).
Валидные примеры полной оценки и отдельной квалификации:
[`telemetry-event.schema.json--full-evaluation.yaml`](../../tests/fixtures/contracts/valid/telemetry-event.schema.json--full-evaluation.yaml)
и
[`telemetry-event.schema.json--qualification.yaml`](../../tests/fixtures/contracts/valid/telemetry-event.schema.json--qualification.yaml).

## Метрики по ролям

| Роль | Ключевые наблюдения |
| --- | --- |
| discovery / parsing | источники, latency, errors |
| extraction | counts, extraction confidence, evidence strength, cost |
| triage / full evaluation | stage, named characteristics, cost |
| qualification | decision и versioned policy |
| knowledge building | принятые claims/relations и provenance |
| завершение run | пять outcome statuses, coverage, gaps/conflicts и consumed budget |

## Definition of Done / критерии соответствия

| Критерий | Проверка |
| --- | --- |
| Событие валидно по закрытой схеме | schema fixture |
| Triage и full evaluation различены | role-specific schema fixtures |
| Evaluation и qualification раздельны | отдельные role-specific schema fixtures |
| Универсальный `confidence` отклоняется | негативный fixture |
| Все пять outcome доступны | ссылка на Research Run Outcome schema |
| Секреты и runtime-логи не попадают в git | repository boundary/security checks |

## Эскалация и исключения

1. **Backend недоступен.** События буферизуются согласно Runtime Configuration; полностью
   ненаблюдаемый прогон не считается нормой.
2. **Провайдер не возвращает токены.** Оценка маркируется отдельно на уровне реализации;
   молчаливый ноль запрещён.
3. **Неизвестная характеристика.** Она допустима, если объявлена Research Specification и проходит
   naming contract; универсальный `confidence` всё равно запрещён.
4. **Production retention/deployment.** Определяется отдельным решением и не расширяет этот scope.

## Обоснование и связанные артефакты

События повторяют разделение доменных контрактов: извлечение, evidence, оценка, политика и outcome
видимы отдельно. Это позволяет измерять стоимость и качество без потери смысла в универсальном
score.

- [ADR-002](../adr/2026-08-adr-002-model-routing.md)
- [ADR-003](../adr/2026-08-adr-003-infrastructure.md)
- [ADR-005](../adr/2026-09-adr-005-evaluation-result.md)
- [`extraction-contract.md`](extraction-contract.md)
- [`relevance-gate-contract.md`](relevance-gate-contract.md)
- [`sufficiency-gate-contract.md`](sufficiency-gate-contract.md)
