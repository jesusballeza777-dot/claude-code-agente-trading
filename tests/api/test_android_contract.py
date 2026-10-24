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

LIMITES: dict[str, type] = {
    "origen": str,
    "editable": bool,
    "aviso": str,
    "vigentes[].nombre": str,
    "vigentes[].valor": str,
    "vigentes[].techo_plan": str,
    "vigentes[].unidad": str,
    "vigentes[].adr": str,
    "grupos_correlacionados": list,
}
VETOS: dict[str, type] = {
    "origen": str,
    "nota": str,
    "vetos[].codigo": str,
    "vetos[].titulo": str,
    "vetos[].explicacion": str,
    "vetos[].veces": int,
}
CALCULADORA_APROBADA: dict[str, type] = {
    "origen": str,
    "motor": str,
    "aprobada": bool,
    "cantidad": str,
    "nocional": str,
    "riesgo_usd": str,
    "presupuesto_usd": str,
    "apalancamiento_efectivo": str,
    "precio_liquidacion": str,
    "costes.comision": str,
    "costes.slippage": str,
    "vetos": list,
}
CALCULADORA_VETADA: dict[str, type] = {
    "aprobada": bool,
    "presupuesto_usd": str,
    "costes.comision": str,
    "vetos[].code": str,
    "vetos[].title": str,
    "vetos[].message": str,
}
DECISIONES: dict[str, type] = {
    "origen": str,
    "vacio": str,
    "decisiones[].t": str,
    "decisiones[].accion": str,
    "decisiones[].nivel": str,
    "decisiones[].motivo": str,
    "decisiones[].evidencia": list,
    "decisiones[].json": dict,
    "libros[].libro": str,
    "libros[].operaciones": int,
}
DIARIO: dict[str, type] = {
    "origen": str,
    "aviso": str,
    "vacio": str,
    "operaciones[].id": str,
    "operaciones[].hipotesis": str,
    "operaciones[].simbolo": str,
    "operaciones[].lado": str,
    "operaciones[].entrada": str,
    "operaciones[].precio_entrada": str,
    "operaciones[].precio_salida": str,
    "operaciones[].motivo_salida": str,
    "operaciones[].pnl": str,
    "operaciones[].r": float,
    "operaciones[].regimen": str,
    "notas[].id": str,
    "notas[].fecha_utc": str,
    "notas[].referencia": str,
    "notas[].texto": str,
}
PROYECTO: dict[str, type] = {
    "origen": str,
    "fases[].id": str,
    "fases[].nombre": str,
    "fases[].estado": str,
    "adr[].id": str,
    "adr[].titulo": str,
    "adr[].estado": str,
    "riesgos[].id": str,
    "riesgos[].riesgo": str,
    "riesgos[].probabilidad": str,
    "riesgos[].impacto": str,
    "pendientes_propietario[].tarea": str,
    "pendientes_propietario[].documento": str,
    "costes.conceptos[].concepto": str,
    "costes.conceptos[].usd_mes": str,
    "costes.conceptos[].estado": str,
    "costes.tipo_de_cambio.mxn_por_usd": str,
    "costes.tipo_de_cambio.estado": str,
    "costes.uso_api_claude.origen": str,
    "costes.uso_api_claude.nota": str,
}
REPORTES: dict[str, type] = {
    "origen": str,
    "reportes[].tipo": str,
    "reportes[].formato": str,
    "reportes[].nombre": str,
    "historial[].fecha_utc": str,
    "historial[].tipo": str,
    "historial[].formato": str,
    "historial[].archivo": str,
    "historial[].demo": bool,
}

CALC_QUERY = {
    "simbolo": "BTCUSDT",
    "mercado": "PERPETUAL",
    "lado": "LONG",
    "entrada": "60000",
    "apalancamiento": "3",
    "capital": "1500",
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


def test_the_remaining_pages_match_what_the_android_app_reads(client: TestClient) -> None:
    client.post(
        "/api/diario/notas",
        json={"referencia": "H2-v1", "texto": "nota"},
        headers={"X-Brujula": "1"},
    )
    client.get("/api/reportes/contador/csv")
    assert _check(client.get("/api/riesgo/limites").json(), LIMITES) == []
    assert _check(client.get("/api/riesgo/vetos").json(), VETOS) == []
    assert _check(client.get("/api/decisiones").json(), DECISIONES) == []
    assert _check(client.get("/api/diario").json(), DIARIO) == []
    assert _check(client.get("/api/proyecto").json(), PROYECTO) == []
    assert _check(client.get("/api/reportes").json(), REPORTES) == []


def test_the_calculator_matches_what_the_android_app_reads(client: TestClient) -> None:
    approved = client.get("/api/riesgo/calculadora", params={**CALC_QUERY, "stop": "58800"}).json()
    vetoed = client.get("/api/riesgo/calculadora", params={**CALC_QUERY, "stop": "61000"}).json()
    assert _check(approved, CALCULADORA_APROBADA) == []
    assert _check(vetoed, CALCULADORA_VETADA) == []
    assert approved["aprobada"] is True
    assert vetoed["aprobada"] is False
    assert vetoed["vetos"][0]["code"] == "INVALID_STOP"


def test_the_apps_sample_responses_still_satisfy_the_contract() -> None:
    samples = {
        "hoy": HOY,
        "en-vivo": EN_VIVO,
        "limites": LIMITES,
        "vetos": VETOS,
        "decisiones": DECISIONES,
        "diario": DIARIO,
        "proyecto": PROYECTO,
        "reportes": REPORTES,
        "calculadora-aprobada": CALCULADORA_APROBADA,
        "calculadora-vetada": CALCULADORA_VETADA,
    }
    for name, contract in samples.items():
        payload = json.loads((RESOURCES / f"{name}.json").read_text("utf-8"))
        assert _check(payload, contract) == [], name


def test_the_contract_detects_a_renamed_field(client: TestClient) -> None:
    payload = client.get("/api/en-vivo").json()
    payload["motores"][0]["nombre_corto"] = payload["motores"][0].pop("nombre")
    assert _check(payload, EN_VIVO) == ["falta motores[].nombre"]
