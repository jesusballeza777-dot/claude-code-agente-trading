"""Instantánea del Centro de Mando para el modo sin servidor de la app Android (ADR-018).

    uv run python ops/android_snapshot.py app/android/app/src/main/assets/snapshot

Pide a la API real (sobre este repositorio: resultados de la F4, documentos, límites) las páginas
que no necesitan un servidor vivo y las guarda como JSON dentro del APK. Lo que sí lo necesita
(la calculadora del motor de riesgo, los datos de mercado de 200 MB y los reportes) no se incluye:
la app lo dice y pide conectar un servidor. La CI la genera en cada compilación, así que siempre
coincide con el commit del APK.
"""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - solo git local, con argumentos fijos
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from trading.api.app import create_app
from trading.api.settings import ApiSettings
from trading.data.holdout import REPO_ROOT

# Máximo de puntos por serie en el detalle del laboratorio: misma forma, archivo ligero.
MAX_POINTS = 240
MAX_TRADES = 60

PAGES = {
    "hoy": "/api/hoy",
    "en-vivo": "/api/en-vivo",
    "limites": "/api/riesgo/limites",
    "vetos": "/api/riesgo/vetos",
    "decisiones": "/api/decisiones",
    "diario": "/api/diario",
    "proyecto": "/api/proyecto",
    "reportes": "/api/reportes",
    "laboratorio": "/api/laboratorio",
}


def thin(series: list[Any], limit: int = MAX_POINTS) -> list[Any]:
    step = max(1, -(-len(series) // limit))
    return series[::step]


def code_commit() -> str:
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short=12", "HEAD"],  # noqa: S607
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return os.environ.get("GITHUB_SHA", "desconocido")[:12]
    return result.stdout.strip() or "desconocido"


def build(out: Path) -> list[str]:
    out.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    with tempfile.TemporaryDirectory() as state:
        settings = ApiSettings(
            auth_enabled=False,
            repo_root=REPO_ROOT,
            data_root=REPO_ROOT / "data",
            app_state=Path(state),
            web_dist=REPO_ROOT / "app" / "web" / "dist",
        )
        client = TestClient(create_app(settings))

        def save(name: str, payload: Any) -> None:
            (out / f"{name}.json").write_text(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
            )
            written.append(name)

        for name, path in PAGES.items():
            response = client.get(path)
            response.raise_for_status()
            payload = response.json()
            if name == "diario":
                payload["operaciones"] = payload["operaciones"][:MAX_TRADES]
            save(name, payload)

        lab = client.get("/api/laboratorio").json()
        for hypothesis in lab["hipotesis"]:
            if not hypothesis["evaluada"]:
                continue
            response = client.get(f"/api/laboratorio/{hypothesis['id']}")
            response.raise_for_status()
            detail = response.json()
            detail["operaciones"] = []  # están en el Diario; aquí pesarían cientos de KB
            for key in ("curva", "underwater"):
                detail[key] = thin(detail[key])
            save(f"laboratorio-{hypothesis['id'].lower()}", detail)

    save_manifest(out)
    return written


def save_manifest(out: Path) -> None:
    manifest = {
        "generado_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit": code_commit(),
        "nota": "Instantánea del repositorio: sin datos de mercado, calculadora ni reportes.",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("uso: android_snapshot.py CARPETA_DE_SALIDA", file=sys.stderr)
        return 2
    names = build(Path(argv[1]))
    print(f"{len(names)} archivos en {argv[1]}: {', '.join(names)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
