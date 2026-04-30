# SAP RAG Search Service

Сервис семантического поиска по SAP-обращениям с RAG-пайплайном:
- векторный поиск (pgvector),
- реранжинг (cross-encoder),
- нечёткий поиск (pg_trgm),
- генерация ответа через LLM.

## Архитектура

```mermaid
flowchart TD
    userQuery[UserQuery] --> vectorSearch[VectorSearchPgvectorTopK]
    userQuery --> fuzzySearch[FuzzySearchPgTrgmTopK]
    vectorSearch --> reranker[CrossEncoderReranker]
    reranker --> mergeStep[MergeAndDedup]
    fuzzySearch --> mergeStep
    mergeStep --> finalContext[SelectFinalContext]
    finalContext --> llmCall[LLMClientGenerate]
    llmCall --> response[ApiResponseAnswerAndSources]
    mergeStep --> fallback[SearchOnlyFallback]
    fallback --> response
```

## Структура проекта

- `services/vectorizer/main.py` — индексация тикетов, чанкинг, эмбеддинги.
- `services/search/main.py` — API поиска `POST /search`.
- `common/search_pipeline.py` — оркестрация этапов поиска и генерации.
- `common/reranker.py` — cross-encoder реранжер.
- `common/fuzzy_search.py` — fuzzy-этап.
- `common/llm_client.py` — OpenAI/local клиенты.
- `migrations/versions/0001_initial.py` — расширения и индексы PostgreSQL.

### Подробно: что за что отвечает

#### 1) API-слой (`services/`)

- `services/search/main.py`
  - поднимает FastAPI-приложение поиска;
  - собирает `SearchPipeline` из компонентов (reranker, LLM-клиент, конфиг);
  - обрабатывает `POST /search` и `GET /health`.
- `services/vectorizer/main.py`
  - принимает тикеты на индексацию через `POST /index`;
  - может забирать исходные тикеты напрямую из внешней таблицы Postgres через `POST /index-from-source`;
  - выполняет чанкинг текста тикета;
  - генерирует эмбеддинги и записывает чанки в БД;
  - поддерживает идемпотентную переиндексацию (обновление существующего тикета).

#### 2) Домен и пайплайн (`common/`)

- `common/config.py`
  - единая точка конфигурации через переменные окружения;
  - включает фичефлаги этапов (`ENABLE_RERANKING`, `ENABLE_FUZZY_SEARCH`, `ENABLE_LLM`).
- `common/schemas.py`
  - контракты API: входной запрос, источник, итоговый ответ;
  - формализует формат ответа для фронта/интеграций.
- `common/search_pipeline.py`
  - главный оркестратор RAG-процесса:
    1. векторный поиск кандидатов;
    2. реранжинг кандидатов cross-encoder моделью;
    3. fuzzy-поиск по триграммам;
    4. merge + dedup по `(ticket_id, chunk_index)`;
    5. сбор финального контекста;
    6. вызов LLM и fallback на search-only.
  - логирует длительность каждого этапа.
- `common/repository.py`
  - SQL-доступ к данным поиска;
  - функции векторного и fuzzy-поиска в PostgreSQL.
- `common/fuzzy_search.py`
  - адаптер fuzzy-поиска для пайплайна;
  - нормализует/взвешивает fuzzy-score.
- `common/reranker.py`
  - абстракция реранкера (`BaseReranker`);
  - реализация на локальном `sentence-transformers` (`CrossEncoderReranker`).
- `common/llm_client.py`
  - абстракция LLM-клиента (`BaseLLMClient`);
  - `OpenAIClient` (в т.ч. совместимый endpoint LM Studio);
  - `LocalLLMClient` для локальной генерации через `transformers`.
- `common/prompt_templates.py`
  - шаблон промпта RAG;
  - сборка контекста из выбранных чанков.
- `common/embeddings.py`
  - загрузка embedding-модели;
  - получение вектора для текста.
- `common/db.py`
  - инициализация async SQLAlchemy engine/session;
  - dependency для FastAPI.
- `common/models.py`
  - ORM-модели `tickets` и `ticket_embeddings`.

#### 3) Данные и миграции (`migrations/`)

- `migrations/versions/0001_initial.py`
  - создаёт таблицы и индексы;
  - включает расширения `vector` и `pg_trgm`;
  - добавляет индексы для ускорения vector/fuzzy-поиска.
- `alembic.ini`, `migrations/env.py`
  - конфигурация и запуск миграций.

#### 4) Инфраструктура и запуск

- `docker-compose.yml`
  - поднимает `postgres`, `search`, `vectorizer`.
- `Dockerfile.search`, `Dockerfile.vectorizer`
  - контейнеризация сервисов.
- `Makefile`
  - команды верхнего уровня: `up`, `migrate`, `test`.
- `.env.example`, `.env.openai.example`, `.env.lmstudio.example`
  - профили конфигурации окружения.
- `requirements.txt`
  - зависимости рантайма и тестов.
- `sql/source_schema_template.sql`
  - шаблон внешней таблицы-источника для индексации.
- `sql/source_schema_template_custom.sql`
  - параметризуемый шаблон с плейсхолдерами `{{SCHEMA}}` и `{{TABLE}}`.
- `sql/source_seed_example.sql`
  - пример наполнения внешней таблицы тестовыми данными.

#### 5) Тесты (`tests/`)

- `tests/test_search_pipeline.py`
  - проверка merge/dedup логики и скоринга.
- `tests/test_search_api.py`
  - smoke-тест API (health endpoint).

## Локальный запуск и развёртывание

### 1) Предварительные требования

- `Python 3.11+`
- `Docker` и `Docker Compose`
- (Опционально) `LM Studio`, если хотите использовать локальную LLM вместо облачного API

### 2) Подготовка окружения

1. Скопируйте `.env.example` в `.env` и заполните ключи.
   - Для OpenAI (PowerShell): `Copy-Item .env.openai.example .env`
   - Для LM Studio (PowerShell): `Copy-Item .env.lmstudio.example .env`
2. Установите зависимости (если запускаете Python-часть локально, не только в Docker):
   - `pip install -r requirements.txt`

### 3) Запуск инфраструктуры (PostgreSQL + сервисы)

Через `Makefile`:
- `make up` — поднимает `postgres`, `search`, `vectorizer`
- `make migrate` — применяет миграции
- `make test` — запускает тесты

Эквивалентные команды без `Makefile`:
- `docker compose up --build -d`
- `alembic upgrade head`
- `pytest -q`

Windows PowerShell (рекомендуется для локального теста):
- `docker compose up --build -d`
- `python -m alembic upgrade head`
- `python -m pytest -q`

### 4) Настройка LM Studio как локального LLM

Проект использует OpenAI-совместимый HTTP API, поэтому LM Studio подключается через `LLM_PROVIDER=openai`.

1. Запустите LM Studio.
2. Загрузите чат-модель (например, инструкционную).
3. Включите локальный сервер в LM Studio (OpenAI-compatible endpoint).
4. Укажите в `.env`:

```ini
ENABLE_LLM=true
LLM_PROVIDER=openai
LLM_MODEL=lmstudio-local-model
LLM_BASE_URL=http://host.docker.internal:1234/v1/chat/completions
LLM_API_KEY=lm-studio
```

Примечания:
- `LLM_API_KEY` здесь может быть любым непустым значением (нужен для совместимости клиента).
- Для запуска `search` не в Docker можно использовать `http://localhost:1234/v1/chat/completions`.
- Если LLM временно не нужна, поставьте `ENABLE_LLM=false`, тогда `/search` вернёт search-only результат.

### 5) Индексация из внешней таблицы Postgres

Если исходные обращения загружаются сторонним ETL-инструментом в отдельную таблицу Postgres, можно индексировать их без ручной передачи JSON.

Настраиваемые ENV-параметры:
- `SOURCE_SCHEMA`
- `SOURCE_TABLE`
- `SOURCE_TICKET_ID_COLUMN`
- `SOURCE_QUESTION_COLUMN`
- `SOURCE_ANSWER_COLUMN`
- `SOURCE_FUNCTIONAL_AREA_COLUMN`

SQL-шаблоны в проекте:
- `sql/source_schema_template.sql` — создать схему/таблицу источника;
- `sql/source_schema_template_custom.sql` — создать схему/таблицу с кастомными именами;
- `sql/source_seed_example.sql` — загрузить тестовые записи.

Пример применения SQL-шаблонов:

```bash
psql "postgresql://postgres:postgres@localhost:5432/sap_rag" -f sql/source_schema_template.sql
psql "postgresql://postgres:postgres@localhost:5432/sap_rag" -f sql/source_seed_example.sql
```

Пример использования параметризуемого шаблона:

```bash
sed "s/{{SCHEMA}}/integration/g; s/{{TABLE}}/sap_tickets_raw/g" sql/source_schema_template_custom.sql \
  | psql "postgresql://postgres:postgres@localhost:5432/sap_rag"
```

Windows PowerShell вариант (без `sed`):

```powershell
$schema = "integration"
$table = "sap_tickets_raw"
$sql = Get-Content "sql/source_schema_template_custom.sql" -Raw
$sql = $sql.Replace("{{SCHEMA}}", $schema).Replace("{{TABLE}}", $table)
Set-Content "sql/source_schema.generated.sql" $sql
psql "postgresql://postgres:postgres@localhost:5432/sap_rag" -f "sql/source_schema.generated.sql"
```

Пример вызова:

```bash
curl -X POST http://localhost:8001/index-from-source \
  -H "Content-Type: application/json" \
  -d '{
    "limit": 500,
    "offset": 0
  }'
```

Windows PowerShell вариант:

```powershell
$body = @{
  limit = 500
  offset = 0
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8001/index-from-source" `
  -ContentType "application/json" `
  -Body $body
```

Важно:
- В таблице-источнике должны быть колонки с типами, совместимыми с текстом (`ticket_id`, `question`, `answer`, `functional_area`).
- Сервис читает данные пакетно (`limit`/`offset`) и применяет идемпотентную переиндексацию.
- Если используете другие имена схемы/таблицы/колонок, обязательно синхронизируйте их через `SOURCE_*` переменные в `.env`.

## Пример индексации

```bash
curl -X POST http://localhost:8001/index \
  -H "Content-Type: application/json" \
  -d '{
    "tickets": [
      {
        "ticket_id": "SAP-12345",
        "functional_area": "MM",
        "user_question": "Ошибка при создании заказа",
        "support_answer": "Проверьте тип документа и настройки схемы выпуска."
      }
    ]
  }'
```

## Тестовый запрос поиска

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Как исправить ошибку создания заказа в MM?",
    "functional_area": "MM"
  }'
```

Пример ответа:

```json
{
  "answer": "Проверьте настройки типа документа ... (ticket SAP-12345).",
  "sources": [
    {
      "ticket_id": "SAP-12345",
      "chunk_index": 0,
      "chunk_text": "Ошибка при создании заказа...",
      "relevance_score": 0.94,
      "source_type": "reranked",
      "functional_area": "MM"
    }
  ],
  "used_llm_model": "gpt-4o-mini",
  "llm_generated": true
}
```

Если LLM недоступна/выключена, вернётся только `sources` и `llm_generated=false`.

## Проверка после развёртывания

1. Проверить health:
   - `curl http://localhost:8000/health`
   - `curl http://localhost:8001/health`
2. Загрузить тестовый тикет через `POST /index`.
3. Выполнить `POST /search` и убедиться, что:
   - при `ENABLE_LLM=true` и рабочем LM Studio приходит `answer`,
   - при `ENABLE_LLM=false` приходит только список `sources`.

## Конфигурация

Ключевые переменные:
- `VECTOR_TOP_K`, `RERANK_TOP_K`, `FUZZY_TOP_K`, `FUZZY_THRESHOLD`, `FINAL_CONTEXT_SIZE`
- `ENABLE_RERANKING`, `ENABLE_FUZZY_SEARCH`, `ENABLE_LLM`
- `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`
- `SOURCE_SCHEMA`, `SOURCE_TABLE`, `SOURCE_*_COLUMN` (внешний источник тикетов в Postgres)

## Производительность

Основные задержки:
- Vector search: обычно миллисекунды-десятки миллисекунд (зависит от индекса и объёма).
- Reranking: линейно зависит от `VECTOR_TOP_K`.
- LLM: основной вклад в latency (сеть + генерация).
