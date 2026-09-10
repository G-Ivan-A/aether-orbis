# examples

| Каталог | Содержимое |
| --- | --- |
| `research-specifications/` | Research Specification для моделей `AM-1`…`AM-5` |
| `acquisition/` | локальный прогон acquisition-ядра на фикстурах `AM-1` и `AM-2` |

```bash
python3 examples/acquisition/local_acquisition_run.py
```

Прогон выполняется оффлайн: источники берутся из `tests/fixtures/acquisition/*/corpus`, все
внешние зависимости закрыты портами. Тот же модуль используется интеграционными тестами
(`tests/test_acquisition_run.py`), поэтому пример и ожидания не могут разойтись.
