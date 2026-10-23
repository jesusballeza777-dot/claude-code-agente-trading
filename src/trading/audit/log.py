"""Registro de auditoría append-only con hash encadenado (auditoría A-18).

Cada entrada guarda el hash de la anterior; su propio hash es
SHA-256(hash_anterior + JSON canónico de la entrada sin el campo `hash`).
Cambiar, borrar o reordenar una entrada rompe la cadena desde ese punto, y
`verify_chain` dice dónde. El fichero es JSON Lines y solo se abre para añadir.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

GENESIS: Final = "0" * 64
CSV_FIELDS: Final = ("indice", "fecha_utc", "tipo", "datos", "hash_anterior", "hash")


@dataclass(frozen=True, slots=True)
class ChainCheck:
    valid: bool
    entries: int
    first_broken: int | None = None
    reason: str = ""


def canonical(entry: Mapping[str, Any]) -> str:
    return json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def entry_hash(previous: str, entry: Mapping[str, Any]) -> str:
    body = {k: v for k, v in entry.items() if k != "hash"}
    return hashlib.sha256((previous + canonical(body)).encode("utf-8")).hexdigest()


def chain(events: Iterable[tuple[str, Mapping[str, Any], datetime]]) -> list[dict[str, Any]]:
    """Construye una cadena nueva a partir de (tipo, datos, fecha)."""
    entries: list[dict[str, Any]] = []
    previous = GENESIS
    for index, (kind, data, moment) in enumerate(events):
        entry: dict[str, Any] = {
            "indice": index,
            "fecha_utc": moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tipo": kind,
            "datos": dict(data),
            "hash_anterior": previous,
        }
        entry["hash"] = entry_hash(previous, entry)
        previous = entry["hash"]
        entries.append(entry)
    return entries


def verify_chain(entries: Sequence[Mapping[str, Any]]) -> ChainCheck:
    previous = GENESIS
    for position, entry in enumerate(entries):
        if entry.get("indice") != position:
            return ChainCheck(False, len(entries), position, "índice fuera de secuencia")
        if entry.get("hash_anterior") != previous:
            return ChainCheck(False, len(entries), position, "hash_anterior no coincide")
        if entry.get("hash") != entry_hash(previous, entry):
            return ChainCheck(False, len(entries), position, "el contenido no coincide con su hash")
        previous = str(entry["hash"])
    return ChainCheck(True, len(entries))


class AuditLog:
    """Fichero JSON Lines append-only con la cadena de hashes."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text("utf-8").splitlines() if line]

    def append(
        self, kind: str, data: Mapping[str, Any], moment: datetime | None = None
    ) -> dict[str, Any]:
        existing = self.entries()
        check = verify_chain(existing)
        if not check.valid:
            raise ValueError(f"cadena rota en la entrada {check.first_broken}: {check.reason}")
        previous = existing[-1]["hash"] if existing else GENESIS
        entry: dict[str, Any] = {
            "indice": len(existing),
            "fecha_utc": (moment or datetime.now(UTC))
            .astimezone(UTC)
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tipo": kind,
            "datos": dict(data),
            "hash_anterior": previous,
        }
        entry["hash"] = entry_hash(previous, entry)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(canonical(entry) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return entry


def to_json(entries: Sequence[Mapping[str, Any]]) -> bytes:
    check = verify_chain(entries)
    payload = {
        "verificacion": {"valida": check.valid, "entradas": check.entries},
        "entradas": list(entries),
    }
    return json.dumps(payload, ensure_ascii=False, indent=1, default=str).encode("utf-8")


def to_csv(entries: Sequence[Mapping[str, Any]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_FIELDS)
    for entry in entries:
        writer.writerow(
            [
                entry["indice"],
                entry["fecha_utc"],
                entry["tipo"],
                canonical(entry["datos"]),
                entry["hash_anterior"],
                entry["hash"],
            ]
        )
    return buffer.getvalue().encode("utf-8")
