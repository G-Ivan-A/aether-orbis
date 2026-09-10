# src/aether_orbis

Исходный код пакета `aether_orbis`. Фаза P1-B добавляет исполняемое acquisition-ядро: прогон от
Research Specification до сохранённого знания без сети, платных API и production-хранилищ.

| Модуль | Зона ответственности |
| --- | --- |
| `frontier.py` | построение фронтира из `specification.scope` (`enumerate`, `expand`, `query`) |
| `ingestion.py` | нормализация материала и обязательная идентичность содержимого |
| `grouping.py` | `source_group_id` фазы 1: только точный canonical URL или точный content hash |
| `extraction.py` | claims, сущности и связи с дословно проверяемыми evidence fragments |
| `evaluation.py` | `EvaluationResult` и отдельный слой Decision Policy |
| `preservation.py` | три независимых dimensions сохранения и accepted risk |
| `pipeline.py` | порядок стадий и ничего кроме порядка |
| `ports.py` | порты внешних зависимостей (`SourceFetcher`, `ContentParser`, `KnowledgeExtractor`, `CharacteristicEvaluator`, `TelemetrySink`) |
| `adapters/` | оффлайн-адаптеры портов: парсеры, фикстурные fetchers, правиловый extractor, конфигурируемый evaluator |
| `telemetry.py`, `clock.py`, `model.py`, `errors.py` | телеметрия, детерминированное время, value objects, ошибки |

Рантайм-ядро использует только стандартную библиотеку — это проверяется тестом
`tests/test_module_boundaries.py`. Опциональные библиотеки (например Trafilatura) импортируются
лениво внутри адаптеров и деградируют к stdlib-реализации. Выбор OSS-решений обоснован в
[`docs/analysis/2026-09-10-acquisition-oss-candidates.md`](../../docs/analysis/2026-09-10-acquisition-oss-candidates.md).

Планируемые модули фаз 2–3 (см. [`docs/roadmap.md`](../../docs/roadmap.md)): `graph/`, `vector/`,
`routing/`, `api/`. Границы зон описаны в
[`docs/architecture.md`](../../docs/architecture.md), раздел 3.
