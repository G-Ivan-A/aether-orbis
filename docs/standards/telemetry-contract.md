---
status: proposed
version: 0.1
updated: 2026-08-18
temperature: 0.1
owner: G-Ivan-A
---

# Контракт телеметрии

Нормативная лексика по RFC 2119 / BCP 14: **ДОЛЖНО** (MUST), **НЕ ДОЛЖНО** (MUST NOT),
**СЛЕДУЕТ** (SHOULD), **НЕ СЛЕДУЕТ** (SHOULD NOT), **МОЖНО** (MAY).
Термины определены в [`glossary.md`](glossary.md) и здесь не переопределяются.

## Стороны и область

| Сторона | Роль |
| --- | --- |
| Поставщик | все компоненты пайплайна |
| Потребитель | оператор, evaluation, контроль бюджета |
| Владелец контракта | G-Ivan-A |

**Область:** обязательный состав событий телеметрии, единицы измерения и границы хранения.

**Вне области:** выбор конкретного бэкенда наблюдаемости
([ADR-001](../adr/2026-08-adr-001-tech-stack.md)), бизнес-метрики направлений.

## Обязательства

### O-1. Обязательность в MVP

Телеметрия **ДОЛЖНА** работать начиная с MVP. Перенос телеметрии на пост-MVP **НЕ ДОЛЖЕН**
рассматриваться как допустимое упрощение объёма.

### O-2. Покрытие переходов

Каждый переход пайплайна (Ingestion, Extraction, Relevance Gate, Graph Building, Vector Indexing,
Sufficiency Gate, Analysis) **ДОЛЖЕН** порождать событие телеметрии.

### O-3. Обязательные поля события

| Поле | Тип | Смысл |
| --- | --- | --- |
| `event_id` | string | уникальный идентификатор события |
| `run_id` | string | идентификатор прогона |
| `direction` | string | направление исследования |
| `component` | enum | компонент-источник события |
| `operation_role` | enum | роль операции по [ADR-002](../adr/2026-08-adr-002-model-routing.md) |
| `started_at` / `finished_at` | date-time | границы шага, ISO 8601 UTC |
| `latency_ms` | integer | длительность шага |
| `status` | enum | `ok`, `partial`, `error` |

### O-4. Поля вызова модели

Для событий, включающих вызов модели, **ДОЛЖНЫ** дополнительно фиксироваться: `provider`, `model`,
`tokens_in`, `tokens_out`, `cached_tokens`, `cost_rub`, `batch` (boolean).

### O-5. Поля решений

Для событий gates **ДОЛЖНЫ** фиксироваться: `decision`, `score` или `criteria_scores`, `threshold`,
`iteration`, `hitl` ∈ {`skipped`, `approved`, `override`}.

### O-6. Confidence

События Extraction **ДОЛЖНЫ** содержать агрегаты `confidence`: `confidence_mean`, `confidence_min`,
а также `uncertain_relations_count`.

### O-7. Единицы измерения

Стоимость **ДОЛЖНА** фиксироваться в рублях (`cost_rub`) с указанием курса/тарифа на момент вызова;
латентность — в миллисекундах; токены — в единицах провайдера. Смешение единиц в одном поле
**НЕ ДОЛЖНО** допускаться.

### O-8. Отсутствие секретов и персональных данных

События **НЕ ДОЛЖНЫ** содержать ключи API, учётные данные и персональные данные. Содержимое
источников **НЕ СЛЕДУЕТ** дублировать в телеметрию; допустимы идентификаторы и хэши.

### O-9. Хранение вне репозитория

Артефакты телеметрии **НЕ ДОЛЖНЫ** коммититься в git
([ADR-003](../adr/2026-08-adr-003-infrastructure.md), [`.gitignore`](../../.gitignore)).

### O-10. Агрегаты прогона

По завершении прогона **ДОЛЖНА** формироваться сводка: суммарная стоимость, стоимость по ролям
операций, число источников на входе gate и на выходе, число итераций Sufficiency Gate, финальное
решение (`sufficient` или `zero`).

## Схема события

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "TelemetryEvent",
  "type": "object",
  "required": ["event_id", "run_id", "direction", "component", "operation_role",
               "started_at", "finished_at", "latency_ms", "status"],
  "properties": {
    "event_id": { "type": "string" },
    "run_id": { "type": "string" },
    "direction": { "type": "string" },
    "component": {
      "enum": ["ingestion", "extraction", "relevance_gate", "graph_builder",
               "vector_index", "sufficiency_gate", "analysis"]
    },
    "operation_role": {
      "enum": ["ingestion", "extraction", "relevance_scoring", "graph_building",
               "sufficiency_evaluation", "analysis"]
    },
    "started_at": { "type": "string", "format": "date-time" },
    "finished_at": { "type": "string", "format": "date-time" },
    "latency_ms": { "type": "integer", "minimum": 0 },
    "status": { "enum": ["ok", "partial", "error"] },
    "model_call": {
      "type": "object",
      "properties": {
        "provider": { "type": "string" },
        "model": { "type": "string" },
        "tokens_in": { "type": "integer", "minimum": 0 },
        "tokens_out": { "type": "integer", "minimum": 0 },
        "cached_tokens": { "type": "integer", "minimum": 0 },
        "cost_rub": { "type": "number", "minimum": 0 },
        "batch": { "type": "boolean" }
      }
    },
    "decision": {
      "type": "object",
      "properties": {
        "decision": { "type": "string" },
        "score": { "type": "number" },
        "criteria_scores": { "type": "object" },
        "threshold": { "type": "number" },
        "iteration": { "type": "integer", "minimum": 0 },
        "hitl": { "enum": ["skipped", "approved", "override"] }
      }
    },
    "confidence": {
      "type": "object",
      "properties": {
        "confidence_mean": { "type": "number", "minimum": 0, "maximum": 1 },
        "confidence_min": { "type": "number", "minimum": 0, "maximum": 1 },
        "uncertain_relations_count": { "type": "integer", "minimum": 0 }
      }
    },
    "error": {
      "type": "object",
      "properties": {
        "kind": { "type": "string" },
        "message": { "type": "string" }
      }
    }
  }
}
```

## Метрики по компонентам

| Компонент | Обязательные метрики |
| --- | --- |
| Ingestion | число источников, латентность, доля ошибок загрузки |
| Extraction | токены, стоимость, `confidence_mean`, `evidence_mismatch`, доля `partial` |
| Relevance Gate | `score`, доля `relevant`, число записей в Source Intelligence |
| Graph Builder | число сущностей и связей, доля `UNCERTAIN`, число слияний сущностей |
| Vector Index | число векторов, латентность индексации |
| Sufficiency Gate | `criteria_scores`, номер итерации, доля `zero` |
| Analysis | токены, стоимость, латентность |

## Definition of Done / критерии соответствия

| Критерий | Проверка |
| --- | --- |
| Каждый переход порождает событие | контрактный тест сквозного прогона |
| События валидны по схеме | валидация в CI |
| Секреты и ПДн отсутствуют в событиях | автопроверка на запрещённые шаблоны |
| Сводка прогона формируется | тест агрегации |
| Артефакты телеметрии не попадают в git | проверка `.gitignore` в CI |

## Эскалация и исключения

1. **Недоступен бэкенд наблюдаемости.** События буферизуются локально; прогон **НЕ ДОЛЖЕН**
   продолжаться с полностью отключённой телеметрией дольше, чем разрешено конфигурацией.
2. **Провайдер не возвращает счёт токенов.** `tokens_*` заполняются оценкой с пометкой `estimated`;
   молчаливое проставление нулей **НЕ ДОЛЖНО** выполняться.
3. **Превышение бюджета прогона.** Прогон останавливается, событие фиксируется как
   `budget_exhausted`, Sufficiency Gate возвращает `zero`.
4. **Расширение схемы события.** Добавление полей допустимо; удаление или смена типа поля требует
   мажорного повышения `version` контракта.

## Обоснование и контекст

Телеметрия включена в MVP, потому что все ключевые решения проекта — маршрутизация моделей, пороги
gates, выбор графовой БД — требуют измерений. Без телеметрии эти решения принимаются на
предпочтениях, а стоимость прогона остаётся неизвестной до счёта провайдера.

Фиксация стоимости по ролям операций напрямую поддерживает экономическую модель проекта: дешёвое
извлечение, среднее построение графа, дорогой анализ. Без разбивки по ролям невозможно проверить,
что Relevance Gate действительно экономит токены аналитической модели.

## Связанные артефакты

- [`extraction-contract.md`](extraction-contract.md)
- [`relevance-gate-contract.md`](relevance-gate-contract.md)
- [`sufficiency-gate-contract.md`](sufficiency-gate-contract.md)
- [ADR-002](../adr/2026-08-adr-002-model-routing.md), [ADR-003](../adr/2026-08-adr-003-infrastructure.md)
