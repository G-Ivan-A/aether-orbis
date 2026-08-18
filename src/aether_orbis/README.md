# src/aether_orbis

Исходный код пакета `aether_orbis`. На фазе 0 роадмапа кода нет намеренно: подготовительный R&D
фиксирует структуру, контракты и решения, но не реализацию.

Планируемые модули (фазы 1–3, см. [`docs/roadmap.md`](../../docs/roadmap.md)):

| Модуль | Зона ответственности |
| --- | --- |
| `ingestion/` | сбор и нормализация источников |
| `extraction/` | извлечение сущностей, связей и claims с evidence |
| `gates/relevance/` | Relevance / Quality Gate |
| `gates/sufficiency/` | Sufficiency Gate |
| `graph/` | Graph / Context Builder |
| `vector/` | векторная индексация |
| `routing/` | Model Router |
| `telemetry/` | телеметрия |
| `api/` | публичный API (FastAPI, 2FA) |

Границы зон описаны в [`docs/architecture.md`](../../docs/architecture.md), раздел 3.
