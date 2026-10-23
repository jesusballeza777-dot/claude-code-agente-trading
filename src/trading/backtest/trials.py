"""Registro obligatorio de pruebas en `research/trials.csv` (CLAUDE.md regla 6; auditoría A-02).

- Solo se añaden filas: nunca se reescribe ni se borra una existente. Antes de añadir se
  comprueba que la cabecera y las filas previas siguen intactas (huella del contenido).
- `record_run` es la única forma de obtener el resultado de un backtest desde el ejecutor de
  la F4: primero escribe la fila y después devuelve. Si la escritura falla, la corrida falla.
- La apertura del holdout es de un solo uso por hipótesis: una segunda fila `holdout` de la
  misma hipótesis se rechaza.
- `verify_frozen_preregistration` comprueba que las reglas no cambiaron desde el commit de
  fusión del pre-registro (solo se admiten las líneas de estado) y devuelve el hash de las
  aclaraciones vigentes, que se anota en cada fila.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import subprocess  # nosec B404 - solo git local, con argumentos fijos
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from trading.data.holdout import REPO_ROOT

TRIALS_PATH: Final = REPO_ROOT / "research" / "trials.csv"
PREREG_DIR: Final = REPO_ROOT / "research" / "preregistration"
PREREG_COMMIT: Final = "4614d659247e57ef6f01614b4986c125fe5468f9"
RULE_FILES: Final = (
    "00-protocolo-comun.md",
    "H1-momentum-series-temporales-diario.md",
    "H2-ruptura-canal-4h.md",
    "H4-filtro-funding-oi.md",
)
CLARIFICATIONS: Final = "ACLARACIONES-v1.md"
_STATUS_PREFIXES: Final = ("- **Estado:**", "- **Commit de fusión:**", "- **Versión:**")
HEADER: Final = (
    "trial_id",
    "fecha_utc",
    "hipotesis_id",
    "prereg_commit",
    "variante",
    "parametros_json",
    "dataset_id",
    "periodo_inicio",
    "periodo_fin",
    "tipo_muestra",
    "n_operaciones",
    "resultado_ref",
    "autor",
    "notas",
)
SAMPLE_TYPES: Final = frozenset({"principal", "robustez", "costes_x1.5", "sensibilidad", "holdout"})


class TrialRegistryError(RuntimeError):
    """El registro no se puede usar: la corrida no debe continuar."""


@dataclass(frozen=True, slots=True)
class TrialRow:
    trial_id: str
    fecha_utc: str
    hipotesis_id: str
    prereg_commit: str
    variante: str
    parametros_json: str
    dataset_id: str
    periodo_inicio: str
    periodo_fin: str
    tipo_muestra: str
    n_operaciones: int
    resultado_ref: str
    autor: str
    notas: str


class TrialRegistry:
    def __init__(self, path: Path = TRIALS_PATH) -> None:
        self.path = path
        self._fingerprint = self._check()

    def rows(self) -> list[dict[str, str]]:
        with self.path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def next_id(self) -> str:
        return f"T{len(self.rows()) + 1:04d}"

    def principal_rows(self) -> list[dict[str, str]]:
        return [r for r in self.rows() if r["tipo_muestra"] == "principal"]

    def append(self, row: TrialRow) -> None:
        if row.tipo_muestra not in SAMPLE_TYPES:
            raise TrialRegistryError(f"tipo_muestra desconocido: {row.tipo_muestra}")
        if row.tipo_muestra == "holdout" and any(
            r["tipo_muestra"] == "holdout" and r["hipotesis_id"] == row.hipotesis_id
            for r in self.rows()
        ):
            raise TrialRegistryError(f"el holdout de {row.hipotesis_id} ya se usó una vez")
        if self._check() != self._fingerprint:
            raise TrialRegistryError("trials.csv cambió desde fuera del registro")
        buffer = io.StringIO()
        csv.writer(buffer, lineterminator="\n").writerow(
            [str(getattr(row, name)) for name in HEADER]
        )
        with self.path.open("a", encoding="utf-8", newline="") as handle:
            handle.write(buffer.getvalue())
            handle.flush()
            os.fsync(handle.fileno())
        self._fingerprint = self._check()

    def record_run(
        self,
        *,
        hypothesis: str,
        variant: str,
        params: Mapping[str, object],
        dataset_id: str,
        period: tuple[datetime, datetime],
        sample: str,
        trades: int,
        result: Mapping[str, object],
        results_dir: Path,
        prereg: str,
        notes: str = "",
        author: str = "Claude (backtester F4)",
    ) -> TrialRow:
        """Guarda el resultado, añade la fila y la devuelve. Sin fila no hay resultado."""
        trial_id = self.next_id()
        results_dir.mkdir(parents=True, exist_ok=True)
        result_path = results_dir / f"{trial_id}.json"
        payload = {"trial_id": trial_id, **result}
        result_path.write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
        reference = (
            str(result_path.relative_to(REPO_ROOT))
            if result_path.is_relative_to(REPO_ROOT)
            else str(result_path)
        )
        row = TrialRow(
            trial_id=trial_id,
            fecha_utc=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            hipotesis_id=hypothesis,
            prereg_commit=prereg,
            variante=variant,
            parametros_json=json.dumps(params, sort_keys=True, separators=(",", ":")),
            dataset_id=dataset_id,
            periodo_inicio=f"{period[0]:%Y-%m-%d}",
            periodo_fin=f"{period[1]:%Y-%m-%d}",
            tipo_muestra=sample,
            n_operaciones=trades,
            resultado_ref=reference,
            autor=author,
            notas=notes,
        )
        try:
            self.append(row)
        except Exception:
            result_path.unlink(missing_ok=True)
            raise
        return row

    def _check(self) -> str:
        if not self.path.exists():
            raise TrialRegistryError(f"no existe {self.path}")
        text = self.path.read_text(encoding="utf-8")
        first_line = text.split("\n", 1)[0]
        if tuple(first_line.split(",")) != HEADER:
            raise TrialRegistryError("la cabecera de trials.csv no es la esperada")
        if text and not text.endswith("\n"):
            raise TrialRegistryError("trials.csv no termina en salto de línea")
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


def row_dict(row: TrialRow) -> dict[str, object]:
    return asdict(row)


def verify_frozen_preregistration(repo: Path = REPO_ROOT, commit: str = PREREG_COMMIT) -> str:
    """Comprueba que las reglas siguen como en `commit` y devuelve el hash de las aclaraciones."""
    files = [str(PREREG_DIR.relative_to(REPO_ROOT) / name) for name in RULE_FILES]
    clarifications = str(PREREG_DIR.relative_to(REPO_ROOT) / CLARIFICATIONS)
    dirty = _git(repo, "status", "--porcelain", "--", *files, clarifications)
    if dirty.strip():
        raise TrialRegistryError("hay cambios sin commit en el pre-registro o en las aclaraciones")
    diff = _git(repo, "diff", "--unified=0", commit, "HEAD", "--", *files)
    for line in diff.splitlines():
        if line.startswith(("+++", "---", "@@", "diff ", "index ")):
            continue
        if line.startswith(("+", "-")) and not line[1:].startswith(_STATUS_PREFIXES):
            raise TrialRegistryError(f"el pre-registro cambió desde {commit[:7]}: {line[:80]}")
    return _git(repo, "log", "-1", "--format=%H", "--", clarifications).strip()


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603 - argumentos fijos, sin shell
        ["git", "-C", str(repo), *args],  # noqa: S607
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise TrialRegistryError(f"git {' '.join(args[:2])}: {result.stderr.strip()}")
    return result.stdout
