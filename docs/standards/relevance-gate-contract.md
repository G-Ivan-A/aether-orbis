---
status: proposed
version: 1.0
updated: 2026-09-09
temperature: 0.1
owner: G-Ivan-A
---

# Контракт Evaluation / Qualification Gate

Нормативная лексика по RFC 2119 / BCP 14: **ДОЛЖНО** (MUST), **НЕ ДОЛЖНО** (MUST NOT),
**СЛЕДУЕТ** (SHOULD), **НЕ СЛЕДУЕТ** (SHOULD NOT), **МОЖНО** (MAY). Термины определены в
[`glossary.md`](glossary.md). Решения этого контракта подчиняются
[ADR-005](../adr/2026-09-adr-005-evaluation-result.md).

## Стороны и область

| Сторона | Роль |
| --- | --- |
| Поставщик | Evaluation и интерпретатор Decision Policy |
| Потребитель | Knowledge Builder, Preservation и Sufficiency Gate |
| Вход | источник и/или `ExtractionResult` |
| Владелец контракта | G-Ivan-A |

**Область:** сохранённые характеристики `EvaluationResult` и отдельное объяснимое решение
`QualificationDecision`.

**Вне области:** извлечение, универсальный набор критериев, полнота всего Research Run и способ
выбора модели.

## Обязательства

### O-1. EvaluationResult отдельно от решения

Evaluation **ДОЛЖНО** сначала сохранять `EvaluationResult`, а затем применять версионированную
Decision Policy и сохранять `QualificationDecision`. Решение **НЕ ДОЛЖНО** перезаписывать
измеренные характеристики.

### O-2. Расширяемые характеристики

`characteristics` **ДОЛЖЕН** быть открытой картой именованных характеристик; каждая характеристика
**ДОЛЖНА** иметь `score` и непустой `rationale`. Набор имён задаётся Research Specification.
Универсальное имя `confidence` **НЕ ДОЛЖНО** использоваться. В частности:

- корректность извлечения — `extraction_confidence` в ExtractionResult;
- сила evidence — `evidence_strength`;
- авторитет источника — `source_authority`.

### O-3. Две стадии оценки

Система **ДОЛЖНА** различать `evaluation_stage: triage` и `evaluation_stage: full`. Triage
**НЕ ДОЛЖЕН** неявно считаться полной оценкой; политика **МОЖЕТ** использовать разные наборы
характеристик, явно объявленные спецификацией.

### O-4. Квалификационное решение

Decision Policy **ДОЛЖНА** содержать упорядоченные правила и fallback. Результат **ДОЛЖЕН** быть
одним из `QUALIFIED`, `CONDITIONAL`, `REJECTED`. `QualificationDecision` **ДОЛЖЕН** фиксировать
идентичность и версию политики, идентичность оценки, совпавшее правило, объяснение и время.

### O-5. Повторное применение политики

Сохранённый EvaluationResult **ДОЛЖЕН** допускать применение другой Decision Policy без повторного
вызова Evaluation. Идентичный EvaluationResult и идентичная версия политики **ДОЛЖНЫ** давать
идентичное решение.

### O-6. Независимость источников Phase 1

`subject` **ДОЛЖЕН** содержать `source_id`, `source_group_id`, `canonical_url` и `content_hash`.
В Phase 1 `source_group_id` **ДОЛЖЕН** объединять только точный canonical URL либо точный content
hash. Семантическое объединение разных публикаций и доменов **НЕ ПОДДЕРЖИВАЕТСЯ** и **НЕ ДОЛЖНО**
имитироваться эвристикой.

### O-7. Сохранение отклонённых оценок

При `REJECTED` EvaluationResult и QualificationDecision **ДОЛЖНЫ** сохраняться согласно
Preservation Policy. Отбраковка из knowledge product **НЕ ДОЛЖНА** уничтожать rationale и
идентичность проверенного содержимого.

### O-8. Версионирование и телеметрия

EvaluationResult, Decision Policy и QualificationDecision **ДОЛЖНЫ** указывать версии схемы и/или
политики. Несовместимое изменение **ДОЛЖНО** повышать мажорную версию. Стадия, характеристики и
решение **ДОЛЖНЫ** наблюдаться раздельно по контракту телеметрии.

## Исполняемые схемы и примеры

Источники истины:

- [`evaluation-result.schema.json`](../../configs/schemas/evaluation-result.schema.json);
- [`decision-policy.schema.json`](../../configs/schemas/decision-policy.schema.json);
- [`qualification-decision.schema.json`](../../configs/schemas/qualification-decision.schema.json).

Пример EvaluationResult:
[`evaluation-result.schema.json--custom.yaml`](../../tests/fixtures/contracts/valid/evaluation-result.schema.json--custom.yaml).
Две политики
[`strict`](../../tests/fixtures/contracts/valid/decision-policy.schema.json--strict.yaml) и
[`permissive`](../../tests/fixtures/contracts/valid/decision-policy.schema.json--permissive.yaml)
дают разные решения для этой же сохранённой оценки.

## Definition of Done / критерии соответствия

| Критерий | Проверка |
| --- | --- |
| Характеристики расширяемы | fixture с направленными именами |
| Универсальное `confidence` запрещено | негативный fixture |
| Triage и full различимы | enum схемы и telemetry fixture |
| EvaluationResult отделён от решения | три отдельные схемы |
| Политика переиспользуется без переоценки | unit test strict/permissive |
| `source_group_id` обязателен | негативный fixture |
| Отклонённые оценки сохраняются | интеграционный тест Preservation |

## Эскалация и исключения

1. **Характеристика не объявлена.** Спецификация отклоняется до запуска.
2. **Политика ссылается на отсутствующий score.** Правило не совпадает; событие конфигурационной
   неполноты фиксируется, молчаливый default запрещён.
3. **Нужна cross-domain lineage.** Phase 1 сохраняет группы раздельно; объединение требует новой
   модели lineage и тестов.
4. **Human override.** Допустим только как отдельное версионированное решение с автором и rationale;
   исходный EvaluationResult остаётся неизменным.

## Обоснование и связанные артефакты

Разделение измерения и решения сохраняет дорогую оценку как факт, а пороговую политику — как
заменяемое управленческое решение. Это позволяет улучшать правила без повторного acquisition и
Evaluation.

- [ADR-005](../adr/2026-09-adr-005-evaluation-result.md)
- [`research-specification-contract.md`](research-specification-contract.md)
- [`preservation-contract.md`](preservation-contract.md)
- [`extraction-contract.md`](extraction-contract.md)
- [`sufficiency-gate-contract.md`](sufficiency-gate-contract.md)
- [`telemetry-contract.md`](telemetry-contract.md)
