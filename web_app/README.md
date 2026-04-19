# Web App

`web_app` содержит web-интерфейс проекта:

- `backend` — `FastAPI`
- `frontend` — `React + Vite`

## Требования

- Python `3.10+`
- `uv`
- Node.js `18+`
- `npm`
- Docker Desktop или Docker Engine + Docker Compose plugin для запуска через контейнеры

## Структура конфигурации

В `web_app` используются три набора `.env`-файлов:

- `web_app/.env` — переменные для `docker compose`
- `web_app/backend/.env` — переменные backend-приложения
- `web_app/frontend/.env` — переменные frontend-приложения

Если используете Docker Compose, держите значения портов синхронными:

- `web_app/.env` → `BACKEND_PORT` должен совпадать с `web_app/backend/.env` → `PORT`
- `web_app/.env` → `FRONTEND_PORT` должен совпадать с `web_app/frontend/.env` → `VITE_DEV_PORT`

## Установка `uv`

Если `uv` ещё не установлен, поставьте его одним из способов ниже.

### macOS

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Альтернатива через Homebrew:

```bash
brew install uv
```

### Linux

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Если `curl` отсутствует:

```bash
wget -qO- https://astral.sh/uv/install.sh | sh
```

### Windows

PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Альтернатива через WinGet:

```powershell
winget install --id=astral-sh.uv -e
```

### Универсальный вариант через Python

Если Python уже установлен, можно поставить `uv` через `pip` или `pipx`:

```bash
pip install uv
```

Или:

```bash
pipx install uv
```

Проверка установки:

```bash
uv --version
```

## Установка Node.js и `npm`

Для frontend нужны Node.js `18+` и `npm`.

Проверка установки:

```bash
node --version
npm --version
```

Если Node.js ещё не установлен, поставьте его одним из способов ниже.

### macOS

Через Homebrew:

```bash
brew install node
```

Или скачайте официальный установщик:

- [Node.js Downloads](https://nodejs.org/en/download)

### Linux

Самый переносимый вариант для Linux:

- [Node.js Downloads](https://nodejs.org/en/download)

Если предпочитаете пакетный менеджер, используйте официальную страницу с командами под конкретный дистрибутив:

- [Node.js via package manager](https://nodejs.org/en/download/package-manager)

### Windows

Через WinGet:

```powershell
winget install OpenJS.NodeJS
```

Или скачайте официальный `.msi`-установщик:

- [Node.js Downloads](https://nodejs.org/en/download)

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

## Запуск через Docker Compose

Для web-приложения подготовлены:

- [web_app/docker-compose.yml](/Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/docker-compose.yml)
- [web_app/backend/Dockerfile](/Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/backend/Dockerfile)
- [web_app/frontend/Dockerfile](/Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/frontend/Dockerfile)

### 1. Подготовка `.env`-файлов

Из корня репозитория:

```bash
cp web_app/.env.example web_app/.env
cp web_app/backend/.env.example web_app/backend/.env
cp web_app/frontend/.env.example web_app/frontend/.env
```

В Windows PowerShell:

```powershell
Copy-Item .\web_app\.env.example .\web_app\.env
Copy-Item .\web_app\backend\.env.example .\web_app\backend\.env
Copy-Item .\web_app\frontend\.env.example .\web_app\frontend\.env
```

### 2. Проверка портов

Перед запуском убедитесь, что значения совпадают:

- `web_app/.env`: `BACKEND_PORT=8000`, `FRONTEND_PORT=5173`
- `web_app/backend/.env`: `PORT=8000`
- `web_app/frontend/.env`: `VITE_DEV_PORT=5173`

Если меняете порты, меняйте их во всех соответствующих файлах.

### 3. Запуск

macOS и Linux:

```bash
cd /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app
docker compose up --build
```

Windows PowerShell:

```powershell
cd C:\path\to\GasHydrate-Analyzer\web_app
docker compose up --build
```

После запуска:

- frontend: `http://localhost:5173`
- backend: `http://localhost:8000`

### 4. Остановка

```bash
docker compose down
```

Удаление контейнеров вместе с томом `node_modules` frontend:

```bash
docker compose down -v
```

## Переменные окружения

### Backend

Backend читает переменные из `web_app/backend/.env` и из окружения процесса. Переменные shell имеют приоритет над файлом.

Создание файла на macOS и Linux:

```bash
cp /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/backend/.env.example /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/backend/.env
```

Создание файла в Windows PowerShell:

```powershell
Copy-Item .\web_app\backend\.env.example .\web_app\backend\.env
```

Поддерживаются:

- `HOST`
- `PORT`
- `RELOAD`

### Frontend

Frontend (`Vite`) читает переменные из каталога `web_app/frontend`.

Создание файла на macOS и Linux:

```bash
cp /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/frontend/.env.example /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/frontend/.env
```

Создание файла в Windows PowerShell:

```powershell
Copy-Item .\web_app\frontend\.env.example .\web_app\frontend\.env
```

Поддерживаются:

- `VITE_DEV_HOST`
- `VITE_DEV_PORT`
- `VITE_BACKEND_URL`
- `VITE_API_BASE`

### Docker Compose

Docker Compose читает переменные из `web_app/.env`.

Поддерживаются:

- `COMPOSE_PROJECT_NAME`
- `BACKEND_HOST`
- `BACKEND_PORT`
- `BACKEND_RELOAD`
- `FRONTEND_HOST`
- `FRONTEND_PORT`

## Запуск приложения

### 1. Запуск backend

Если `.env` ещё не создан, на macOS и Linux:

```bash
cp /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/backend/.env.example /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/backend/.env
```

Если `.env` ещё не создан, в Windows PowerShell:

```powershell
Copy-Item .\web_app\backend\.env.example .\web_app\backend\.env
```

Запуск из корня репозитория на macOS и Linux:

```bash
cd /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer
uv run python web_app/backend/run.py
```

Запуск из корня репозитория в Windows PowerShell:

```powershell
cd C:\path\to\GasHydrate-Analyzer
uv run python web_app/backend/run.py
```

По умолчанию backend стартует на `http://0.0.0.0:8000`.

Запуск backend на другом порту на macOS и Linux:

```bash
cd /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer
PORT=8001 uv run python web_app/backend/run.py
```

Запуск backend на другом порту в Windows PowerShell:

```powershell
cd C:\path\to\GasHydrate-Analyzer
$env:PORT=8001
uv run python web_app/backend/run.py
```

### 2. Запуск frontend

Если `.env` ещё не создан, на macOS и Linux:

```bash
cp /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/frontend/.env.example /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/frontend/.env
```

Если `.env` ещё не создан, в Windows PowerShell:

```powershell
Copy-Item .\web_app\frontend\.env.example .\web_app\frontend\.env
```

Запуск dev-сервера на macOS и Linux:

```bash
cd /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/frontend
npm run dev
```

Запуск dev-сервера в Windows PowerShell:

```powershell
cd C:\path\to\GasHydrate-Analyzer\web_app\frontend
npm run dev
```

По умолчанию frontend стартует на `http://localhost:5173` и проксирует `/api` на `http://localhost:8000`.

Запуск frontend с указанием другого backend на macOS и Linux:

```bash
cd /Users/igorzolotyh/teplophysica/GasHydrate-Analyzer/web_app/frontend
VITE_BACKEND_URL=http://localhost:8001 npm run dev
```

Запуск frontend с указанием другого backend в Windows PowerShell:

```powershell
cd C:\path\to\GasHydrate-Analyzer\web_app\frontend
$env:VITE_BACKEND_URL="http://localhost:8001"
npm run dev
```

## Docker-файлы

- backend-контейнер ставит зависимости в два слоя:
- базовые зависимости проекта из корневого `pyproject.toml`, потому что backend использует модули из `src/visualize_app`
- web-зависимости из `web_app/backend/requirements.txt` для `FastAPI` и сопутствующего runtime
- frontend-контейнер ставит зависимости через `npm ci`
- в Docker Compose backend и frontend запускаются в dev-режиме с bind mount
- backend healthcheck проверяет `GET /api/health`
- frontend обращается к backend внутри Docker-сети по адресу `http://backend:<BACKEND_PORT>`

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

В Windows PowerShell тот же сценарий выглядит так:

```powershell
cd C:\path\to\GasHydrate-Analyzer
uv sync --group web
Copy-Item .\web_app\backend\.env.example .\web_app\backend\.env
uv run python web_app/backend/run.py
```

Во втором окне PowerShell:

```powershell
cd C:\path\to\GasHydrate-Analyzer\web_app\frontend
npm install
Copy-Item .env.example .env
npm run dev
```
