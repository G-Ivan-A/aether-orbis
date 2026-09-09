---
status: proposed
version: 1.0
updated: 2026-09-09
temperature: 0.1
owner: G-Ivan-A
---

# Глоссарий AetherOrbis

Единственный источник истины для терминов проекта. Контракты и ADR **НЕ ДОЛЖНЫ** переопределять
термины — они ссылаются сюда. Термины уровня экосистемы наследуются из `standards/glossary.md`
Хаба ([hybrid-Intelligence-lab](https://github.com/G-Ivan-A/hybrid-Intelligence-lab)).

| Термин | Определение |
| --- | --- |
| Acquisition | Приобретение внешних источников: discovery, получение, нормализация и фиксация происхождения. |
| Acquisition Model | Один из пяти классов движения по пространству источников: AM-1 Domain Monitoring, AM-2 Entity / Relationship Extraction, AM-3 Question-driven Research, AM-4 Property / Market Monitoring, AM-5 Open-ended Discovery. |
| Analysis | Компонент-потребитель, выполняющий предметное рассуждение поверх проверенного knowledge product. |
| Claim | Утверждение, извлечённое из источника и сопровождаемое evidence, extraction confidence и content identity. |
| `CONDITIONAL` | QualificationDecision: материал можно использовать только с явно указанными ограничениями. |
| `CONFLICT` | Research Run Outcome: независимые квалифицированные source groups материально противоречат друг другу. |
| `CONTRADICTED` | Состояние relation: evidence содержит материальное опровержение наблюдаемой связи. |
| Decision Policy | Версионированные упорядоченные правила, преобразующие характеристики EvaluationResult в QualificationDecision. |
| Derived Knowledge | Сохраняемый результат обработки приобретённого материала: claims, relations или полный knowledge product. |
| Evidence | Проверяемый фрагмент источника с `source_id`, `fragment`, `retrieved_at` и evidence strength. |
| Evidence Strength | Числовая оценка того, насколько evidence поддерживает конкретный элемент; не качество извлечения и не авторитет источника. Поле: `evidence_strength`. |
| Evaluation | Измерение именованных характеристик материала на стадии triage или full evaluation без принятия квалификационного решения. |
| EvaluationResult | Неизменяемый версионированный результат Evaluation: subject identity, stage, открытая карта характеристик с rationale и время оценки. |
| `EXHAUSTED` | Research Run Outcome: runtime budget исчерпан до достижения success conditions. |
| Extraction | Извлечение entities, relations и claims из нормализованного содержимого с evidence и content identity. |
| Extraction Confidence | Локальная числовая оценка корректности конкретного извлечённого элемента. Поле: `extraction_confidence`. |
| Graph / Knowledge Builder | Компонент, формирующий knowledge product и решающий, какие квалифицированные элементы становятся узлами и рёбрами. |
| Human-in-the-loop | Явная точка вмешательства человека, сохраняющая автора, rationale и исходное автоматическое решение. |
| Knowledge Product | Ожидаемый предметный результат Research Specification: классификация, граф, ответы, изменения свойств или discovery candidates. |
| `NOT_OBSERVED` | Состояние relation: связь не найдена в исследованном материале; не эквивалентно отсутствию связи в реальности. |
| `OBSERVED` | Состояние relation: связь непосредственно поддержана извлечённым evidence. |
| Parser | Компонент нормализации приобретённого содержимого; не весь research pipeline и не синоним Extraction. |
| Preservation Policy | Декларация трёх независимых измерений: acquired artifact, derived knowledge и observation history. |
| Preserved Record | Сохраняемая запись, которая при любой Preservation Policy удерживает content identity и provenance. |
| Provenance | Прослеживаемость элемента до конкретного фрагмента, версии обработки и идентичности полученного содержимого. |
| `PARTIAL` | Research Run Outcome: полезное знание получено, но обязательные success conditions достигнуты не полностью. |
| `QUALIFIED` | QualificationDecision: материал удовлетворяет применённой Decision Policy. |
| QualificationDecision | Отдельное от EvaluationResult объяснимое решение `QUALIFIED`, `CONDITIONAL` или `REJECTED` с идентичностью и версией политики. |
| `REJECTED` | QualificationDecision: материал не удовлетворяет применённой Decision Policy; оценка и rationale всё равно сохраняются. |
| Research Profile | Устанавливаемая исполняемая конфигурация исследования: identity/support metadata и одна Research Specification; runtime controls не входят. |
| Research Run | Зафиксированное исполнение спецификации с версиями specification/runtime/models, content identities, решениями, итерациями, бюджетом и outcome. |
| Research Run Outcome | Объяснимый итог Research Run: `SUFFICIENT`, `PARTIAL`, `ZERO`, `CONFLICT` или `EXHAUSTED`. |
| Research Specification | Декларативный контракт исследования из шести блоков: objective, target, scope, evaluation, preservation, termination. |
| Runtime Configuration | Отдельная операционная конфигурация моделей, workers, stores, budgets и retries; исследовательская политика не входит. |
| Source Authority | Числовая оценка происхождения и авторитетности источника. Поле характеристики: `source_authority`; не evidence strength и не extraction confidence. |
| Source Group | Группа представлений одного источника для оценки независимости. В Phase 1 объединяется только по точному canonical URL либо content hash. |
| `source_group_id` | Стабильный идентификатор Source Group, обязательный в EvaluationResult. |
| `SUFFICIENT` | Research Run Outcome: все success conditions конкретной Research Specification достигнуты. |
| Sufficiency Gate | Переход, сопоставляющий накопленное знание с termination conditions и формирующий объяснимый Research Run Outcome. |
| Telemetry | Сквозная фиксация latency, cost, operation role, отдельных extraction/evaluation/qualification характеристик и outcome. |
| Triage | Ранняя дешёвая стадия Evaluation; не является полной оценкой и маркируется отдельно. |
| `UNCERTAIN` | Состояние relation: evidence недостаточно для наблюдения или опровержения связи. |
| `ZERO` | Research Run Outcome: прогон не получил квалифицируемого знания и возвращает объяснение вместо синтезированного полного ответа. |

Универсальная характеристика или агрегат с именем `confidence` запрещены: корректность извлечения,
сила evidence и авторитет источника имеют разные владельцы, семантику и поля.

## Связанные артефакты

- [`research-specification-contract.md`](research-specification-contract.md)
- [`preservation-contract.md`](preservation-contract.md)
- [`extraction-contract.md`](extraction-contract.md)
- [`relevance-gate-contract.md`](relevance-gate-contract.md)
- [`sufficiency-gate-contract.md`](sufficiency-gate-contract.md)
- [`telemetry-contract.md`](telemetry-contract.md)
- [ADR-004](../adr/2026-09-adr-004-preservation-policy.md)
- [ADR-005](../adr/2026-09-adr-005-evaluation-result.md)
- [ADR-006](../adr/2026-09-adr-006-research-specification.md)
