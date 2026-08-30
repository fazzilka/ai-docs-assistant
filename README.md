# AI Docs Assistant

FastAPI-сервис для семантического поиска и генерации документации REST API.
Документы индексируются в Qdrant с помощью локальной embedding-модели Ollama,
а CrewAI использует локальную LLM для генерации новых Markdown-файлов.

## Запуск через Docker

Требования: Docker Desktop с поддержкой Docker Compose.

```bash
docker compose up --build -d
```

При первом запуске Compose скачает контейнеры и модели `bge-m3` и
`qwen2.5:7b`. Модели и данные Qdrant сохраняются в Docker volumes, поэтому
повторные запуски не требуют повторной загрузки.

После запуска доступны:

- API: <http://localhost:8000>
- Swagger UI: <http://localhost:8000/docs>
- health check: <http://localhost:8000/health>
- Qdrant: <http://localhost:6333/dashboard>
- Ollama: <http://localhost:11434>

Проверить состояние контейнеров:

```bash
docker compose ps
docker compose logs -f app
```

Остановить проект:

```bash
docker compose down
```

Удалить контейнеры вместе с локальными Docker volumes:

```bash
docker compose down -v
```

## Настройка

Значения по умолчанию перечислены в `.env.example`. Для локальных
переопределений скопируйте файл в `.env`; `.env` исключён из Git и Docker
build context.

Основные переменные Compose:

- `APP_PORT` — внешний порт API, по умолчанию `8000`;
- `QDRANT_HTTP_PORT` и `QDRANT_GRPC_PORT` — внешние порты Qdrant;
- `OLLAMA_PORT` — внешний порт Ollama;
- `QDRANT_COLLECTION_NAME`, `EMBEDDING_MODEL_NAME`, `VECTOR_SIZE`,
  `OLLAMA_MODEL` — настройки приложения.

