"""Genera las credenciales del Centro de Mando en el ordenador del propietario (ADR-015).

Uso: `uv run python -m trading.api.credentials`. Pide la contraseña sin mostrarla, crea el
secreto TOTP y la clave de sesión, y escribe las tres variables en formato YAML para pegarlas
con `sops secrets/centro-de-mando.sops.yaml`. No guarda nada en disco ni en logs: lo que
imprime solo aparece en la terminal de quien lo ejecuta.
"""

from __future__ import annotations

import base64
import getpass
import secrets
import sys
from collections.abc import Callable
from typing import Final, TextIO
from urllib.parse import quote

from trading.api.security import hash_password

MIN_PASSWORD_LENGTH: Final = 12
ISSUER: Final = "Centro de Mando"


def generate(password: str) -> dict[str, str]:
    """Las tres variables que lee `ApiSettings.from_env` cuando la autenticación está activa."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"la contraseña necesita al menos {MIN_PASSWORD_LENGTH} caracteres")
    return {
        "TRADING_API_PASSWORD_HASH": hash_password(password),
        "TRADING_API_TOTP_SECRET": base64.b32encode(secrets.token_bytes(20)).decode(),
        "TRADING_API_SESSION_KEY": secrets.token_urlsafe(48),
    }


def otpauth_uri(totp_secret: str) -> str:
    """URI para dar de alta el TOTP en la app de autenticación (6 dígitos, 30 s)."""
    label = quote(f"{ISSUER}:propietario")
    return (
        f"otpauth://totp/{label}?secret={totp_secret}"
        f"&issuer={quote(ISSUER)}&algorithm=SHA1&digits=6&period=30"
    )


def main(
    ask: Callable[[str], str] = getpass.getpass,
    out: TextIO = sys.stdout,
) -> int:
    password = ask("Contraseña del Centro de Mando: ")
    if ask("Repítela: ") != password:
        print("Las contraseñas no coinciden; no se generó nada.", file=sys.stderr)
        return 1
    try:
        values = generate(password)
    except ValueError as exc:
        print(f"{exc}; no se generó nada.", file=sys.stderr)
        return 1
    print("# Pega estas líneas con `sops secrets/centro-de-mando.sops.yaml`.", file=out)
    for name, value in values.items():
        print(f'{name}: "{value}"', file=out)
    uri = otpauth_uri(values["TRADING_API_TOTP_SECRET"])
    print(f"# Alta del TOTP en tu app de autenticación (luego limpia la terminal): {uri}", file=out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
