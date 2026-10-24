"""Contrato con la app Android (ADR-018).

La app nativa lee /api/hoy y /api/en-vivo con `Parsers.kt`. Si cambia el nombre o el tipo de
un campo que usa, este test falla aquí en lugar de romper la app en el teléfono.
Las respuestas de ejemplo de la app (app/android/.../test/resources) son salidas de esta API.
"""

import json
from typing import Any

from fastapi.testclient import TestClient

from trading.data.holdout import REPO_ROOT

RESOURCES = REPO_ROOT / "app" / "android" / "app" / "src" / "test" / "resources"

# camino -> tipo esperado; "[]" entra en el primer elemento de la lista.
HOY: dict[str, type] = {
    "estado.origen": str,
    "estado.fase_actual": str,
    "estado.fases[].id": str,
    "estado.fases[].nombre": str,
    "estado.fases[].estado": str,
    "estado.live_trading": bool,
    "estado.holdout.desde": str,
    "estado.holdout.sellado": bool,
    "estado.datos.disponible": bool,
    "estado.motor_de_riesgo.estado": str,
    "estado.motor_de_riesgo.version_limites": str,
    "estado.intentos.principales": int,
    "estado.intentos.total": int,
    "estado.pendientes_propietario[].tarea": str,
    "estado.pendientes_propietario[].documento": str,
    "parte_del_dia.autor": str,
    "parte_del_dia.texto": str,
    "parte_del_dia.validado": bool,
    "cuenta.origen": str,
    "cuenta.capital": str,
    "cuenta.maximo": str,
    "cuenta.drawdown": float,
    "cuenta.umbrales.parada": float,
    "cuenta.umbrales.corte_duro": float,
    "cuenta.presupuesto.diario.usado": float,
    "cuenta.presupuesto.diario.limite": float,
    "cuenta.presupuesto.diario.texto": str,
    "cuenta.presupuesto.semanal.usado": float,
    "cuenta.presupuesto.semanal.limite": float,
    "cuenta.curva[].t": str,
    "cuenta.curva[].capital": float,
    "posiciones.origen": str,
    "posiciones.items": list,
    "posiciones.vacio": str,
    "eventos_macro.origen": str,
    "eventos_macro.items": list,
    "eventos_macro.vacio": str,
}
EN_VIVO: dict[str, type] = {
    "origen": str,
    "hora_utc": str,
    "live_trading": bool,
    "motores[].id": str,
    "motores[].nombre": str,
    "motores[].estado": str,
    "motores[].detalle": str,
    "eventos": list,
    "total_eventos": int,
    "decisiones.origen": str,
    "decisiones.aviso": str,
    "decisiones.items[].t": str,
    "decisiones.items[].accion": str,
    "decisiones.items[].nivel": str,
    "decisiones.items[].motivo": str,
}


def _walk(node: Any, path: str) -> Any:
    for part in path.split("."):
        node = node[part[:-2]][0] if part.endswith("[]") else node[part]
    return node


def _check(payload: dict[str, Any], contract: dict[str, type]) -> list[str]:
    problems = []
    for path, expected in contract.items():
        try:
            value = _walk(payload, path)
        except (KeyError, IndexError, TypeError):
            problems.append(f"falta {path}")
            continue
        # Un entero es un número válido donde la app espera un decimal.
        ok = (
            isinstance(value, (int, float)) and not isinstance(value, bool)
            if expected is float
            else isinstance(value, expected)
        )
        if not ok:
            problems.append(
                f"{path}: se esperaba {expected.__name__} y llegó {type(value).__name__}"
            )
    return problems


def test_hoy_matches_what_the_android_app_reads(client: TestClient) -> None:
    assert _check(client.get("/api/hoy").json(), HOY) == []


def test_en_vivo_matches_what_the_android_app_reads(client: TestClient) -> None:
    assert _check(client.get("/api/en-vivo").json(), EN_VIVO) == []


def test_the_apps_sample_responses_still_satisfy_the_contract() -> None:
    hoy = json.loads((RESOURCES / "hoy.json").read_text("utf-8"))
    vivo = json.loads((RESOURCES / "en-vivo.json").read_text("utf-8"))
    assert _check(hoy, HOY) == []
    assert _check(vivo, EN_VIVO) == []


def test_the_contract_detects_a_renamed_field(client: TestClient) -> None:
    payload = client.get("/api/en-vivo").json()
    payload["motores"][0]["nombre_corto"] = payload["motores"][0].pop("nombre")
    assert _check(payload, EN_VIVO) == ["falta motores[].nombre"]
