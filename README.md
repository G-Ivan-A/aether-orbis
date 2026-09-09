# AetherOrbis

**Web Knowledge Acquisition Pipeline**: evidence-backed extraction with configurable evaluation,
preservation and sufficiency policies.

AetherOrbis приобретает внешние источники, извлекает структурированные данные с сохранением
происхождения, оценивает релевантность и достаточность собранного материала и передаёт результат
аналитическому компоненту через формализованный контракт. Прогон завершается объяснимым
`SUFFICIENT`, `PARTIAL`, `ZERO`, `CONFLICT` или `EXHAUSTED`, а не додумывает недостающее.

Spoke-репозиторий экосистемы
[hybrid-Intelligence-lab](https://github.com/G-Ivan-A/hybrid-Intelligence-lab).

## Статус

Основа контрактов P1-A реализована: JSON Schemas, позитивные и негативные fixtures, два исполняемых
профиля Phase 1 (`AM-1`, `AM-2`), отдельная Runtime Configuration и примеры общей Research
Specification для `AM-1`…`AM-5`. Acquisition runtime и end-to-end исполнение остаются задачами
P1-B/P1-C — см. [`docs/roadmap.md`](docs/roadmap.md).

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
Research Profile ─┐
                  ├→ Research Run
Runtime Config ───┘

Sources → Acquisition → Extraction → EvaluationResult → Decision Policy
        → Knowledge Product → Sufficiency Gate
        → SUFFICIENT | PARTIAL | ZERO | CONFLICT | EXHAUSTED
```

Телеметрия снимается на каждом переходе.

## Структура репозитория

| Путь | Содержимое |
| --- | --- |
| `docs/` | документация уровней 1–4, ADR, контракты |
| `configs/` | JSON Schemas, Research Profiles и отдельная Runtime Configuration |
| `src/aether_orbis/` | исходный код (наполняется с фазы 1) |
| `tests/` | контрактные unit tests и позитивные/негативные fixtures |
| `tools/` | служебные скрипты, в т.ч. валидация именования файлов |
| `experiments/` | экспериментальные скрипты |
| `examples/` | валидируемые Research Specification для AM-1…AM-5 |
| `.github/workflows/` | CI |

## Локальная проверка

```bash
python3 -m pip install --user -r requirements-dev.txt
python3 tools/validate-contracts.py
python3 -m unittest discover -s tests -v
```

Полный набор проверок указан в [`CONTRIBUTING.md`](CONTRIBUTING.md); схема Research Specification
описана в [`docs/standards/research-specification-contract.md`](docs/standards/research-specification-contract.md).

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
