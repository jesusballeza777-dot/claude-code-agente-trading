"""Inicio del día y de la semana en UTC para los límites de pérdida (auditoría A-09).

El límite diario se mide desde las 00:00 UTC y el semanal desde el lunes a las 00:00 UTC
(ADR-007). El capital al inicio de cada periodo (`AccountState.day_start_equity` y
`week_start_equity`) es el capital a mercado en estos instantes; calcularlos aquí evita que
cada llamador use su propia zona horaria o su propio primer día de la semana.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from trading.risk.models import require_aware


def day_start(moment: datetime) -> datetime:
    """00:00 UTC del día de `moment` (convertido antes a UTC)."""
    utc = require_aware("moment", moment).astimezone(UTC)
    return utc.replace(hour=0, minute=0, second=0, microsecond=0)


def week_start(moment: datetime) -> datetime:
    """Lunes a las 00:00 UTC de la semana de `moment` (convertido antes a UTC)."""
    start = day_start(moment)
    return start - timedelta(days=start.weekday())
