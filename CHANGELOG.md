# Changelog

Формат — [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
версионирование — [SemVer](https://semver.org/lang/ru/).

## [Unreleased]

### Added

- Исполняемая основа P1-A: двенадцать JSON Schemas контрактов, валидатор репозиторных
  YAML-артефактов и позитивные/негативные contract fixtures.
- Общие Research Specification examples для `AM-1`…`AM-5`; исполняемые профили Phase 1 для
  `AM-1 Domain Monitoring` и `AM-2 Entity / Relationship Extraction`.
- Отдельная Runtime Configuration без исследовательской политики.
- Нормативные контракты Research Specification и Preservation v1.0.
- `docs/analysis/2026-09-02-acquisition-models-variation.md`: анализ репрезентативных моделей
  Research / Acquisition, минимальных различий контрактов и проверка гипотезы уровней сохранения.
- Проекты ADR: ADR-004 (Preservation Policy), ADR-005 (Evaluation Result и decision layer),
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

- Контракты Extraction, Evaluation / Qualification, Sufficiency и Telemetry переведены на
  несовместимые версии 1.0 по принятым ADR-004/005/006.
- CI валидирует схемы, конфигурации, examples и запускает контрактные unit tests.
- `docs/vision.md` переписан как долгосрочное видение и миссия, без технических деталей MVP.
- `docs/concept.md` дополнен разделами: обобщённая Research Specification, модели Acquisition,
  Preservation Policy, многомерная Evaluation, явные состояния недостаточности.
- `docs/adr/README.md` и `docs/README.md`: реестр ADR и индекс документации дополнены.
