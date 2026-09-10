# experiments

Минимальные воспроизводимые эксперименты, на результатах которых основаны документы
`docs/analysis/`. Скрипты не пишут артефакты в репозиторий и не требуют учётных данных.

| Скрипт | Что измеряет | Документ |
| --- | --- | --- |
| `oss-candidates/content_extraction.py` | recall содержимого и отсечение boilerplate на размеченном корпусе | [2026-09-10-acquisition-oss-candidates.md](../docs/analysis/2026-09-10-acquisition-oss-candidates.md) |
| `oss-candidates/dependency_footprint.py` | число транзитивных пакетов кандидатов (резолвер pip, `--dry-run`) | тот же |

```bash
python3 experiments/oss-candidates/content_extraction.py
python3 experiments/oss-candidates/dependency_footprint.py --names
```

`content_extraction.py` работает полностью оффлайн; `dependency_footprint.py` обращается к
индексу пакетов только для разрешения зависимостей и ничего не устанавливает.
