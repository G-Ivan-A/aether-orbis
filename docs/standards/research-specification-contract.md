---
status: proposed
version: 1.0
updated: 2026-09-09
temperature: 0.1
owner: G-Ivan-A
---

# Контракт Research Specification

Нормативная лексика по RFC 2119 / BCP 14: **ДОЛЖНО** (MUST), **НЕ ДОЛЖНО** (MUST NOT),
**СЛЕДУЕТ** (SHOULD), **НЕ СЛЕДУЕТ** (SHOULD NOT), **МОЖНО** (MAY). Термины определены в
[`glossary.md`](glossary.md). Решения этого контракта подчиняются
[ADR-006](../adr/2026-09-adr-006-research-specification.md).

## Стороны и область

| Сторона | Роль |
| --- | --- |
| Поставщик | автор или генератор Research Specification |
| Потребитель | оркестратор Research Run, acquisition, evaluation и preservation |
| Владелец контракта | G-Ivan-A |

**Область:** декларативная постановка исследования: зачем исследовать, что считать целью, как
ограничить пространство источников, как оценивать и сохранять результат и когда остановиться.

**Вне области:** выбор моделей и провайдеров, число воркеров, хранилища, ретраи, численные лимиты
стоимости и итераций; это поля Runtime Configuration. Реализация ingestion, LLM-вызовов и
оркестратора также не входит в контракт.

## Обязательства

### O-1. Шесть обязательных блоков

Каждая спецификация **ДОЛЖНА** содержать `objective`, `target`, `scope`, `evaluation`,
`preservation` и `termination`. Отсутствующий блок **НЕ ДОЛЖЕН** дополняться скрытым значением из
кода.

| Блок | Ответственность |
| --- | --- |
| `objective` | формулировка цели и ожидаемый knowledge product |
| `target` | topics, entities/relations, questions, observations либо novelty criteria |
| `scope` | стратегия frontier, типы источников и временное окно |
| `evaluation` | именованные характеристики и версионированная Decision Policy |
| `preservation` | три независимых измерения сохранения |
| `termination` | измерения полноты, условия успеха и причины остановки |

### O-2. Модели приобретения и область

Общая спецификация **ДОЛЖНА** выражать `AM-1`…`AM-5`. `scope.strategy` **ДОЛЖНА** быть ровно одной
из `enumerate`, `expand`, `query`, а форма `frontier` **ДОЛЖНА** соответствовать выбранной
стратегии. Критерии исследования **ДОЛЖНЫ** приходить из спецификации и **НЕ ДОЛЖНЫ** быть
универсально зашиты в код.

### O-3. Evaluation как политика исследования

`evaluation.dimensions` **ДОЛЖЕН** объявлять все характеристики, используемые условиями
`decision_policy`. Универсальная характеристика `confidence` **НЕ ДОЛЖНА** использоваться.
Decision Policy **ДОЛЖНА** оставаться отдельной версионированной сущностью, чтобы сохранённый
EvaluationResult можно было классифицировать повторно без повторной оценки источника.

### O-4. Завершение без runtime-смешения

`termination.completion_dimensions` **ДОЛЖЕН** объявлять измерения всех `success_conditions`.
Спецификация **МОЖЕТ** назвать `budget_exhausted` причиной остановки, но значения бюджета
**ДОЛЖНЫ** находиться только в Runtime Configuration.

### O-5. Общий контракт и Phase 1

Общий контракт допускает все пять Acquisition Model и все режимы Preservation Policy. Исполняемый
Research Profile Phase 1 **ДОЛЖЕН**:

- иметь `phase: 1` и `support: executable`;
- использовать только `AM-1` или `AM-2`;
- использовать только `observation_history: latest_only`;
- содержать Research Specification и не содержать runtime-полей.

Примеры `AM-3`…`AM-5` демонстрируют выразимость контракта и **НЕ ДОЛЖНЫ** считаться заявлением об
исполняемой поддержке Phase 1.

### O-6. Версионирование

`schema_version`, `specification_version`, версия Decision Policy и версия профиля **ДОЛЖНЫ**
фиксироваться явно. Несовместимое изменение обязательных полей, типов или семантики **ДОЛЖНО**
повышать мажорную версию; потребитель **НЕ ДОЛЖЕН** принимать неизвестную мажорную версию молча.

## Исполняемая схема и примеры

Источник истины для полей —
[`research-specification.schema.json`](../../configs/schemas/research-specification.schema.json).
Ограничение Phase 1 задаёт
[`research-profile.schema.json`](../../configs/schemas/research-profile.schema.json), а runtime —
[`runtime-configuration.schema.json`](../../configs/schemas/runtime-configuration.schema.json).

Валидные примеры находятся в [`examples/research-specifications/`](../../examples/research-specifications/):

- [`am-1-domain-monitoring.yaml`](../../examples/research-specifications/am-1-domain-monitoring.yaml);
- [`am-2-entity-relationship.yaml`](../../examples/research-specifications/am-2-entity-relationship.yaml);
- [`am-3-question-research.yaml`](../../examples/research-specifications/am-3-question-research.yaml);
- [`am-4-market-monitoring.yaml`](../../examples/research-specifications/am-4-market-monitoring.yaml);
- [`am-5-open-discovery.yaml`](../../examples/research-specifications/am-5-open-discovery.yaml).

## Definition of Done / критерии соответствия

| Критерий | Проверка |
| --- | --- |
| Все шесть блоков обязательны | позитивные и негативные schema fixtures |
| Выражаются `AM-1`…`AM-5` | пять валидируемых примеров |
| Выражаются три стратегии | fixtures `enumerate`, `expand`, `query` |
| Необъявленная характеристика отклоняется | cross-field контрактный тест |
| Профиль Phase 1 принимает только AM-1/AM-2 и `latest_only` | негативные profile fixtures |
| Research Profile и Runtime Configuration не смешиваются | закрытые схемы и негативные fixtures |
| Репозиторные конфиги валидны | `python3 tools/validate-contracts.py` |

## Эскалация и исключения

1. **Неизвестное измерение.** Прогон завершается ошибкой конфигурации; значение по умолчанию
   **НЕ ДОЛЖНО** подставляться молча.
2. **AM-3…AM-5 запрошена как исполняемая в Phase 1.** Профиль отклоняется. Поддержка требует
   отдельного roadmap-решения и контрактных тестов.
3. **`full_history` запрошен в Phase 1.** Профиль отклоняется; общая спецификация остаётся валидным
   описанием будущей возможности.
4. **Несовместимая схема.** Требуются ADR либо изменение принятого ADR и новая мажорная версия.

## Обоснование и связанные артефакты

Единая постановка исследования делает цель, критерии, сохранение и завершение проверяемыми до
запуска, а разделение с Runtime Configuration позволяет менять инфраструктуру без изменения
исследовательской политики.

- [ADR-004](../adr/2026-09-adr-004-preservation-policy.md)
- [ADR-005](../adr/2026-09-adr-005-evaluation-result.md)
- [ADR-006](../adr/2026-09-adr-006-research-specification.md)
- [`preservation-contract.md`](preservation-contract.md)
- [`relevance-gate-contract.md`](relevance-gate-contract.md)
- [`sufficiency-gate-contract.md`](sufficiency-gate-contract.md)
