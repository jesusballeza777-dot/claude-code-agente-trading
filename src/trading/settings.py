"""Ajustes globales de seguridad.

LIVE_TRADING está desactivado y es una constante: ningún código, variable de entorno ni
fichero de configuración puede activarlo (CLAUDE.md, regla 2). El mecanismo de activación
por el propietario (CLI local con TOTP y commit firmado) se construye en la F6.
"""

from typing import Final

LIVE_TRADING: Final[bool] = False
