---
status: proposed
version: 1.0
updated: 2026-09-09
temperature: 0.1
owner: G-Ivan-A
---

# Контракт Sufficiency Gate

Нормативная лексика по RFC 2119 / BCP 14: **ДОЛЖНО** (MUST), **НЕ ДОЛЖНО** (MUST NOT),
**СЛЕДУЕТ** (SHOULD), **НЕ СЛЕДУЕТ** (SHOULD NOT), **МОЖНО** (MAY). Термины определены в
[`glossary.md`](glossary.md). Модель завершения согласована с
[ADR-006](../adr/2026-09-adr-006-research-specification.md).

## Стороны и область

| Сторона | Роль |
| --- | --- |
| Поставщик | Sufficiency Gate / оркестратор Research Run |
| Потребитель | Analysis, оператор и последующая итерация acquisition |
| Вход | квалифицированное знание и `termination` Research Specification |
| Владелец контракта | G-Ivan-A |

**Область:** объяснимый итог Research Run, покрытие цели, пробелы, противоречия и рекомендации по
расширению.

**Вне области:** универсальные метрики достаточности, runtime-бюджеты и генерация ответа Analysis.

## Обязательства

### O-1. Пять результатов

Каждый завершённый Research Run **ДОЛЖЕН** иметь ровно один итог:

| Статус | Семантика |
| --- | --- |
| `SUFFICIENT` | все success conditions достигнуты |
| `PARTIAL` | полезное знание получено, но остаются существенные gaps |
| `ZERO` | квалифицируемое знание не получено |
| `CONFLICT` | квалифицированные независимые source groups материально противоречат друг другу |
| `EXHAUSTED` | прогон остановлен лимитом до достижения достаточности |

Статус **НЕ ДОЛЖЕН** маскировать другой: конфликт не сводится к partial, а исчерпание бюджета — к
zero.

### O-2. Объяснимость результата

Каждый Research Run Outcome **ДОЛЖЕН** включать `coverage`, `gaps`, `conflicts`,
`recommended_expansion` и непустой `rationale`. Для `PARTIAL`, `ZERO`, `EXHAUSTED` список `gaps`
**ДОЛЖЕН** быть непустым; для `CONFLICT` **ДОЛЖЕН** быть указан хотя бы один конфликт и не менее
двух `source_group_ids`.

### O-3. Метрики задаёт спецификация

Имена `coverage` **ДОЛЖНЫ** происходить из `termination.completion_dimensions` конкретной Research
Specification. Универсальный набор критериев или порог **НЕ ДОЛЖЕН** быть зашит в gate.

### O-4. Расширение исследования

При недостигнутых success conditions оркестратор **МОЖЕТ** продолжить `enumerate`, `expand` или
`query` согласно спецификации и runtime budget. `recommended_expansion` **ДОЛЖЕН** описывать
следующее полезное действие или причину отсутствия такого действия. Повторение итерации без
прогресса **НЕ СЛЕДУЕТ** выполнять.

### O-5. Разделение termination и бюджета

Причина `budget_exhausted` **МОЖЕТ** находиться в `termination.stop_conditions`, но численные
`max_iterations` и `max_cost_rub` **ДОЛЖНЫ** поступать только из Runtime Configuration. Исчерпание
любого лимита до успеха **ДОЛЖНО** давать `EXHAUSTED`.

### O-6. Передача в Analysis

При `SUFFICIENT` потребитель **ДОЛЖЕН** получить использованные claims с evidence, решениями и
идентичностью контента. При остальных статусах Analysis **НЕ ДОЛЖЕН** выдавать результат как полный;
частичный ответ **МОЖЕТ** быть выдан только с сохранёнными gaps/conflicts/rationale.

### O-7. Research Run и версии

Research Run **ДОЛЖЕН** фиксировать версии спецификации, Runtime Configuration и моделей,
processed content identities, решения, итерации, фактический бюджет и outcome. Несовместимое
изменение схемы outcome/run **ДОЛЖНО** повышать мажорную версию.

### O-8. Телеметрия

Каждая итерация и итог **ДОЛЖНЫ** порождать события с измерениями покрытия, стоимостью и статусом,
не заменяя сам сохраняемый Research Run.

## Исполняемые схемы и примеры

Источники истины:

- [`research-run-outcome.schema.json`](../../configs/schemas/research-run-outcome.schema.json);
- [`research-run.schema.json`](../../configs/schemas/research-run.schema.json).

Пять валидных примеров outcome находятся в
[`tests/fixtures/contracts/valid/`](../../tests/fixtures/contracts/valid/) и имеют префикс
`research-run-outcome.schema.json--`; полный прогон показан в
[`research-run.schema.json--complete.yaml`](../../tests/fixtures/contracts/valid/research-run.schema.json--complete.yaml).

## Definition of Done / критерии соответствия

| Критерий | Проверка |
| --- | --- |
| Покрыты пять статусов | пять schema fixtures и unit test |
| Каждый outcome имеет объяснение | обязательные поля и негативный fixture |
| Gaps обязательны для partial/zero/exhausted | условные ограничения схемы |
| Conflict содержит независимые группы | условное ограничение и fixture |
| Runtime budget не смешан со спецификацией | закрытые схемы смешения |
| Run фиксирует версии, identities, решения и бюджет | Research Run fixture |

## Эскалация и исключения

1. **Противоречие источников.** Возвращается `CONFLICT`; автоматическое удаление одной стороны
   запрещено без отдельной Decision Policy или human review.
2. **Исчерпан бюджет.** Возвращается `EXHAUSTED`; понижение success conditions во время прогона
   запрещено.
3. **Нет qualifying evidence.** Возвращается `ZERO` с gaps и рекомендацией, а не синтезированный
   ответ.
4. **Human override.** Сохраняется отдельным объяснённым решением; исходный outcome не стирается.

## Обоснование и связанные артефакты

Пять результатов разделяют отсутствие данных, неполноту, конфликт и техническое исчерпание. Такое
разделение не позволяет маскировать качество исследования одним бинарным порогом.

- [ADR-006](../adr/2026-09-adr-006-research-specification.md)
- [`research-specification-contract.md`](research-specification-contract.md)
- [`relevance-gate-contract.md`](relevance-gate-contract.md)
- [`preservation-contract.md`](preservation-contract.md)
- [`telemetry-contract.md`](telemetry-contract.md)
