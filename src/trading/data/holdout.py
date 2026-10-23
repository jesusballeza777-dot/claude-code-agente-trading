"""Guardia del holdout en código (CLAUDE.md regla 7; auditoría A-01).

El holdout empieza el 2025-01-01 00:00 UTC y está sellado. Toda función que lea datos para
investigación o ejecute un backtest llama a `ensure_research_window` (o filtra con
`research_cutoff`) y se niega a usar instantes ≥ 2025-01-01 salvo que exista una autorización:

- `research/holdout_unlock.toml` con fecha, hipótesis autorizadas, commit del pre-registro,
  quién aprueba y motivo;
- el fichero está versionado, sin cambios locales, y el último commit que lo tocó tiene una
  firma válida de una clave listada en `ops/allowed_signers` (la clave pública del
  propietario; ese fichero lo añade el propietario, nunca Claude).

Sin todo eso, el holdout sigue sellado. La apertura es de un solo uso por hipótesis: el
backtester comprueba además en `research/trials.csv` que no exista ya una corrida `holdout`
de esa hipótesis.
"""

from __future__ import annotations

import re
import subprocess  # nosec B404 - solo git local, con argumentos fijos
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

HOLDOUT_START: Final = datetime(2025, 1, 1, tzinfo=UTC)
REPO_ROOT: Final = Path(__file__).resolve().parents[3]
UNLOCK_PATH: Final = REPO_ROOT / "research" / "holdout_unlock.toml"
ALLOWED_SIGNERS_PATH: Final = REPO_ROOT / "ops" / "allowed_signers"

_COMMIT = re.compile(r"[0-9a-f]{40}")


class HoldoutSealedError(PermissionError):
    """Se intentó usar datos del holdout sin autorización firmada."""


@dataclass(frozen=True, slots=True)
class HoldoutUnlock:
    fecha_utc: datetime
    hipotesis: frozenset[str]
    prereg_commit: str
    aprobado_por: str
    motivo: str


SignatureCheck = Callable[[Path], bool]


def ensure_research_window(
    start: datetime,
    end: datetime,
    *,
    hypothesis: str | None = None,
    unlock_path: Path = UNLOCK_PATH,
    signature_ok: SignatureCheck | None = None,
) -> None:
    """Falla si `[start, end)` toca el holdout y no hay autorización para `hypothesis`."""
    _require_utc("start", start)
    _require_utc("end", end)
    if end < start:
        raise ValueError("end no puede ser anterior a start")
    if end <= HOLDOUT_START:
        return
    unlock = load_unlock(unlock_path, signature_ok=signature_ok)
    if unlock is None:
        raise HoldoutSealedError(
            f"el rango {start.isoformat()} → {end.isoformat()} toca el holdout "
            f"(≥ {HOLDOUT_START.date()}) y no hay autorización firmada (CLAUDE.md regla 7)"
        )
    if hypothesis is None or hypothesis not in unlock.hipotesis:
        raise HoldoutSealedError(
            f"la autorización del holdout no incluye la hipótesis {hypothesis!r}"
        )


def research_cutoff(
    *,
    hypothesis: str | None = None,
    unlock_path: Path = UNLOCK_PATH,
    signature_ok: SignatureCheck | None = None,
) -> datetime | None:
    """Instante a partir del cual los datos no se pueden leer, o None si está autorizado."""
    try:
        ensure_research_window(
            HOLDOUT_START,
            datetime.max.replace(tzinfo=UTC),
            hypothesis=hypothesis,
            unlock_path=unlock_path,
            signature_ok=signature_ok,
        )
    except HoldoutSealedError:
        return HOLDOUT_START
    return None


def load_unlock(
    path: Path = UNLOCK_PATH, *, signature_ok: SignatureCheck | None = None
) -> HoldoutUnlock | None:
    """Autorización válida y firmada, o None. Un fichero presente pero inválido es un error."""
    if not path.exists():
        return None
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise HoldoutSealedError(f"{path.name} no es TOML válido: {exc}") from exc
    expected = {"fecha_utc", "hipotesis", "prereg_commit", "aprobado_por", "motivo"}
    if set(raw) != expected:
        raise HoldoutSealedError(
            f"{path.name} debe tener exactamente las claves {sorted(expected)}"
        )
    fecha = raw["fecha_utc"]
    if not isinstance(fecha, datetime) or fecha.utcoffset() is None:
        raise HoldoutSealedError("fecha_utc debe ser una fecha y hora con zona (UTC)")
    hipotesis = raw["hipotesis"]
    if (
        not isinstance(hipotesis, list)
        or not hipotesis
        or not all(isinstance(h, str) and h for h in hipotesis)
    ):
        raise HoldoutSealedError("hipotesis debe ser una lista de textos no vacía")
    commit = raw["prereg_commit"]
    if not isinstance(commit, str) or not _COMMIT.fullmatch(commit):
        raise HoldoutSealedError("prereg_commit debe ser un hash de commit completo (40 hex)")
    for key in ("aprobado_por", "motivo"):
        if not isinstance(raw[key], str) or not raw[key].strip():
            raise HoldoutSealedError(f"{key} no puede estar vacío")
    check = signature_ok if signature_ok is not None else git_signature_ok
    if not check(path):
        raise HoldoutSealedError(
            f"{path.name} no está en un commit firmado por una clave de ops/allowed_signers"
        )
    return HoldoutUnlock(
        fecha_utc=fecha.astimezone(UTC),
        hipotesis=frozenset(hipotesis),
        prereg_commit=commit,
        aprobado_por=raw["aprobado_por"],
        motivo=raw["motivo"],
    )


def git_signature_ok(path: Path, allowed_signers: Path = ALLOWED_SIGNERS_PATH) -> bool:
    """True si `path` está versionado sin cambios y su último commit tiene firma válida."""
    if not allowed_signers.exists():
        return False
    repo = path.resolve().parent
    relative = path.resolve()
    clean = subprocess.run(  # noqa: S603 - argumentos fijos, sin shell
        ["git", "-C", str(repo), "diff", "--quiet", "HEAD", "--", str(relative)],  # noqa: S607
        check=False,
        capture_output=True,
    )
    if clean.returncode != 0:
        return False
    result = subprocess.run(  # noqa: S603
        [  # noqa: S607
            "git",
            "-C",
            str(repo),
            "-c",
            f"gpg.ssh.allowedSignersFile={allowed_signers}",
            "log",
            "-1",
            "--format=%G?",
            "--",
            str(relative),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "G"


def _require_utc(name: str, value: datetime) -> None:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{name} debe llevar zona horaria")
