"""Brújula, el copiloto del Centro de Mando: textos por plantillas deterministas.

Español de México, de tú, cálido y directo. Cada cifra de un texto sale de un dato calculado
por el backend y se formatea aquí; nunca se inventa un número ni una probabilidad
(CLAUDE.md regla 3). `numbers_in` permite al validador comprobar que todas las cifras de un
texto están entre las cifras de origen.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any, Final

NAME: Final = "Brújula"
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def numbers_in(text: str) -> set[str]:
    return {n.replace(",", "") for n in _NUMBER.findall(text)}


def validate(text: str, allowed: Iterable[str]) -> bool:
    """Validador anti-invención: toda cifra del texto debe venir de los datos de origen."""
    return numbers_in(text) <= {a.replace(",", "") for a in allowed}


def pct(value: float, decimals: int = 1) -> str:
    return f"{value * 100:.{decimals}f}%"


def daily_brief(status: Mapping[str, Any], lab: Mapping[str, Any]) -> dict[str, Any]:
    """ "Parte del día": resumen en lenguaje natural a partir del estado y del laboratorio."""
    hypotheses = [h for h in lab.get("hipotesis", []) if h.get("evaluada")]
    passing = [h for h in hypotheses if (h.get("gate") or {}).get("pasa_sin_holdout")]
    completeness = status.get("datos", {}).get("completitud")
    sentences = [
        "Hoy no hay dinero en juego: el sistema está en modo investigación y "
        "LIVE_TRADING sigue apagado.",
    ]
    if completeness is not None:
        sentences.append(
            f"Los datos públicos de 2020-2024 están completos al {pct(completeness, 2)} y el "
            "holdout sigue sellado."
        )
    if hypotheses:
        sentences.append(
            f"En el laboratorio hay {len(hypotheses)} hipótesis evaluadas; "
            f"{len(passing)} pasan los criterios 1-8 del gate sin abrir el holdout."
        )
        if not passing:
            sentences.append(
                "Que ninguna pase no es un fracaso: es el examen funcionando. Mejor saberlo "
                "ahora que con dinero."
            )
    else:
        sentences.append("Todavía no hay backtests registrados.")
    sentences.append(
        "No operar también es una decisión, y mientras no haya evidencia, es la correcta."
    )
    text = " ".join(sentences)
    sources = [str(len(hypotheses)), str(len(passing)), "2020", "2024", "8", "1"]
    if completeness is not None:
        sources.append(f"{completeness * 100:.2f}")
    return {"autor": NAME, "texto": text, "validado": validate(text, sources)}


def gate_hint(trades: int, required: int = 200) -> str:
    if trades >= required:
        return f"Tiene {trades} operaciones: la muestra alcanza el mínimo de {required}."
    missing = required - trades
    return (
        f"Esta estrategia aún no pasa el examen: le faltan {missing} operaciones para tener una "
        "muestra confiable."
    )


def budget_hint(used: float, limit: float) -> str:
    share = used / limit if limit else 0.0
    tail = (
        "Margen de sobra." if share < 0.5 else "Ve con calma." if share < 0.9 else "Casi al límite."
    )
    return f"Vas usando {pct(used)} de tu {pct(limit, 0)} de pérdida diaria. {tail}"


EMPTY_STATES: Final = {
    "posiciones": "No hay posiciones: la simulación en sombra empieza en la F7. Mientras tanto, "
    "prueba la calculadora de riesgo con el motor real.",
    "eventos": "El calendario macro (FOMC, CPI, NFP) llega con la F6. Las reglas del ADR-013 ya "
    "bloquean entradas 2 h antes y después.",
    "decisiones": "El analista Claude empieza en la F5. Lo que ves aquí son datos de "
    "demostración para que conozcas la pantalla.",
    "diario": "Aún no hay operaciones en sombra ni reales. Puedes revisar las del backtest y "
    "dejar notas.",
    "reportes": "Todavía no has generado reportes. Empieza por la ficha de una estrategia.",
}

GLOSSARY: Final = {
    "R": "Unidad de riesgo: lo que pierdes si salta el stop. Ganar 2 R es ganar el doble de lo "
    "que arriesgaste.",
    "Esperanza": "Lo que gana o pierde en promedio cada operación, en R y ya con costes.",
    "Drawdown": "Cuánto ha caído el capital desde su máximo. Mide el peor momento, no el final.",
    "Profit factor": "Suma de lo ganado entre suma de lo perdido. Por encima de 1, gana más de "
    "lo que pierde.",
    "Funding": "Pago periódico entre largos y cortos en los perpetuos. Puede sumar o restar.",
    "Liquidación": "Precio al que el exchange cierra la posición por falta de margen. El motor "
    "exige que quede al menos 3 veces más lejos que el stop.",
    "DSR": "Sharpe deflactado: corrige el resultado por todas las pruebas hechas. Si se prueban "
    "muchas variantes, exige más.",
    "PBO": "Probabilidad de sobreajuste: qué tan seguido la mejor variante en un tramo queda por "
    "debajo de la mediana en el resto.",
    "Holdout": "Datos de 2025 en adelante que nadie ha mirado. Se abren una sola vez, en el examen "
    "final.",
    "IC90%": "Rango donde está el valor real con un 90% de confianza según el remuestreo.",
    "Pre-registro": "Las reglas escritas y congeladas antes de ver resultados. Evita acomodar la "
    "estrategia a los datos.",
    "Veto": "El motor de riesgo bloquea una operación que rompe un límite. Su decisión es "
    "absoluta.",
    "Apalancamiento efectivo": "Tamaño total de las posiciones entre el capital. El límite es 2x.",
    "Régimen": "Etiqueta del mercado según BTC y su media de 200 días: alcista, bajista o lateral.",
}
