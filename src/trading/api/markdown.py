"""Lectura de tablas Markdown de `docs/` (ADR, riesgos, presupuesto, roadmap)."""

from __future__ import annotations

import re
from pathlib import Path

_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_EMPHASIS = re.compile(r"\*\*([^*]+)\*\*|`([^`]+)`")


def plain(cell: str) -> str:
    """Quita enlaces, negritas y código de una celda."""
    text = _LINK.sub(r"\1", cell)
    text = _EMPHASIS.sub(lambda m: m.group(1) or m.group(2), text)
    return text.strip()


def tables(text: str) -> list[list[dict[str, str]]]:
    """Todas las tablas del documento como listas de filas {cabecera: celda}."""
    found: list[list[dict[str, str]]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines) - 1:
        line, separator = lines[i].strip(), lines[i + 1].strip()
        if line.startswith("|") and re.fullmatch(r"\|(\s*:?-+:?\s*\|)+", separator):
            header = _cells(line)
            rows = []
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = _cells(lines[i].strip())
                rows.append(
                    dict(zip(header, cells + [""] * (len(header) - len(cells)), strict=False))
                )
                i += 1
            found.append(rows)
        else:
            i += 1
    return found


def read_tables(path: Path) -> list[list[dict[str, str]]]:
    return tables(path.read_text(encoding="utf-8")) if path.exists() else []


def _cells(line: str) -> list[str]:
    inner = line.strip().strip("|")
    # Las barras escapadas (\|) no separan celdas.
    parts = re.split(r"(?<!\\)\|", inner)
    return [p.replace("\\|", "|").strip() for p in parts]
