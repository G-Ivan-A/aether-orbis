---
status: draft
version: 0.1
updated: 2026-08-18
temperature: 0.2
---

# AetherOrbis — Архитектура

Документ описывает **как** система устроена: потоки данных, зоны ответственности и точки принятия
решений. Что именно система делает — см. [`docs/concept.md`](concept.md).

## 1. Контекстная диаграмма

```mermaid
graph LR
    EXT[Внешние источники<br/>web, ленты, поиск]
    AO[AetherOrbis<br/>Web Knowledge Acquisition]
    AN[Аналитический компонент<br/>потребитель контекста]
    OPS[Оператор / исследователь]
    LLM[Провайдеры моделей<br/>RF / China / прочие]

    EXT -->|HTTP| AO
    OPS -->|YAML-конфиг направления| AO
    AO <-->|Model Router| LLM
    AO -->|формализованный контракт| AN
    AO -->|телеметрия| OPS
```

## 2. Основной поток данных

```mermaid
flowchart TD
    S[Sources] --> ING[Ingestion]
    ING --> RAW[(Raw / Source Store)]
    RAW --> EXTR[Extraction<br/>entities, relations, claims<br/>+ evidence + confidence]
    EXTR --> RG{Relevance /<br/>Quality Gate}

    RG -->|not_relevant| SI[(Source Intelligence<br/>метаданные + summary + причина)]
    RG -->|relevant| GB[Graph / Context Builder]

    GB --> GRAPH[(Graph Store)]
    GB --> VEC[(Vector Index)]

    GRAPH --> SG{Sufficiency Gate}
    VEC --> SG

    SG -->|достаточно| AN[Analysis]
    SG -->|недостаточно| EXP[Расширение сбора /<br/>уточняющий запрос]
    SG -->|исчерпано| ZERO[ZERO<br/>insufficient evidence]

    EXP --> ING
    AN --> RES[Результат / решение / артефакт]

    SI -.->|повторное использование<br/>при смене вопроса| GB
```

Граф и вектор строятся **параллельно** из одного и того же прошедшего gate материала; вектор не
является следствием построения графа.

## 3. Зоны ответственности

```mermaid
graph TB
    subgraph Z1["Зона 1 — Acquisition"]
        A1[Ingestion]
        A2[Raw / Source Store]
        A3[Extraction]
    end
    subgraph Z2["Зона 2 — Selection"]
        B1[Relevance / Quality Gate]
        B2[Source Intelligence]
    end
    subgraph Z3["Зона 3 — Representation"]
        C1[Graph / Context Builder]
        C2[Graph Store]
        C3[Vector Index]
    end
    subgraph Z4["Зона 4 — Decision"]
        D1[Sufficiency Gate]
        D2[Human-in-the-loop]
    end
    subgraph Z5["Зона 5 — Consumption"]
        E1[Analysis]
    end
    subgraph Z0["Сквозные — Cross-cutting"]
        X1[Model Router]
        X2[Telemetry]
        X3[Config / YAML]
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
| Acquisition | сбором, хранением сырого материала, извлечением утверждений | строить граф, оценивать релевантность для задачи |
| Selection | решением relevant / not_relevant и сохранением отброшенного | изменять содержимое claims |
| Representation | решением, что становится ребром графа, и entity resolution | пере-извлекать данные из источника |
| Decision | решением «достаточно / недостаточно / ZERO» | делать предметные выводы |
| Consumption | рассуждением поверх контекста | обращаться к источникам напрямую в обход контракта |
| Cross-cutting | выбором модели, наблюдаемостью, конфигурацией | принимать решения gates |

Жёсткое правило: **Parser ≠ Graph Builder ≠ Analysis**. Флаг вида `--build-graph` внутри парсера
отклонён как нарушение границы зон.

## 4. Логика Relevance Gate

```mermaid
stateDiagram-v2
    [*] --> Scoring
    Scoring: оценка по критериям YAML-профиля
    Scoring --> Relevant: score >= threshold
    Scoring --> NotRelevant: score < threshold
    Relevant --> [*]: в Graph / Context Builder
    NotRelevant --> Archived: summary + метаданные + reason
    Archived --> [*]: в Source Intelligence
```

## 5. Логика Sufficiency Gate

```mermaid
stateDiagram-v2
    [*] --> Evaluate
    Evaluate: покрытие вопроса, плотность evidence,<br/>конфликты, доля UNCERTAIN
    Evaluate --> Sufficient: критерии достаточности выполнены
    Evaluate --> Insufficient: критерии не выполнены
    Insufficient --> Expand: бюджет итераций не исчерпан
    Expand --> Evaluate: повторный сбор и Relevance Gate
    Insufficient --> Zero: бюджет / источники исчерпаны
    Sufficient --> [*]: в Analysis
    Zero --> [*]: явный отказ, insufficient evidence
```

Цикл `Insufficient → Expand → Evaluate` ограничен бюджетом итераций и бюджетом стоимости; выход по
исчерпанию любого из них даёт `ZERO`, а не «лучшее из имеющегося».

## 6. Экономика по ролям операций

```mermaid
graph LR
    E[Extraction<br/>cost-sensitive] --> G[Graph Building<br/>mid-tier] --> A[Analysis<br/>quality-first]
```

| Шаг | Профиль | Приёмы снижения стоимости |
| --- | --- | --- |
| Extraction | cost-sensitive | дешёвые модели, batch API (−50 %), prompt caching (−90 %), semantic caching |
| Graph building | mid-tier | батчирование, дедупликация сущностей |
| Analysis | quality-first | вход ограничен прошедшим оба gate контекстом |

Relevance Gate — главный рычаг экономики: он определяет, какая доля собранного вообще доходит до
дорогого шага.

## 7. Развёртывание

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

## 8. Граница репозитория и runtime

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

## 9. Связанные артефакты

- [`docs/concept.md`](concept.md) — компоненты и контракты
- [`docs/standards/`](standards/) — контракты границ
- [`docs/adr/README.md`](adr/README.md) — технические решения
