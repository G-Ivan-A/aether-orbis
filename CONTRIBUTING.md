# Contributing — AetherOrbis

Проектный профиль: **product** (`product-profile.md` Хаба
[hybrid-Intelligence-lab](https://github.com/G-Ivan-A/hybrid-Intelligence-lab)).
Правила AI-assisted работы вынесены в [`GOVERNANCE.md`](GOVERNANCE.md).

## Роли

| Роль | Кто | Решает |
| --- | --- | --- |
| Product / technical owner | G-Ivan-A | приоритеты, приёмка, ADR |
| Contributor | участник или AI-агент | изменения через issue → PR |
| Reviewer | назначается на PR | соответствие контрактам и стандартам |

## Workflow

1. **Issue до PR.** Изменения кода, контрактов, ADR и структуры каталогов начинаются с issue.
   Исключение — опечатки и правки форматирования.
2. **Ветка** от `main`, имя отражает issue.
3. **PR** ссылается на issue и на затронутые контракты.
4. **Review** обязателен перед merge. Прямые коммиты в `main` не используются.

## Требования к изменениям

- Изменение поведения на границе компонента **требует** обновления соответствующего контракта в
  [`docs/standards/`](docs/standards/) в том же PR.
- Обратно несовместимое изменение контракта **требует** ADR и мажорного повышения `version`
  контракта.
- Архитектурное решение фиксируется ADR по формату `standards/adr-structure-standard.md` Хаба.
- Новое направление исследования добавляется YAML-конфигом в `configs/directions/`, без изменения
  кода модулей.

## Качество

| Проверка | Когда |
| --- | --- |
| `bash tools/validate-file-naming.sh` | локально и в CI |
| `bash tools/validate-frontmatter.sh` | локально и в CI |
| `bash tools/validate-repo-boundary.sh` | локально и в CI |
| `python3 tools/validate-contracts.py` | локально и в CI |
| `python3 -m unittest discover -s tests -v` | локально и в CI |
| Линтеры и тесты кода | с фазы 1 роадмапа |

Запуск локально перед пушем:

```bash
python3 -m pip install --user -r requirements-dev.txt
python3 tools/validate-contracts.py
python3 -m unittest discover -s tests -v
bash tools/validate-file-naming.sh
bash tools/validate-frontmatter.sh
bash tools/validate-repo-boundary.sh
```

## Данные и секреты

В репозиторий **не попадают**: базы данных, сырой и извлечённый контент источников, секреты и ключи
API, артефакты прогонов, логи и телеметрия. См. [`.gitignore`](.gitignore),
[`SECURITY.md`](SECURITY.md) и [ADR-003](docs/adr/2026-08-adr-003-infrastructure.md).

## Definition of Done для PR

- [ ] PR связан с issue.
- [ ] Затронутые контракты и ADR обновлены.
- [ ] Frontmatter изменённых артефактов актуален (`version`, `updated`, `status`).
- [ ] Локальные проверки из раздела «Качество» проходят.
- [ ] CI зелёный.
- [ ] Runtime-данные и секреты не добавлены.
- [ ] AI-участие раскрыто согласно [`GOVERNANCE.md`](GOVERNANCE.md).
