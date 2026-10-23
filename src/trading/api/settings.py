"""Configuración del Centro de Mando, leída del entorno en tiempo de ejecución.

Variables (los secretos los inyecta `sops exec-env secrets/api.sops.yaml '...'`):
- `TRADING_API_AUTH`: `on` (por defecto) o `disabled`. Sin autenticación solo se permite
  escuchar en 127.0.0.1 (desarrollo local y tests E2E).
- `TRADING_API_PASSWORD_HASH`, `TRADING_API_TOTP_SECRET`, `TRADING_API_SESSION_KEY`.
- `TRADING_API_HOST` (127.0.0.1) y `TRADING_API_PORT` (8000).
- `TRADING_API_SECURE_COOKIE`: `1` detrás de HTTPS (Tailscale con certificado).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from trading.data.holdout import REPO_ROOT

LOOPBACK: Final = frozenset({"127.0.0.1", "::1", "localhost"})


class InsecureConfigError(RuntimeError):
    """La configuración expondría la app sin protección."""


@dataclass(frozen=True, slots=True)
class ApiSettings:
    auth_enabled: bool = True
    password_hash: str = field(default="", repr=False)
    totp_secret: str = field(default="", repr=False)
    session_key: bytes = field(default=b"", repr=False)
    host: str = "127.0.0.1"
    port: int = 8000
    secure_cookie: bool = False
    repo_root: Path = REPO_ROOT
    data_root: Path = REPO_ROOT / "data"
    app_state: Path = REPO_ROOT / "data" / "app"
    web_dist: Path = REPO_ROOT / "app" / "web" / "dist"

    def __post_init__(self) -> None:
        if self.auth_enabled:
            missing = [
                name
                for name, value in (
                    ("TRADING_API_PASSWORD_HASH", self.password_hash),
                    ("TRADING_API_TOTP_SECRET", self.totp_secret),
                    ("TRADING_API_SESSION_KEY", self.session_key),
                )
                if not value
            ]
            if missing:
                raise InsecureConfigError(
                    f"autenticación activa sin {', '.join(missing)} (se leen de SOPS)"
                )
            if len(self.session_key) < 32:
                raise InsecureConfigError("TRADING_API_SESSION_KEY debe tener al menos 32 bytes")
        elif self.host not in LOOPBACK:
            raise InsecureConfigError("sin autenticación solo se puede escuchar en 127.0.0.1")

    @classmethod
    def from_env(cls) -> ApiSettings:
        env = os.environ
        return cls(
            auth_enabled=env.get("TRADING_API_AUTH", "on") != "disabled",
            password_hash=env.get("TRADING_API_PASSWORD_HASH", ""),
            totp_secret=env.get("TRADING_API_TOTP_SECRET", ""),
            session_key=env.get("TRADING_API_SESSION_KEY", "").encode("utf-8"),
            host=env.get("TRADING_API_HOST", "127.0.0.1"),
            port=int(env.get("TRADING_API_PORT", "8000")),
            secure_cookie=env.get("TRADING_API_SECURE_COOKIE", "0") == "1",
            data_root=Path(env.get("TRADING_DATA_ROOT", str(REPO_ROOT / "data"))),
            app_state=Path(env.get("TRADING_APP_STATE", str(REPO_ROOT / "data" / "app"))),
        )
