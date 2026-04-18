from __future__ import annotations

import os
from pathlib import Path

import uvicorn

BACKEND_DIR = Path(__file__).resolve().parent


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def main() -> None:
    load_env_file(BACKEND_DIR / ".env")

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "true").lower() in {"1", "true", "yes", "on"}

    uvicorn.run(
        "app_entry:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
