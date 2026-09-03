# Changelog

Формат — [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
версионирование — [SemVer](https://semver.org/lang/ru/).

## [Unreleased]

### Added

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

- `docs/vision.md` переписан как долгосрочное видение и миссия, без технических деталей MVP.
- `docs/concept.md` дополнен разделами: обобщённая Research Specification, модели Acquisition,
  Preservation Policy, многомерная Evaluation, явные состояния недостаточности.
- `docs/adr/README.md` и `docs/README.md`: реестр ADR и индекс документации дополнены.
