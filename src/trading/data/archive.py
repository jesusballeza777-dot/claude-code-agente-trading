"""Archivo público de Binance (`data.binance.vision`), solo lectura y sin claves.

Se lee por su espejo en S3 porque el host directo no es accesible desde el entorno de
desarrollo (ACLARACIONES-v1 §1). Solo se permiten los prefijos de velas mensuales (spot y
perpetuos USDⓈ-M) y de funding: ningún endpoint de cuenta, órdenes, retiro o transferencia.
Cada zip se verifica con su `.CHECKSUM` SHA-256; si no cuadra, se borra y se lanza un error.
"""

from __future__ import annotations

import hashlib
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

ARCHIVE_BASE: Final = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
ALLOWED_PREFIXES: Final = (
    "data/spot/monthly/klines/",
    "data/futures/um/monthly/klines/",
    "data/futures/um/monthly/fundingRate/",
)
_S3_NS: Final = "{http://s3.amazonaws.com/doc/2006-03-01/}"
_MONTH = re.compile(r"-(\d{4})-(\d{2})\.zip$")

Fetch = Callable[[str], bytes]


class ArchiveError(RuntimeError):
    """Respuesta inesperada del archivo o checksum que no cuadra."""


@dataclass(frozen=True, slots=True)
class ArchiveFile:
    key: str
    size: int

    @property
    def month(self) -> tuple[int, int]:
        return month_of(self.key)


def http_fetch(url: str, *, attempts: int = 5, backoff: float = 2.0) -> bytes:
    """GET con reintentos (espera 2, 4, 8, 16 s); respeta HTTPS_PROXY y SSL_CERT_FILE."""
    if not url.startswith(ARCHIVE_BASE):
        raise ArchiveError(f"URL fuera del archivo permitido: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "agente-trading-f3"})  # noqa: S310
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
                body: bytes = response.read()
                return body
        except urllib.error.HTTPError as exc:
            if exc.code < 500 or attempt == attempts:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == attempts:
                raise
        time.sleep(backoff**attempt)
    raise ArchiveError("sin intentos")  # pragma: no cover - el bucle siempre devuelve o lanza


def check_prefix(prefix: str) -> str:
    if not prefix.startswith(ALLOWED_PREFIXES) or ".." in prefix:
        raise ArchiveError(f"prefijo no permitido: {prefix!r}")
    return prefix


def list_prefixes(prefix: str, fetch: Fetch = http_fetch) -> list[str]:
    """Subcarpetas directas de `prefix` (por ejemplo, los símbolos de un mercado)."""
    found: list[str] = []
    for root in _list_pages(check_prefix(prefix), fetch):
        found += [
            node.text
            for node in root.iter(f"{_S3_NS}Prefix")
            if node.text and node.text != prefix and node.text.startswith(prefix)
        ]
    return sorted(set(found))


def list_files(prefix: str, fetch: Fetch = http_fetch) -> list[ArchiveFile]:
    """Ficheros .zip mensuales bajo `prefix` (sin los .CHECKSUM)."""
    files: list[ArchiveFile] = []
    for root in _list_pages(check_prefix(prefix), fetch):
        for item in root.iter(f"{_S3_NS}Contents"):
            key = item.findtext(f"{_S3_NS}Key") or ""
            size = item.findtext(f"{_S3_NS}Size") or "0"
            if key.endswith(".zip") and _MONTH.search(key):
                files.append(ArchiveFile(key=key, size=int(size)))
    return sorted(files, key=lambda f: f.key)


def download(file_key: str, raw_root: Path, fetch: Fetch = http_fetch) -> tuple[Path, str]:
    """Descarga un zip y su checksum, verifica SHA-256 y devuelve (ruta, sha256).

    Si el zip ya existe y su checksum cuadra, no se vuelve a descargar.
    """
    check_prefix(file_key)
    target = raw_root / file_key
    checksum_path = target.with_name(target.name + ".CHECKSUM")
    if not checksum_path.exists():
        checksum_path.parent.mkdir(parents=True, exist_ok=True)
        checksum_path.write_bytes(fetch(f"{ARCHIVE_BASE}/{file_key}.CHECKSUM"))
    expected = _parse_checksum(checksum_path.read_text(encoding="utf-8"), target.name)
    if target.exists() and _sha256(target.read_bytes()) == expected:
        return target, expected
    body = fetch(f"{ARCHIVE_BASE}/{file_key}")
    actual = _sha256(body)
    if actual != expected:
        raise ArchiveError(f"checksum de {file_key}: esperado {expected}, obtenido {actual}")
    partial = target.with_name(target.name + ".part")
    partial.write_bytes(body)
    partial.replace(target)
    return target, expected


def month_of(key: str) -> tuple[int, int]:
    match = _MONTH.search(key)
    if match is None:
        raise ArchiveError(f"no es un fichero mensual: {key}")
    return int(match.group(1)), int(match.group(2))


def _list_pages(prefix: str, fetch: Fetch) -> list[ET.Element]:
    pages: list[ET.Element] = []
    marker = ""
    while True:
        query = urllib.parse.urlencode({"delimiter": "/", "prefix": prefix, "marker": marker})
        root = ET.fromstring(fetch(f"{ARCHIVE_BASE}?{query}"))  # noqa: S314
        pages.append(root)
        if root.findtext(f"{_S3_NS}IsTruncated") != "true":
            return pages
        keys = [n.text for n in root.iter(f"{_S3_NS}Key") if n.text]
        prefixes = [n.text for n in root.iter(f"{_S3_NS}Prefix") if n.text and n.text != prefix]
        last = max(keys + prefixes, default="")
        if not last or last <= marker:
            raise ArchiveError("paginación de S3 sin avance")
        marker = last


def _parse_checksum(text: str, filename: str) -> str:
    parts = text.split()
    if len(parts) != 2 or parts[1] != filename or not re.fullmatch(r"[0-9a-f]{64}", parts[0]):
        raise ArchiveError(f"CHECKSUM con formato inesperado para {filename}")
    return parts[0]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
