# Web App

`web_app` содержит web-интерфейс проекта:

- `backend` — `FastAPI`
- `frontend` — `React + Vite`

## Требования

- Python `3.10+`
- `uv`
- Node.js `18+`
- `npm`

## Установка зависимостей

### Backend

Из корня репозитория установите Python-зависимости вместе с группой `web`:

```bash
cd /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer
uv sync --group web
```

Это создаст и заполнит `.venv` с зависимостями backend.

### Frontend

Установите frontend-зависимости из каталога `web_app/frontend`:

```bash
cd /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/frontend
npm install
```

## Переменные окружения

### Backend

Backend читает переменные из `web_app/backend/.env` и из окружения процесса. Переменные shell имеют приоритет над файлом.

Создание файла:

```bash
cp /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/backend/.env.example /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/backend/.env
```

Поддерживаются:

- `HOST`
- `PORT`
- `RELOAD`

### Frontend

Frontend (`Vite`) читает переменные из каталога `web_app/frontend`.

Создание файла:

```bash
cp /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/frontend/.env.example /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/frontend/.env
```

Поддерживаются:

- `VITE_DEV_HOST`
- `VITE_DEV_PORT`
- `VITE_BACKEND_URL`
- `VITE_API_BASE`

## Запуск приложения

### 1. Запуск backend

Если `.env` ещё не создан:

```bash
cp /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/backend/.env.example /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/backend/.env
```

Запуск из корня репозитория:

```bash
cd /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer
uv run python web_app/backend/run.py
```

По умолчанию backend стартует на `http://0.0.0.0:8000`.

Запуск backend на другом порту:

```bash
cd /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer
PORT=8001 uv run python web_app/backend/run.py
```

### 2. Запуск frontend

Если `.env` ещё не создан:

```bash
cp /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/frontend/.env.example /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/frontend/.env
```

Запуск dev-сервера:

```bash
cd /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/frontend
npm run dev
```

По умолчанию frontend стартует на `http://localhost:5173` и проксирует `/api` на `http://localhost:8000`.

Запуск frontend с указанием другого backend:

```bash
cd /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/frontend
VITE_BACKEND_URL=http://localhost:8001 npm run dev
```

## Быстрый старт с нуля

Если зависимости ещё не установлены, полный сценарий запуска выглядит так.

В первом терминале:

```bash
cd /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer
uv sync --group web
cp web_app/backend/.env.example web_app/backend/.env
uv run python web_app/backend/run.py
```

Во втором терминале:

```bash
cd /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/frontend
npm install
cp .env.example .env
npm run dev
```
