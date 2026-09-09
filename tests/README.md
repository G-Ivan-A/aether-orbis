# tests

Контрактный suite проверяет исполняемую основу P1-A до появления acquisition runtime.

| Группа | Что проверяет |
| --- | --- |
| Позитивные fixtures | валидные сущности каждого JSON Schema и expressibility AM-1…AM-5 |
| Негативные fixtures | отсутствие шести блоков, смешение config classes, запрещённые режимы и поля |
| Decision Policy | повторное применение разных политик к одному EvaluationResult |
| Research Run Outcome | `SUFFICIENT`, `PARTIAL`, `ZERO`, `CONFLICT`, `EXHAUSTED` с объяснением |
| Repository artifacts | два профиля, Runtime Configuration и пять примеров проходят схемы |

Запуск:

```bash
python3 -m pip install --user -r requirements-dev.txt
python3 -m unittest discover -s tests -v
```

Fixtures находятся в `tests/fixtures/contracts/{valid,invalid}`. Имя файла начинается с имени
схемы, затем следует `--<case>.yaml`; валидатор использует эту связь как проверяемый контракт.
