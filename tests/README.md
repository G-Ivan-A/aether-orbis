# tests

Suite проверяет исполняемую основу контрактов P1-A и acquisition-ядро P1-B.

| Группа | Что проверяет |
| --- | --- |
| Frontier | построение фронтира из спецификации для `enumerate`, `expand`, `query` |
| Ingestion | нормализация обычного, пустого и повреждённого материала, обязательная идентичность |
| Grouping | `source_group_id` только по точному canonical URL или точному content hash |
| Extraction | дословная проверяемость evidence fragments и три раздельные характеристики |
| Evaluation | хранимый `EvaluationResult`, повторное применение Decision Policy без переоценки |
| Preservation | все допустимые на фазе 1 комбинации сохранения и accepted risk |
| Module boundaries | отсутствие критериев отбора вне спецификации и stdlib-only рантайм |
| Acquisition run | локальные прогоны `AM-1` и `AM-2` от спецификации до сохранённого знания |
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

Fixtures acquisition-прогонов находятся в `tests/fixtures/acquisition/{am-1,am-2}`; обвязка
прогона живёт в `examples/acquisition/local_acquisition_run.py`.

Contract fixtures находятся в `tests/fixtures/contracts/{valid,invalid}`. Имя файла начинается с имени
схемы, затем следует `--<case>.yaml`; валидатор использует эту связь как проверяемый контракт.
