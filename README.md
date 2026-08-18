# AetherOrbis

**Web Knowledge Acquisition Pipeline**: evidence-backed extraction with configurable relevance and
sufficiency gates.

AetherOrbis приобретает внешние источники, извлекает структурированные данные с сохранением
происхождения, оценивает релевантность и достаточность собранного материала и передаёт результат
аналитическому компоненту через формализованный контракт. Если материала недостаточно — система
возвращает явный `ZERO`, а не додумывает недостающее.

Spoke-репозиторий экосистемы
[hybrid-Intelligence-lab](https://github.com/G-Ivan-A/hybrid-Intelligence-lab).

## Статус

Подготовительный R&D (фаза 0 роадмапа). Репозиторий содержит структуру, документацию и контракты;
реализация начинается с фазы 1 — см. [`docs/roadmap.md`](docs/roadmap.md).

## С чего начать

| Вопрос | Документ |
| --- | --- |
| Зачем проект существует | [`docs/vision.md`](docs/vision.md) |
| Как он устроен по компонентам | [`docs/concept.md`](docs/concept.md) |
| Как идут данные и где границы зон | [`docs/architecture.md`](docs/architecture.md) |
| Какие решения приняты и почему | [`docs/adr/README.md`](docs/adr/README.md) |
| Какие контракты обязаны соблюдать компоненты | [`docs/standards/`](docs/standards/) |
| Что делается дальше | [`docs/roadmap.md`](docs/roadmap.md) |

## Пайплайн

```
Sources → Ingestion → Raw Store → Extraction → Relevance Gate → Graph / Vector
        → Sufficiency Gate → Analysis | ZERO
```

Телеметрия снимается на каждом переходе.

## Структура репозитория

| Путь | Содержимое |
| --- | --- |
| `docs/` | документация уровней 1–4, ADR, контракты |
| `configs/` | YAML-конфигурации направлений исследования |
| `src/aether_orbis/` | исходный код (наполняется с фазы 1) |
| `tests/` | тесты, включая контрактные |
| `tools/` | служебные скрипты, в т.ч. валидация именования файлов |
| `experiments/` | экспериментальные скрипты |
| `examples/` | примеры использования |
| `.github/workflows/` | CI |

## Границы репозитория

Репозиторий **не хранит** runtime-данные: базы (graph, vector, реляционные), сырой контент
источников, секреты и ключи API, артефакты прогонов, логи и телеметрию. См.
[`.gitignore`](.gitignore) и [ADR-003](docs/adr/2026-08-adr-003-infrastructure.md).

## Соглашения об именовании

| Контекст | Форма |
| --- | --- |
| Репозиторий | `aether-orbis` |
| Бренд | `AetherOrbis` |
| Python-пакеты | `aether_orbis` |
| Переменные окружения | `AETHER_ORBIS_API_KEY` |
| Docker-образы | `aether-orbis-parser` |

## Участие

См. [`CONTRIBUTING.md`](CONTRIBUTING.md) (человеческий workflow) и [`GOVERNANCE.md`](GOVERNANCE.md)
(правила AI-assisted работы).

## Лицензия

[MIT](LICENSE).
