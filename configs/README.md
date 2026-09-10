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
