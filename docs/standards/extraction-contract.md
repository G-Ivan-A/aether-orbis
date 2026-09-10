---
status: proposed
version: 1.0
updated: 2026-09-09
temperature: 0.1
owner: G-Ivan-A
---

# Контракт извлечения (Extraction Contract)

Нормативная лексика по RFC 2119 / BCP 14: **ДОЛЖНО** (MUST), **НЕ ДОЛЖНО** (MUST NOT),
**СЛЕДУЕТ** (SHOULD), **НЕ СЛЕДУЕТ** (SHOULD NOT), **МОЖНО** (MAY). Термины определены в
[`glossary.md`](glossary.md). Модель оценки согласована с
[ADR-005](../adr/2026-09-adr-005-evaluation-result.md), а сохранение — с
[ADR-004](../adr/2026-09-adr-004-preservation-policy.md).

## Стороны и область

| Сторона | Роль |
| --- | --- |
| Поставщик | компонент Extraction |
| Потребитель | Evaluation, Knowledge Builder и Preservation |
| Владелец контракта | G-Ivan-A |

**Область:** форма `ExtractionResult`, локальная уверенность извлечения и провенанс каждого
извлечённого элемента.

**Вне области:** способ и модель извлечения, квалификация источника, построение глобального графа и
выводы из нескольких источников.

## Обязательства

### O-1. Форма результата

Extraction **ДОЛЖНО** возвращать версионированный `ExtractionResult` с `source`, `entities`,
`relations`, `claims` и `extraction_meta`. Закрытая машинная схема определяет точные поля и типы.

### O-2. Идентичность контента

`source` **ДОЛЖЕН** включать `source_id`, `canonical_url`, `content_hash`, `retrieved_at`,
`published_at`, `parser_version` и `extractor_version`. Результат без любого из этих полей
**НЕ ДОЛЖЕН** покидать компонент.

### O-3. Evidence для каждого элемента

Каждая entity, relation и claim **ДОЛЖНА** содержать `evidence` с `source_id`, дословным
`fragment`, `retrieved_at` и `evidence_strength`. `fragment` **ДОЛЖЕН** быть подстрокой
нормализованного источника; пересказ или реконструкция **НЕ ДОЛЖНЫ** записываться как evidence.

### O-4. Разделённые характеристики

Локальная вероятность корректности извлечения **ДОЛЖНА** называться `extraction_confidence` и
лежать в диапазоне `0.0`–`1.0`. Сила свидетельства **ДОЛЖНА** называться `evidence_strength`.
Авторитетность источника оценивается отдельно как `source_authority` в EvaluationResult.
Универсальное поле `confidence` **НЕ ДОЛЖНО** использоваться.

### O-5. Состояния связей

`relations[].state` **ДОЛЖЕН** быть одним из `OBSERVED`, `NOT_OBSERVED`, `UNCERTAIN`,
`CONTRADICTED`. `NOT_OBSERVED` **НЕ ДОЛЖЕН** трактоваться как отсутствие связи в реальности;
`CONTRADICTED` **ДОЛЖЕН** сохранять материальное противоречие, а не сводиться к `UNCERTAIN`.

### O-6. Граница извлечения

Extraction **НЕ ДОЛЖНО** синтезировать элементы без дословного evidence или строить логические
следствия из нескольких источников. Глобальное разрешение сущностей и выбор рёбер — ответственность
Knowledge Builder.

### O-7. Пустой и ошибочный результат

Корректно обработанный источник без извлекаемых элементов **ДОЛЖЕН** возвращать пустые массивы и
`extraction_meta.status: ok`. Частично валидный результат **МОЖЕТ** иметь `partial`; невозможность
сформировать контрактный результат **ДОЛЖНА** иметь `error` и наблюдаемую ошибку телеметрии.

### O-8. Версионирование и телеметрия

Каждый результат **ДОЛЖЕН** указывать `schema_version`; несовместимое изменение **ДОЛЖНО** повышать
мажорную версию. Каждый вызов **ДОЛЖЕН** порождать событие по
[`telemetry-contract.md`](telemetry-contract.md).

## Исполняемая схема и пример

Источник истины —
[`extraction-result.schema.json`](../../configs/schemas/extraction-result.schema.json).
Валидный результат с `CONTRADICTED` находится в
[`extraction-result.schema.json--contradicted.yaml`](../../tests/fixtures/contracts/valid/extraction-result.schema.json--contradicted.yaml).

## Definition of Done / критерии соответствия

| Критерий | Проверка |
| --- | --- |
| Результат валиден по закрытой схеме | позитивные и негативные fixtures |
| Каждый элемент имеет evidence | обязательные поля схемы |
| Content identity и версии обработчиков обязательны | source schema fixture |
| Различены extraction confidence и evidence strength | схема запрещает лишнее `confidence` |
| Поддержаны четыре состояния связи | fixture `CONTRADICTED` и enum схемы |
| Несовпадающий evidence fragment не сохраняется | интеграционный тест Extraction |

## Эскалация и исключения

1. **Невалидная выдача модели.** Выполняются runtime retries; после исчерпания возвращается только
   валидная часть с `partial` либо `error` без синтеза данных.
2. **Фрагмент не найден.** Элемент отбрасывается и фиксируется `evidence_mismatch`.
3. **Противоречащие фрагменты.** Связь сохраняется как `CONTRADICTED`; автоматический выбор стороны
   без Decision Policy запрещён.
4. **Несовместимое изменение.** Требуются ADR либо изменение принятого ADR и новая мажорная версия.

## Обоснование и связанные артефакты

Разделённые характеристики позволяют различать ошибку распознавания, слабое свидетельство и низкий
авторитет источника. Обязательная content identity сохраняет проверяемую цепочку от knowledge
product до полученного байтового содержимого.

- [`preservation-contract.md`](preservation-contract.md)
- [`relevance-gate-contract.md`](relevance-gate-contract.md)
- [`telemetry-contract.md`](telemetry-contract.md)
- [ADR-002](../adr/2026-08-adr-002-model-routing.md)
- [ADR-004](../adr/2026-09-adr-004-preservation-policy.md)
- [ADR-005](../adr/2026-09-adr-005-evaluation-result.md)
