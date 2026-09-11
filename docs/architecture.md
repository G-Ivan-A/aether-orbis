---
status: draft
version: 0.3
updated: 2026-09-11
temperature: 0.2
---

# AetherOrbis — Архитектура

Документ описывает **как** система устроена: потоки данных, зоны ответственности и точки принятия
решений. Что именно система делает — см. [`docs/concept.md`](concept.md). Термины употребляются в
значении [`docs/standards/glossary.md`](standards/glossary.md).

Разделы 2–7 отражают реализацию Фазы 1 (`src/aether_orbis/`), разделы 8–9 — целевое развёртывание
по [ADR-003](adr/2026-08-adr-003-infrastructure.md), которое ещё не выполнено.

## 1. Контекстная диаграмма

```mermaid
graph LR
    EXT[Внешние источники<br/>web, ленты, поиск]
    AO[AetherOrbis<br/>Web Knowledge Acquisition]
    AN[Аналитический компонент<br/>потребитель контекста]
    OPS[Оператор / исследователь]
    RP[Research Profile<br/>исследовательская политика]
    RC[Runtime Configuration<br/>модели, workers, stores, budgets]
    LLM[Провайдеры моделей<br/>RF / China / прочие]

    EXT -->|HTTP| AO
    OPS --> RP
    OPS --> RC
    RP --> AO
    RC --> AO
    AO <-->|Model Router| LLM
    AO -->|формализованный контракт| AN
    AO -->|телеметрия| OPS
```

## 2. Основной поток данных

```mermaid
flowchart TD
    S[Sources] --> ING[Ingestion<br/>нормализация + content identity]
    ING --> RAW[(Raw / Source Store)]
    RAW --> TR{Triage Evaluation<br/>+ Decision Policy}

    TR -->|REJECTED — без затрат на Extraction| PRES[(Preserved Records<br/>по Preservation Policy)]
    TR -->|оценка продолжается| EXTR[Extraction<br/>entities, relations, claims<br/>+ evidence + content identity]

    EXTR --> EV[Full Evaluation<br/>EvaluationResult]
    EV --> DP{Decision Policy<br/>QualificationDecision}

    DP -->|любое решение, включая REJECTED| PRES
    DP -->|QUALIFIED / CONDITIONAL| KB[Knowledge Builder<br/>Knowledge Product]

    KB --> GRAPH[(Graph Store)]
    KB --> VEC[(Vector Index)]
    KB --> SG{Sufficiency Gate}

    SG -->|success conditions не выполнены,<br/>бюджет остался| EXP[Расширение frontier]
    SG --> OUT[Research Run Outcome<br/>SUFFICIENT / PARTIAL / ZERO /<br/>CONFLICT / EXHAUSTED]

    EXP --> ING
    OUT --> CP[Context Package<br/>контракт для потребителя]
    CP --> AN[Analysis]

    PRES -.->|повторное использование<br/>при смене вопроса| KB
```

Квалификация разделена на два шага: дешёвый **Triage Evaluation** решает, стоит ли платить за
Extraction, а **Full Evaluation** оценивает уже извлечённое знание. Решение в обоих случаях
принимает не Evaluation, а отдельная версионированная **Decision Policy**: `EvaluationResult`
содержит только именованные характеристики с rationale ([ADR-005](adr/2026-09-adr-005-evaluation-result.md)).
Отклонённый материал не исчезает: **Preserved Record** с content identity и provenance создаётся для
каждого оценённого материала независимо от решения, а состав записи задаёт объявленная Preservation
Policy ([ADR-004](adr/2026-09-adr-004-preservation-policy.md)).

Граф и вектор строятся **параллельно и независимо** из одного и того же квалифицированного потока:
вектор не является следствием построения графа, ни одно из двух представлений не является
предусловием другого, и прогон с одним отключённым представлением — или без обоих — даёт тот же
Research Run document. Sufficiency Gate тоже читает квалифицированный поток напрямую, а не
результаты индексации.

## 3. Зоны ответственности

```mermaid
graph TB
    subgraph Z1["Зона 1 — Acquisition"]
        A1[Ingestion]
        A2[Raw / Source Store]
        A3[Extraction]
    end
    subgraph Z2["Зона 2 — Selection"]
        B1[Evaluation → EvaluationResult]
        B2[Decision Policy → QualificationDecision]
        B3[Preserved Records]
    end
    subgraph Z3["Зона 3 — Representation"]
        C1[Knowledge Builder]
        C2[Graph Store]
        C3[Vector Index]
    end
    subgraph Z4["Зона 4 — Decision"]
        D1[Sufficiency Gate]
        D2[Human-in-the-loop]
    end
    subgraph Z5["Зона 5 — Consumption"]
        E1[Context Package → Analysis]
    end
    subgraph Z0["Сквозные — Cross-cutting"]
        X1[Research Run<br/>оркестрация и бюджет]
        X2[Model Router]
        X3[Telemetry]
        X4[Config / YAML]
    end

    Z1 --> Z2 --> Z3 --> Z4 --> Z5
    Z0 -.-> Z1
    Z0 -.-> Z2
    Z0 -.-> Z3
    Z0 -.-> Z4
    Z0 -.-> Z5
```

| Зона | Владеет | Не имеет права |
| --- | --- | --- |
| Acquisition | сбором, хранением сырого материала, извлечением утверждений с evidence | строить знание, оценивать релевантность для задачи |
| Selection | измерением характеристик (`EvaluationResult`), решением `QUALIFIED` / `CONDITIONAL` / `REJECTED` и сохранением отклонённого материала | изменять содержимое claims, смешивать оценку с решением |
| Representation | решением, что становится узлом и ребром, и entity resolution | пере-извлекать данные из источника |
| Decision | итогом `SUFFICIENT` / `PARTIAL` / `ZERO` / `CONFLICT` / `EXHAUSTED` | делать предметные выводы |
| Consumption | рассуждением поверх Context Package | обращаться к источникам напрямую в обход контракта |
| Cross-cutting | версиями прогона, бюджетом, выбором модели, наблюдаемостью, конфигурацией | задавать исследовательские критерии и принимать решения gates |

Жёсткое правило: **Parser ≠ Knowledge Builder ≠ Analysis**. Флаг вида `--build-graph` внутри
парсера отклонён как нарушение границы зон.

## 4. Точки вариативности пайплайна

Единый acquisition pipeline конфигурируется в четырёх контрактных точках:

1. **Research Specification** — цель, target и стратегия frontier.
2. **EvaluationResult + Decision Policy** — измеряемые характеристики и правила вывода решения.
3. **Preservation Policy** — состав сохраняемого материала, производного знания и истории.
4. **Termination / Sufficiency Policy** — условия завершения и статус исхода прогона.

Это **контрактные точки вариативности**, а не отдельные runtime-компоненты. Компонентные границы и
последовательность основного потока данных остаются общими для всех моделей Acquisition: в Фазе 1
`AM-1 Domain Monitoring` и `AM-2 Entity / Relationship Extraction` исполняются одной кодовой базой
и различаются только Research Specification.
Research Profile содержит исследовательскую политику, а отдельная Runtime Configuration — модели,
workers, stores, budgets и retries; смешение этих классов запрещено схемами.

## 5. Логика квалификации материала

```mermaid
stateDiagram-v2
    [*] --> Triage
    Triage: дешёвая ранняя оценка относительно Research Specification
    Triage --> Extraction: решение не REJECTED
    Triage --> Rejected: REJECTED до затрат на Extraction
    Extraction: entities, relations, claims с evidence
    Extraction --> Evaluation
    Evaluation: многомерная оценка извлечённого знания
    Evaluation --> EvaluationResult
    EvaluationResult: именованные характеристики с rationale, без решения
    EvaluationResult --> DecisionPolicy
    DecisionPolicy: версионированные упорядоченные правила
    DecisionPolicy --> Qualified: QUALIFIED
    DecisionPolicy --> Conditional: CONDITIONAL
    DecisionPolicy --> Rejected: REJECTED
    Qualified --> [*]: в Knowledge Builder
    Conditional --> [*]: в Knowledge Builder с зафиксированными ограничениями
    Rejected --> Preserved: Preserved Record по Preservation Policy
    Preserved --> [*]
```

Обе стадии оценки и оба решения — с идентичностью, версией политики и rationale — попадают в
Research Run document, поэтому исход прогона восстановим без доступа к содержимому источников.
Нормативная форма перехода — [`relevance-gate-contract`](standards/relevance-gate-contract.md).

## 6. Логика Sufficiency Gate

```mermaid
stateDiagram-v2
    [*] --> Evaluate
    Evaluate: completion dimensions из Research Specification
    Evaluate --> Sufficient: success conditions выполнены
    Evaluate --> Conflict: независимые source groups противоречат
    Evaluate --> Zero: квалифицируемого знания нет
    Evaluate --> Incomplete: остаются gaps
    Incomplete --> Expand: frontier расширяем и runtime budget не исчерпан
    Expand --> Evaluate: повторный сбор, Evaluation и Decision Policy
    Incomplete --> Partial: полезный неполный результат
    Incomplete --> Exhausted: runtime budget исчерпан
    Sufficient --> [*]: SUFFICIENT → Context Package
    Partial --> [*]: PARTIAL + gaps
    Zero --> [*]: ZERO + rationale
    Conflict --> [*]: CONFLICT + source groups
    Exhausted --> [*]: EXHAUSTED + consumed budget
```

Цикл `Incomplete → Expand → Evaluate` ограничен Runtime Configuration: числовые лимиты
(`max_iterations`, `max_cost_rub`) приходят только оттуда, исследовательские критерии — только из
Research Specification. Итог различает неполноту, отсутствие данных, противоречие и исчерпание
ресурсов; каждый статус содержит coverage, gaps, conflicts, recommended expansion и rationale и
передаётся потребителю в составе Context Package.

## 7. Экономика по ролям операций

```mermaid
graph LR
    T[Triage Evaluation<br/>cheapest] --> E[Extraction<br/>cost-sensitive] --> K[Knowledge Building<br/>mid-tier] --> A[Analysis<br/>quality-first]
```

| Шаг | Профиль | Приёмы снижения стоимости |
| --- | --- | --- |
| Triage evaluation | cheapest | оценка без Extraction, отсев до дорогих шагов |
| Extraction | cost-sensitive | дешёвые модели, batch API (−50 %), prompt caching (−90 %), semantic caching |
| Knowledge building | mid-tier | батчирование, дедупликация сущностей |
| Analysis | quality-first | вход ограничен квалифицированным и достаточным контекстом |

Главный рычаг экономики — квалификация: Triage Evaluation определяет, какая доля собранного вообще
доходит до Extraction, а Decision Policy — какая доля извлечённого доходит до Analysis.

## 8. Развёртывание

```mermaid
graph TB
    subgraph SL["Serverless (основной путь)"]
        F1[Ingestion / Extraction workers]
        F2[API — FastAPI]
    end
    subgraph VPS["VPS fallback (stateful)"]
        V1[(Graph Store)]
        V2[(Vector Index)]
        V3[(Object / Raw Store)]
        V4[Observability]
    end
    subgraph EXTP["Внешние провайдеры"]
        P1[Модели RF / China]
    end

    F1 --> V1
    F1 --> V2
    F1 --> V3
    F2 --> V1
    F1 <--> P1
    F2 -->|2FA| U[Публичный API-клиент]
    F1 --> V4
```

Обоснование serverless-first, требований юрисдикции РФ и обязательной 2FA — см.
[ADR-003](adr/2026-08-adr-003-infrastructure.md).

## 9. Граница репозитория и runtime

```mermaid
graph LR
    subgraph REPO["Git-репозиторий"]
        R1[docs/]
        R2[configs/ — YAML]
        R3[src/, tests/]
        R4[.github/, tools/]
    end
    subgraph RUNTIME["Runtime — вне git"]
        T1[(БД: graph, vector, реляционные)]
        T2[(Сырой контент источников)]
        T3[Секреты и ключи API]
        T4[Артефакты прогонов, логи, телеметрия]
    end
    REPO -->|описывает и конфигурирует| RUNTIME
    RUNTIME -.->|никогда не коммитится| REPO
```

## 10. Связанные артефакты

- [`docs/concept.md`](concept.md) — компоненты и контракты
- [`docs/standards/glossary.md`](standards/glossary.md) — единственный источник истины для терминов
- [`docs/standards/research-specification-contract.md`](standards/research-specification-contract.md)
- [`docs/standards/preservation-contract.md`](standards/preservation-contract.md)
- [`docs/standards/sufficiency-gate-contract.md`](standards/sufficiency-gate-contract.md)
- [`configs/schemas/`](../configs/schemas/) — исполняемые схемы контрактов
- [`docs/adr/README.md`](adr/README.md) — технические решения
- [`docs/running-locally.md`](running-locally.md) — как исполнить описанный поток локально
- [`docs/roadmap.md`](roadmap.md) — состояние фаз и границы Фазы 1
