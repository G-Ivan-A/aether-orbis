# Changelog

Формат — [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
версионирование — [SemVer](https://semver.org/lang/ru/).

## [Unreleased]

### Added

- Persistence и оркестрация P1-C: параллельные graph/vector представления одного
  квалифицированного потока за портами `GraphStore` и `VectorIndex`, Research Run как отдельная
  сущность (версии спецификации, конфигурации и адаптеров, хэши обработанного контента, решения
  triage и полной оценки с обоснованиями, решения о сохранении, итерации, бюджет и итог) и
  Sufficiency Gate с пятью явными статусами `SUFFICIENT` / `PARTIAL` / `ZERO` / `CONFLICT` /
  `EXHAUSTED`.
- Сквозные прогоны AM-1 и AM-2 одной командой без сети и секретов:
  `examples/research-runs/local_research_run.py` и тесты `tests/test_research_run.py`;
  различия направлений живут в Research Specification, а не в ветвлениях пайплайна.
- `docs/analysis/2026-09-10-graph-store-selection.md` с критериями, измерениями и границами
  эксперимента по выбору графового хранилища; воспроизводимые скрипты в `experiments/graph-store/`.
- `docs/running-locally.md`: точные команды локального прогона и явные границы фазы 1.
- Опциональный адаптер `KuzuGraphStore` за тем же портом, что и stdlib-адаптер по умолчанию.
- Acquisition-ядро P1-B: фронтир из Research Specification, нормализация с обязательной
  идентичностью содержимого, дешёвый triage и полная оценка с хранимым `EvaluationResult`,
  извлечение claims/сущностей/связей с дословно проверяемыми evidence fragments, группировка
  источников фазы 1 и сохранение по трём независимым dimensions.
- Порты и оффлайн-адаптеры внешних зависимостей: прогон, тесты и пример выполняются без сети,
  платных API и production-хранилищ.
- Локальные прогоны `AM-1` и `AM-2` на фикстурах: `examples/acquisition/local_acquisition_run.py`
  и интеграционные тесты `tests/test_acquisition_run.py`.
- `docs/analysis/2026-09-10-acquisition-oss-candidates.md` с критериями выбора и измеримыми
  результатами экспериментов в `experiments/oss-candidates/`.
- Исполняемая основа P1-A: двенадцать JSON Schemas контрактов, валидатор репозиторных
  YAML-артефактов и позитивные/негативные contract fixtures.
- Общие Research Specification examples для `AM-1`…`AM-5`; исполняемые профили Phase 1 для
  `AM-1 Domain Monitoring` и `AM-2 Entity / Relationship Extraction`.
- Отдельная Runtime Configuration без исследовательской политики.
- Нормативные контракты Research Specification и Preservation v1.0.
- `docs/analysis/2026-09-02-acquisition-models-variation.md`: анализ репрезентативных моделей
  Research / Acquisition, минимальных различий контрактов и проверка гипотезы уровней сохранения.
- Принятые решения ADR-004 (Preservation Policy), ADR-005 (Evaluation Result и decision layer),
  ADR-006 (обобщённая Research Specification и состояния исхода прогона).
- Подготовительный R&D (фаза 0 роадмапа): структура репозитория по архетипу Spoke Хаба.
- Документы уровней 1–2: `docs/vision.md`, `docs/concept.md`, `docs/architecture.md`.
- ADR уровня 4: ADR-001 (технологический стек), ADR-002 (маршрутизация моделей),
  ADR-003 (инфраструктура).
- Контракты уровня 4: извлечение, Relevance Gate, Sufficiency Gate, телеметрия, глоссарий.
- `docs/roadmap.md` с фазами 0–5, задачами и зависимостями.
- YAML-конфигурации двух направлений MVP.
- Root-артефакты профиля product: `PRODUCT_VISION.md`, `CONTRIBUTING.md`, `GOVERNANCE.md`,
  `SECURITY.md`, `CHANGELOG.md`.
- CI: валидация именования файлов и frontmatter.

### Changed

- ADR-001: отложенный выбор графовой БД заменён явным — движком выбран Kuzu, default фазы 1
  остаётся stdlib-адаптером за тем же портом; зафиксированы последствия миграции (версия 0.2).
- `AcquisitionPipeline.run()` принимает фронтир и уже обработанные `source_id`, что позволяет
  оркестратору расширять фронтир итерациями, решая каждый источник один раз за прогон.
- Контракты Extraction, Evaluation / Qualification, Sufficiency и Telemetry переведены на
  несовместимые версии 1.0 по принятым ADR-004/005/006.
- CI валидирует схемы, конфигурации, examples и запускает контрактные unit tests.
- `docs/vision.md` переписан как долгосрочное видение и миссия, без технических деталей MVP.
- `docs/concept.md` дополнен разделами: обобщённая Research Specification, модели Acquisition,
  Preservation Policy, многомерная Evaluation, явные состояния недостаточности.
- `docs/adr/README.md` и `docs/README.md`: реестр ADR и индекс документации дополнены.
