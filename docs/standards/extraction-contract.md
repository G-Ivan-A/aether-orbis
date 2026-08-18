---
status: proposed
version: 0.1
updated: 2026-08-18
temperature: 0.1
owner: G-Ivan-A
---

# Контракт извлечения (Extraction Contract)

Нормативная лексика по RFC 2119 / BCP 14: **ДОЛЖНО** (MUST), **НЕ ДОЛЖНО** (MUST NOT),
**СЛЕДУЕТ** (SHOULD), **НЕ СЛЕДУЕТ** (SHOULD NOT), **МОЖНО** (MAY).
Термины определены в [`glossary.md`](glossary.md) и здесь не переопределяются.

## Стороны и область

| Сторона | Роль |
| --- | --- |
| Поставщик | компонент Extraction |
| Потребитель | Relevance Gate, Graph / Context Builder, Vector Index |
| Владелец контракта | G-Ivan-A |

**Область:** форма и обязательные свойства данных, покидающих компонент Extraction.

**Вне области:** способ извлечения, выбор модели ([ADR-002](../adr/2026-08-adr-002-model-routing.md)),
решение о релевантности ([relevance-gate-contract](relevance-gate-contract.md)), решение о том, что
становится ребром графа (зона Graph Builder).

## Обязательства

### O-1. Единица выдачи

Extraction **ДОЛЖНО** возвращать объект `ExtractionResult` со свойствами `source`, `entities`,
`relations`, `claims`, `extraction_meta`.

### O-2. Провенанс

Каждый элемент `entities`, `relations` и `claims` **ДОЛЖЕН** содержать `evidence` с полями `source`
(URI), `fragment` (дословный фрагмент исходного текста) и `retrieved_at` (ISO 8601, UTC).
Элемент без валидного `evidence` **НЕ ДОЛЖЕН** покидать компонент.

### O-3. Confidence

Каждый элемент **ДОЛЖЕН** содержать `confidence` — число в диапазоне `0.0`–`1.0`.
Extraction **НЕ ДОЛЖНО** проставлять `confidence: 1.0` иначе как при дословном совпадении с
фрагментом.

### O-4. Состояния связей

Каждая связь **ДОЛЖНА** иметь `state` ∈ {`OBSERVED`, `NOT_OBSERVED`, `UNCERTAIN`}.
Extraction **НЕ ДОЛЖНО** приводить `NOT_OBSERVED` к утверждению об отсутствии связи в реальности.
`UNCERTAIN` **ДОЛЖНО** использоваться при противоречивых или недостаточных данных, а не как значение
по умолчанию.

### O-5. Дословность фрагмента

`evidence.fragment` **ДОЛЖЕН** быть подстрокой нормализованного текста источника. Пересказ,
перевод или реконструкция фрагмента моделью **НЕ ДОЛЖНЫ** записываться в это поле.

### O-6. Запрет выводов

Extraction **НЕ ДОЛЖНО** возвращать элементы, не подтверждаемые текстом источника, в том числе
логические следствия из нескольких источников. Такие выводы — зона Graph Builder и Analysis.

### O-7. Идентификаторы

`entities[].id` **ДОЛЖЕН** быть уникален в пределах `ExtractionResult`. Глобальное разрешение
сущностей **НЕ ДОЛЖНО** выполняться на этом шаге.

### O-8. Телеметрия

Каждый вызов Extraction **ДОЛЖЕН** порождать запись телеметрии согласно
[`telemetry-contract`](telemetry-contract.md).

### O-9. Пустой результат

Отсутствие извлекаемого содержимого **ДОЛЖНО** выражаться пустыми массивами и
`extraction_meta.status = "empty"`, а **НЕ ДОЛЖНО** — синтезированным содержимым или ошибкой.

## Схема

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ExtractionResult",
  "type": "object",
  "required": ["source", "entities", "relations", "claims", "extraction_meta"],
  "properties": {
    "source": {
      "type": "object",
      "required": ["uri", "retrieved_at"],
      "properties": {
        "uri": { "type": "string", "format": "uri" },
        "retrieved_at": { "type": "string", "format": "date-time" },
        "content_hash": { "type": "string" },
        "language": { "type": "string" }
      }
    },
    "entities": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "type", "name", "confidence", "evidence"],
        "properties": {
          "id": { "type": "string" },
          "type": { "type": "string" },
          "name": { "type": "string" },
          "attributes": { "type": "object" },
          "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
          "evidence": { "$ref": "#/$defs/evidence" }
        }
      }
    },
    "relations": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["subject", "predicate", "object", "state", "confidence", "evidence"],
        "properties": {
          "subject": { "type": "string", "description": "entities[].id" },
          "predicate": { "type": "string" },
          "object": { "type": "string", "description": "entities[].id" },
          "state": { "enum": ["OBSERVED", "NOT_OBSERVED", "UNCERTAIN"] },
          "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
          "evidence": { "$ref": "#/$defs/evidence" }
        }
      }
    },
    "claims": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["claim", "confidence", "evidence"],
        "properties": {
          "claim": { "type": "string" },
          "entities": { "type": "array", "items": { "type": "string" } },
          "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
          "evidence": { "$ref": "#/$defs/evidence" }
        }
      }
    },
    "extraction_meta": {
      "type": "object",
      "required": ["status", "model", "extracted_at"],
      "properties": {
        "status": { "enum": ["ok", "empty", "partial"] },
        "model": { "type": "string" },
        "operation_role": { "const": "extraction" },
        "extracted_at": { "type": "string", "format": "date-time" },
        "direction": { "type": "string" }
      }
    }
  },
  "$defs": {
    "evidence": {
      "type": "object",
      "required": ["source", "fragment", "retrieved_at"],
      "properties": {
        "source": { "type": "string", "format": "uri" },
        "fragment": { "type": "string", "minLength": 1 },
        "retrieved_at": { "type": "string", "format": "date-time" }
      }
    }
  }
}
```

### Пример

```json
{
  "source": {
    "uri": "https://example.com/news/123",
    "retrieved_at": "2026-08-18T09:14:00Z",
    "language": "ru"
  },
  "entities": [
    {
      "id": "e1", "type": "organization", "name": "Компания A",
      "confidence": 0.97,
      "evidence": {
        "source": "https://example.com/news/123",
        "fragment": "…в марте компания A объявила о запуске продукта B…",
        "retrieved_at": "2026-08-18T09:14:00Z"
      }
    }
  ],
  "relations": [
    {
      "subject": "e1", "predicate": "launched", "object": "e2",
      "state": "OBSERVED", "confidence": 0.91,
      "evidence": {
        "source": "https://example.com/news/123",
        "fragment": "…в марте компания A объявила о запуске продукта B…",
        "retrieved_at": "2026-08-18T09:14:00Z"
      }
    }
  ],
  "claims": [
    {
      "claim": "Компания A запустила продукт B",
      "entities": ["e1", "e2"],
      "confidence": 0.91,
      "evidence": {
        "source": "https://example.com/news/123",
        "fragment": "…в марте компания A объявила о запуске продукта B…",
        "retrieved_at": "2026-08-18T09:14:00Z"
      }
    }
  ],
  "extraction_meta": {
    "status": "ok",
    "model": "<model-id>",
    "operation_role": "extraction",
    "extracted_at": "2026-08-18T09:14:07Z",
    "direction": "reputation-technologies"
  }
}
```

## Definition of Done / критерии соответствия

| Критерий | Проверка |
| --- | --- |
| Выдача валидна по JSON Schema | контрактный тест в CI |
| 100 % элементов имеют `evidence` с непустым `fragment` | контрактный тест |
| `fragment` является подстрокой нормализованного текста | автопроверка на корпусе фикстур |
| `confidence` в диапазоне `0.0`–`1.0` | валидация схемы |
| `state` присутствует у всех связей | валидация схемы |
| Пустой источник даёт `status = "empty"`, а не синтез | негативный тест |
| Есть запись телеметрии на каждый вызов | контрактный тест телеметрии |

## Эскалация и исключения

1. **Невалидная выдача модели.** Вызов повторяется по политике Model Router; при повторной неудаче
   источник помечается `extraction_meta.status = "partial"` и передаётся дальше только валидная часть.
2. **Фрагмент не найден в тексте.** Элемент отбрасывается, событие фиксируется в телеметрии как
   `evidence_mismatch`. Молчаливое сохранение такого элемента **НЕ ДОЛЖНО** происходить.
3. **Изменение схемы.** Обратно несовместимое изменение требует нового ADR и мажорного повышения
   `version` контракта.
4. **Исключения из O-6.** Не предоставляются: запрет на выводы в Extraction — граница зон, а не
   настройка.

## Обоснование и контекст

Требование evidence для **каждого** элемента, а не только для связей, взято из SSOT v4.3: проверяемость
вывода определяется прослеживаемостью самого мелкого используемого утверждения. Если сущность попала
в граф без фрагмента-источника, цепочка проверки рвётся в первом же звене.

Три состояния связи сохранены осознанно, несмотря на предложение упростить модель до бинарной:
«связь не наблюдалась» ≠ «связи не существует», и потеря этого различия превращает пробел в сборе в
ложное отрицательное утверждение.

Запрет выводов внутри Extraction поддерживает жёсткую границу Parser ≠ Graph Builder ≠ Analysis: если
извлечение начнёт выводить следствия, исчезнет возможность отличить наблюдение от интерпретации.

## Связанные артефакты

- [`glossary.md`](glossary.md)
- [`relevance-gate-contract.md`](relevance-gate-contract.md)
- [`telemetry-contract.md`](telemetry-contract.md)
- [ADR-001](../adr/2026-08-adr-001-tech-stack.md), [ADR-002](../adr/2026-08-adr-002-model-routing.md)
