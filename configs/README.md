# configs — контрактные конфигурации

Research Profile задаёт исследовательскую политику, а Runtime Configuration — операционные
параметры. Эти классы разделены и валидируются закрытыми JSON Schemas: перенос budget/model/store в
профиль или objective/evaluation в runtime-конфиг делает файл невалидным.

| Путь | Назначение |
| --- | --- |
| `directions/<direction>/research-profile.yaml` | исполняемый профиль Phase 1 с полной Research Specification |
| `runtime/*.yaml` | модели, workers, stores, budgets и retries без исследовательской политики |
| `schemas/*.schema.json` | JSON Schema Draft 2020-12 для всех контрактных сущностей |

Исполняемые профили Phase 1:

- `hub-practice-analysis` — `AM-1 Domain Monitoring`, стратегия `enumerate`;
- `reputation-technologies` — `AM-2 Entity / Relationship Extraction`, стратегия `expand`.

Общая Research Specification выражает `AM-1`…`AM-5`; примеры находятся в
[`examples/research-specifications/`](../examples/research-specifications/). `AM-3`…`AM-5` не
являются исполняемыми профилями Phase 1. В Phase 1 поддерживается только
`observation_history: latest_only`; `archival` включается только явно.

Проверка всех отслеживаемых конфигураций:

```bash
python3 -m pip install --user -r requirements-dev.txt
python3 tools/validate-contracts.py
```

Конфигурации **не содержат** секретов и ключей API: они передаются переменными окружения
`AETHER_ORBIS_*` (см. [ADR-003](../docs/adr/2026-08-adr-003-infrastructure.md)). Нормативное
разделение классов описано в
[`research-specification-contract.md`](../docs/standards/research-specification-contract.md).

Для операторского прогона на локальном корпусе передайте профиль и путь к каталогу с
`manifest.json`. Ключи манифеста соответствуют значениям frontier профиля. Для другого
направления укажите другой YAML и корпус в той же команде.

```bash
python3 tools/run-research-profile.py \
  --profile configs/directions/hub-practice-analysis/research-profile.yaml \
  --corpus /path/to/local/corpus
```

`--runtime` по умолчанию использует `configs/runtime/default.yaml`. Блок `offline_adapters`
задаёт маркеры извлечения и имеющиеся измерители для оффлайн-прогона. Измерители по словарю
и совпадениям проверяют проводку прогона. Допуск и оценка качества живого пилота описаны в
[#52](https://github.com/G-Ivan-A/aether-orbis/issues/52).

## Маршрутизация моделей

Runtime `models.<role>` ссылается на ключ `model_routes`. Для выбранного маршрута указывают
идентификатор модели в `model`, одобренный HTTPS `api_base`, имя переменной ключа `api_key_env`,
`timeout_seconds` и `max_tokens`. Необязательный `usd_to_rub` нужен для пересчёта оценки стоимости
в рубли. Роли без маршрута сохраняют локальные адаптеры при оффлайн-запуске. Конфиг по умолчанию
не включает вызовы моделей. [Схема runtime](schemas/runtime-configuration.schema.json).

Интеграция для AM-1 устанавливает `requirements-models.txt` и вызывает `build_routed_profile_run`
из `aether_orbis.adapters.model_extraction`. Оператор передаёт проверенные профиль и runtime,
локальную проекцию текста, функцию допуска точного запроса и получателя и приёмник телеметрии.
Запросы выполняются последовательно к одному endpoint без повторов, перенаправлений и fallback.
Для проверки цены фактического пилота нужны сверка журнала провайдера и согласованный курс.
[LiteLLM Python SDK](https://docs.litellm.ai/docs/python_sdk), [задача допуска](https://github.com/G-Ivan-A/aether-orbis/issues/52).
