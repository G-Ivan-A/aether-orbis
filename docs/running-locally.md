---
status: draft
version: 0.1
updated: 2026-09-10
temperature: 0.1
---

# Локальный запуск: от фикстуры до Context Package

Документ содержит точные команды, которыми Research Run фазы 1 воспроизводится локально, и
границы того, что фаза 1 доказывает. Всё исполняется **без сети, секретов и внешних сервисов**:
источники — фикстуры репозитория, оба представления — оффлайн-адаптеры.

## 1. Установка

```bash
python3 -m pip install --user -r requirements-dev.txt
```

Рантайм-ядро `src/aether_orbis` работает на stdlib; зависимости нужны тестам, валидаторам и
опциональному графовому движку (`kuzu`). Тесты, которым нужен Kuzu, пропускаются при его
отсутствии, поэтому stdlib-checkout остаётся зелёным.

## 2. Сквозные прогоны AM-1 и AM-2

Одна команда выполняет оба направления на одном и том же коде:

```bash
python3 examples/research-runs/local_research_run.py
```

Ожидаемый вывод (детерминирован на фикстурах репозитория):

```
am-1: PARTIAL
  1 iteration(s), 3 source(s), 3 recorded decision(s)
  coverage: {"window_coverage": 0.75}
  gap: window_coverage is 0.75 and does not satisfy gte 1.0: 3 of 4 retrieved material(s)
       reached a decision; 1 could not be normalized.
  graph: 5 node(s), 8 edge(s); vector: 3 chunk(s)
am-2: SUFFICIENT
  2 iteration(s), 4 source(s), 4 recorded decision(s)
  coverage: {"neighborhood_completeness": 1.0, "new_entity_saturation": 0.0}
  graph: 11 node(s), 26 edge(s); vector: 6 chunk(s)
```

Различия между направлениями живут **только** в Research Specification и Runtime Configuration:
AM-1 объявляет стратегию `enumerate` и измерение `window_coverage`, AM-2 — стратегию `expand`,
`neighborhood_completeness` и `new_entity_saturation`. Ветвлений по имени модели в пайплайне нет.

AM-1 намеренно завершается статусом `PARTIAL`: один документ корпуса не нормализуется, и прогон
сообщает об этом дырой в покрытии, а не сгенерированным ответом.

Отдельный прогон только стадий acquisition (без оркестрации и представлений):

```bash
python3 examples/acquisition/local_acquisition_run.py
```

## 3. Проверки

```bash
python3 tools/validate-contracts.py
python3 -m unittest discover -s tests -v
./tools/validate-file-naming.sh
./tools/validate-frontmatter.sh
./tools/validate-repo-boundary.sh
```

Те же команды выполняет CI ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)).

## 4. Эксперименты по выбору графового хранилища

```bash
python3 experiments/graph-store/traversal_benchmark.py
python3 experiments/graph-store/deployment_footprint.py --names
```

Результаты и их границы — в
[`analysis/2026-09-10-graph-store-selection.md`](analysis/2026-09-10-graph-store-selection.md);
принятое решение — в [ADR-001](adr/2026-08-adr-001-tech-stack.md), пункт 2.

## 5. Что фаза 1 доказывает и чего не делает

**Доказывает**

- один код исполняет два направления, различающиеся только спецификацией;
- граф и вектор индексируют один и тот же квалифицированный поток **независимо**: отключение
  одного представления не ломает другое и не меняет документ прогона;
- от сущности в графе и от чанка в векторе есть путь к provenance и evidence источника;
- Research Run — отдельная сущность: версии спецификации, конфигурации и адаптеров, хэши
  обработанного контента, решения triage и полной оценки с обоснованиями, решения о сохранении,
  итерации, потреблённый бюджет и итог;
- каждый прогон завершается одним из `SUFFICIENT`, `PARTIAL`, `ZERO`, `CONFLICT`, `EXHAUSTED`
  с покрытием, дырами, конфликтами и рекомендацией расширения; недостаточность не подменяется
  сгенерированным ответом.

**Границы (не входит в фазу 1)**

- источники — только локальные фикстуры: сеть, платные API и браузерный рантайм подключаются
  адаптерами за портами и в фазу 1 не входят;
- извлечение — правиловое (`DictionaryExtractor`); LLM-извлечение относится к фазе 2;
- `source_group_id` формируется только по `canonical_url` или точному `content_hash`;
  `observation_history` принимает только `latest_only`;
- ретрив вектора — детерминированный bag-of-words, а не эмбеддинги;
- телеметрия минимальна и техническая; production-контракт телеметрии — фаза 3;
- persistence по умолчанию in-memory: Kuzu включается путём к базе, а сама база — артефакт
  рантайма и в репозиторий не попадает ([CONTRIBUTING](../CONTRIBUTING.md));
- маршрутизация моделей РФ/Китая, human-in-the-loop, FastAPI и production-инфраструктура —
  фазы 2–5.
