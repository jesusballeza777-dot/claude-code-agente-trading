"""Seguridad del Centro de Mando (ADR-015).

- Un solo usuario: contraseña con hash scrypt y TOTP (RFC 6238), con los secretos leídos del
  entorno que prepara SOPS en tiempo de ejecución (`sops exec-env`). Nada se escribe en código.
- Sesión: token firmado con HMAC-SHA256 en una cookie HttpOnly, SameSite=Strict.
- Cabeceras: CSP estricta, sin marcos, sin referrer, sin caché en la API.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from dataclasses import dataclass
from typing import Final

SCRYPT_N: Final = 2**15
SCRYPT_R: Final = 8
SCRYPT_P: Final = 1
TOTP_STEP: Final = 30
SESSION_SECONDS: Final = 12 * 3600

SECURITY_HEADERS: Final = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; "
        "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    """`scrypt$N$r$p$sal$hash` en base64. Para generar el hash que va a SOPS."""
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=32,
        maxmem=64 * 1024 * 1024,
    )
    return "$".join(
        [
            "scrypt",
            str(SCRYPT_N),
            str(SCRYPT_R),
            str(SCRYPT_P),
            base64.b64encode(salt).decode(),
            base64.b64encode(digest).decode(),
        ]
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, expected = stored.split("$")
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=base64.b64decode(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=32,
            maxmem=64 * 1024 * 1024,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, base64.b64decode(expected))


def totp(secret_base32: str, moment: float, *, step: int = TOTP_STEP, digits: int = 6) -> str:
    key = base64.b32decode(secret_base32.upper() + "=" * (-len(secret_base32) % 8))
    counter = struct.pack(">Q", int(moment // step))
    mac = hmac.new(key, counter, hashlib.sha1).digest()
    offset = mac[-1] & 0x0F
    code = (struct.unpack(">I", mac[offset : offset + 4])[0] & 0x7FFFFFFF) % 10**digits
    return f"{code:0{digits}d}"


def verify_totp(secret_base32: str, code: str, *, now: float | None = None) -> bool:
    """Acepta el código del paso actual y de los pasos vecinos (±30 s de desfase)."""
    moment = time.time() if now is None else now
    candidates = (totp(secret_base32, moment + delta * TOTP_STEP) for delta in (-1, 0, 1))
    return any(hmac.compare_digest(code, candidate) for candidate in candidates)


@dataclass(frozen=True, slots=True)
class SessionSigner:
    key: bytes

    def issue(self, *, now: float | None = None) -> str:
        expires = int((time.time() if now is None else now) + SESSION_SECONDS)
        payload = f"propietario.{expires}.{secrets.token_hex(8)}"
        return f"{payload}.{self._sign(payload)}"

    def valid(self, token: str | None, *, now: float | None = None) -> bool:
        if not token or token.count(".") != 3:
            return False
        payload, signature = token.rsplit(".", 1)
        if not hmac.compare_digest(signature, self._sign(payload)):
            return False
        try:
            expires = int(payload.split(".")[1])
        except ValueError:
            return False
        return (time.time() if now is None else now) < expires

    def _sign(self, payload: str) -> str:
        return hmac.new(self.key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
