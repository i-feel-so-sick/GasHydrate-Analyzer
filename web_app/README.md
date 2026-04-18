# Web App

`web_app` содержит web-интерфейс проекта:

- `backend` — `FastAPI`
- `frontend` — `React + Vite`

## Установка

Из корня репозитория:

```bash
uv sync --group web
```

Для frontend:

```bash
cd web_app/frontend
npm install
```

## Переменные окружения

Backend читает переменные из `web_app/backend/.env` и из окружения процесса.
Переменные shell имеют приоритет над файлом.

```bash
cp web_app/backend/.env.example web_app/backend/.env
```

Поддерживаются:

- `HOST`
- `PORT`
- `RELOAD`

Frontend (`Vite`) читает переменные из каталога `web_app/frontend`:

```bash
cp web_app/frontend/.env.example web_app/frontend/.env
```

Поддерживаются:

- `VITE_DEV_HOST`
- `VITE_DEV_PORT`
- `VITE_BACKEND_URL`
- `VITE_API_BASE`

## Быстрый запуск

Backend:

```bash
cp web_app/backend/.env.example web_app/backend/.env
cd /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer
python web_app/backend/run.py
```

Backend на другом порту:

```bash
cd /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer
PORT=8001 python web_app/backend/run.py
```

Frontend:

```bash
cd /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/frontend
npm run dev
```

Frontend с указанием backend:

```bash
cd /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/frontend
VITE_BACKEND_URL=http://localhost:8001 npm run dev
```
