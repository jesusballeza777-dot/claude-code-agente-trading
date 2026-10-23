"""Arranque local: `uv run python -m trading.api` (escucha solo en 127.0.0.1 por defecto)."""

from __future__ import annotations

import uvicorn

from trading.api.app import create_app
from trading.api.settings import ApiSettings


def main() -> None:
    settings = ApiSettings.from_env()
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port, log_level="info")


if __name__ == "__main__":
    main()
