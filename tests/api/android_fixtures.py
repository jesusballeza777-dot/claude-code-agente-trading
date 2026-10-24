"""Genera las respuestas de ejemplo de la app Android a partir de la API real.

    uv run python tests/api/android_fixtures.py

Se guardan en app/android/app/src/test/resources y los tests de JVM de la app las leen.
`tests/api/test_android_contract.py` comprueba que siguen siendo las que da la API.
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api_fixtures import build_repo, client_for
from trading.data.holdout import REPO_ROOT

OUT = REPO_ROOT / "app" / "android" / "app" / "src" / "test" / "resources"
CALC = {
    "simbolo": "BTCUSDT",
    "mercado": "PERPETUAL",
    "lado": "LONG",
    "entrada": "60000",
    "apalancamiento": "3",
    "capital": "1500",
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        client = client_for(build_repo(Path(tmp), with_data=True))
        client.post(
            "/api/diario/notas",
            json={"referencia": "H2-v1", "texto": "Revisé el PBO: sigue en 0.456."},
            headers={"X-Brujula": "1"},
        )
        client.get("/api/reportes/contador/csv")
        paths = {
            "hoy": "/api/hoy",
            "en-vivo": "/api/en-vivo",
            "limites": "/api/riesgo/limites",
            "vetos": "/api/riesgo/vetos",
            "decisiones": "/api/decisiones",
            "diario": "/api/diario",
            "proyecto": "/api/proyecto",
            "reportes": "/api/reportes",
        }
        for name, path in paths.items():
            write(name, client.get(path).json())
        write(
            "calculadora-aprobada",
            client.get("/api/riesgo/calculadora", params={**CALC, "stop": "58800"}).json(),
        )
        write(
            "calculadora-vetada",
            client.get("/api/riesgo/calculadora", params={**CALC, "stop": "61000"}).json(),
        )


def write(name: str, data: object) -> None:
    (OUT / f"{name}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"{name}.json")


if __name__ == "__main__":
    main()
