"""Explicación de los vetos en español claro (auditoría A-11).

Cada veto se convierte en un código estable (el valor de `VetoReason`, que no cambia aunque
cambie el texto), un título corto y un mensaje con las cifras del veto. Los textos salen de
plantillas fijas: no hay modelo de lenguaje en medio (CLAUDE.md, regla 3).

Redondeo de las cifras mostradas: cuando la cifra observada supera el límite se redondea hacia
arriba y el límite hacia abajo (y al revés cuando la cifra queda por debajo), para que el
mensaje nunca muestre dos cifras iguales donde el motor vio una diferencia.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from enum import Enum, auto

from trading.risk.engine import RiskDecision, Veto, VetoReason
from trading.risk.models import in_risk_context


class Unit(Enum):
    USD = auto()
    PERCENT = auto()  # fracción: 0.15 -> 15.00%
    MULTIPLE = auto()  # 2.35 -> 2.35x
    DURATION = auto()  # segundos -> "4 h 5 min"
    COUNT = auto()
    BPS = auto()  # puntos básicos -> "7.5 pb"


class Direction(Enum):
    TOO_HIGH = auto()  # la cifra observada supera el límite
    TOO_LOW = auto()  # la cifra observada queda por debajo del límite


@dataclass(frozen=True, slots=True)
class Template:
    title: str
    message: str  # admite {obs}, {lim} y {subject}
    fallback: str  # sin cifras ni sujeto: se usa si falta alguno de los que pide `message`
    unit: Unit = Unit.USD
    direction: Direction = Direction.TOO_HIGH


@dataclass(frozen=True, slots=True)
class VetoExplanation:
    code: str
    title: str
    message: str


_HIGH, _LOW = Direction.TOO_HIGH, Direction.TOO_LOW

TEMPLATES: dict[VetoReason, Template] = {
    VetoReason.TRADING_HALTED: Template(
        "Sistema detenido",
        "El sistema está detenido (parada manual o automática): no se abren posiciones hasta "
        "que el propietario lo reactive.",
        "El sistema está detenido: no se abren posiciones.",
    ),
    VetoReason.NON_POSITIVE_EQUITY: Template(
        "Capital agotado",
        "El capital de la cuenta es USD {obs}: no se abren posiciones y se cierran las abiertas.",
        "El capital de la cuenta no es positivo: no se abren posiciones y se cierran las abiertas.",
        direction=_LOW,
    ),
    VetoReason.DRAWDOWN_HALT: Template(
        "Parada por drawdown",
        "La cuenta está {obs} por debajo de su máximo y la parada salta en {lim}: no se abren "
        "posiciones nuevas.",
        "La cuenta alcanzó la parada por drawdown: no se abren posiciones nuevas.",
        Unit.PERCENT,
    ),
    VetoReason.DRAWDOWN_HARD_STOP: Template(
        "Corte duro por drawdown",
        "La cuenta está {obs} por debajo de su máximo y el corte duro es {lim}: se cierran "
        "todas las posiciones y no se abren nuevas.",
        "La cuenta alcanzó el corte duro por drawdown: se cierran todas las posiciones.",
        Unit.PERCENT,
    ),
    VetoReason.MARKET_DATA_MISMATCH: Template(
        "Datos de otro activo",
        "Los datos de mercado no corresponden a {subject}: el motor no evalúa con datos ajenos.",
        "Los datos de mercado no corresponden al activo de la propuesta.",
    ),
    VetoReason.FUTURE_TIMESTAMP: Template(
        "Hora de datos imposible",
        "Los datos llegan fechados {obs} en el futuro y la tolerancia es {lim}: pueden estar "
        "mal y el motor no los usa.",
        "Los datos llegan fechados en el futuro: pueden estar mal y el motor no los usa.",
        Unit.DURATION,
    ),
    VetoReason.STALE_PRICE: Template(
        "Precio atrasado",
        "El dato de {subject} tiene {obs} de antigüedad y el máximo es {lim}: con un precio "
        "viejo no se puede medir el riesgo.",
        "El precio está atrasado: con un precio viejo no se puede medir el riesgo.",
        Unit.DURATION,
    ),
    VetoReason.STALE_BARS: Template(
        "Velas atrasadas",
        "La última vela cerrada es de hace {obs} y lo máximo esperado es {lim}: faltan datos "
        "recientes.",
        "Faltan velas recientes: la señal no se apoya en datos al día.",
        Unit.DURATION,
    ),
    VetoReason.NON_POSITIVE_QUANTITY: Template(
        "Cantidad inválida",
        "La cantidad propuesta no es positiva.",
        "La cantidad propuesta no es positiva.",
    ),
    VetoReason.INVALID_STOP: Template(
        "Stop mal colocado",
        "El stop está del lado equivocado del precio de entrada: no protegería la operación.",
        "El stop está del lado equivocado del precio de entrada.",
    ),
    VetoReason.SHORT_ON_SPOT: Template(
        "Corto en spot",
        "En spot no se puede abrir en corto (ADR-001).",
        "En spot no se puede abrir en corto (ADR-001).",
    ),
    VetoReason.SHORT_NOT_VALIDATED: Template(
        "Cortos no validados",
        "La estrategia {subject} todavía no tiene los cortos validados: solo puede abrir largos.",
        "La estrategia todavía no tiene los cortos validados: solo puede abrir largos.",
    ),
    VetoReason.CROSS_MARGIN: Template(
        "Margen cruzado",
        "El margen cruzado está prohibido: cada posición usa margen aislado.",
        "El margen cruzado está prohibido: cada posición usa margen aislado.",
    ),
    VetoReason.RISK_PER_TRADE: Template(
        "Riesgo por operación",
        "Esta operación arriesgaría USD {obs} y tu límite por operación es USD {lim}.",
        "Esta operación arriesgaría más que tu límite por operación.",
    ),
    VetoReason.EFFECTIVE_LEVERAGE: Template(
        "Apalancamiento",
        "Con esta operación el apalancamiento efectivo sería {obs} y el máximo es {lim}.",
        "Con esta operación el apalancamiento efectivo superaría el máximo.",
        Unit.MULTIPLE,
    ),
    VetoReason.LIQUIDATION_TOO_CLOSE: Template(
        "Liquidación demasiado cerca",
        "La liquidación quedaría a {obs} la distancia al stop y el mínimo es {lim}: un "
        "movimiento brusco podría liquidar la posición antes de que salte el stop.",
        "La liquidación quedaría demasiado cerca del stop.",
        Unit.MULTIPLE,
        _LOW,
    ),
    VetoReason.DAILY_LOSS: Template(
        "Pérdida diaria",
        "Si todo saliera mal, la pérdida del día podría llegar a USD {obs} y el límite diario "
        "es USD {lim}.",
        "Si todo saliera mal, la pérdida del día superaría el límite diario.",
    ),
    VetoReason.WEEKLY_LOSS: Template(
        "Pérdida semanal",
        "Si todo saliera mal, la pérdida de la semana podría llegar a USD {obs} y el límite "
        "semanal es USD {lim}.",
        "Si todo saliera mal, la pérdida de la semana superaría el límite semanal.",
    ),
    VetoReason.CORRELATED_EXPOSURE: Template(
        "Exposición correlacionada",
        "El riesgo conjunto de {subject} sería USD {obs} y el límite es USD {lim}: se mueven "
        "casi juntos y cuentan como una sola apuesta.",
        "El riesgo conjunto de activos correlacionados superaría el límite.",
    ),
    VetoReason.BELOW_MIN_NOTIONAL: Template(
        "Orden demasiado pequeña",
        "La orden de {subject} sería de USD {obs} y el mínimo del contrato es USD {lim}; el "
        "tamaño nunca se aumenta para llegar al mínimo.",
        "La orden no llega al mínimo del contrato; el tamaño nunca se aumenta para llegar.",
        direction=_LOW,
    ),
    VetoReason.LIQUIDATION_MODEL_UNAVAILABLE: Template(
        "Liquidación sin fórmula",
        "No hay fórmula de liquidación verificada para {subject}: sin ella el motor no puede "
        "medir el riesgo y no aprueba.",
        "No hay fórmula de liquidación verificada para esta plataforma.",
    ),
    VetoReason.BETA_EXPOSURE: Template(
        "Exposición a cripto",
        "La exposición a cripto ajustada por beta frente a BTC sería USD {obs} y el máximo es "
        "USD {lim}.",
        "La exposición a cripto ajustada por beta superaría el máximo.",
    ),
    VetoReason.ALT_NOTIONAL: Template(
        "Tamaño en una alt",
        "La posición en {subject} sería de USD {obs} y el máximo por alt es USD {lim}.",
        "La posición en esta alt superaría el máximo por alt.",
    ),
    VetoReason.ALTS_TOTAL_NOTIONAL: Template(
        "Total en alts",
        "Las posiciones en alts sumarían USD {obs} y el máximo para todas las alts es USD {lim}.",
        "Las posiciones en alts superarían el máximo conjunto.",
    ),
    VetoReason.MAX_OPEN_POSITIONS: Template(
        "Posiciones simultáneas",
        "Habría {obs} posiciones abiertas a la vez y el máximo es {lim}.",
        "Se superaría el máximo de posiciones abiertas a la vez.",
        Unit.COUNT,
    ),
    VetoReason.STABLECOIN_DEPEG: Template(
        "Stablecoin fuera de paridad",
        "{subject} se desvía {obs} de su paridad con el dólar y lo tolerado es {lim}: se "
        "bloquean las entradas y se recomienda cerrar posiciones de forma ordenada.",
        "Una stablecoin perdió su paridad con el dólar: se bloquean las entradas.",
        Unit.PERCENT,
    ),
    VetoReason.MACRO_EVENT_WINDOW: Template(
        "Evento macro",
        "Hay un evento macro ({subject}) a {obs} de ahora; no se abren posiciones desde {lim} "
        "antes hasta {lim} después.",
        "Hay un evento macro cerca: no se abren posiciones en su ventana.",
        Unit.DURATION,
        _LOW,
    ),
    VetoReason.VOLATILITY_CIRCUIT: Template(
        "Volatilidad extrema",
        "La volatilidad de la última hora en {subject} es {obs} y supera su percentil 99 "
        "histórico ({lim}): se pausan las entradas hasta que se calme.",
        "La volatilidad de la última hora supera su percentil 99: se pausan las entradas.",
        Unit.PERCENT,
    ),
    VetoReason.API_ERROR_CIRCUIT: Template(
        "Errores de la API",
        "Hubo {obs} errores de la API en la ventana reciente y el disyuntor salta con {lim}: "
        "no se abren posiciones hasta que se estabilice.",
        "Hubo demasiados errores de la API: no se abren posiciones hasta que se estabilice.",
        Unit.COUNT,
    ),
    VetoReason.SPREAD_TOO_WIDE: Template(
        "Spread amplio",
        "El spread de {subject} es {obs} y el máximo es {lim}: entrar costaría más de lo que "
        "supone el backtest.",
        "El spread es demasiado amplio: entrar costaría más de lo que supone el backtest.",
        Unit.BPS,
    ),
    VetoReason.BOOK_TOO_THIN: Template(
        "Libro fino",
        "Hay USD {obs} de profundidad útil en {subject} y se necesitan al menos USD {lim} para "
        "que la orden no mueva el precio.",
        "El libro de órdenes es demasiado fino para el tamaño de la orden.",
        direction=_LOW,
    ),
    VetoReason.ADVERSE_FUNDING: Template(
        "Funding en contra",
        "El funding en contra de {subject} es {obs} cada 8 h y el máximo es {lim}: mantener "
        "la posición costaría demasiado.",
        "El funding en contra supera el máximo: mantener la posición costaría demasiado.",
        Unit.PERCENT,
    ),
    VetoReason.MISSING_CONDITION: Template(
        "Falta un dato",
        "Falta un dato que el motor necesita ({subject}); sin él no aprueba (fallo cerrado).",
        "Falta un dato que el motor necesita; sin él no aprueba (fallo cerrado).",
    ),
}


@in_risk_context
def explain(veto: Veto) -> VetoExplanation:
    """Código estable, título y mensaje en español de un veto."""
    template = TEMPLATES[veto.reason]
    text = template.message
    needs_obs = "{obs}" in text
    needs_lim = "{lim}" in text
    needs_subject = "{subject}" in text
    if (
        (needs_obs and veto.observed is None)
        or (needs_lim and veto.limit is None)
        or (needs_subject and not veto.subject)
    ):
        return VetoExplanation(veto.reason.value, template.title, template.fallback)
    high = template.direction is Direction.TOO_HIGH
    obs = _format(veto.observed, template.unit, ROUND_CEILING if high else ROUND_FLOOR)
    lim = _format(veto.limit, template.unit, ROUND_FLOOR if high else ROUND_CEILING)
    message = text.format(obs=obs, lim=lim, subject=veto.subject)
    return VetoExplanation(veto.reason.value, template.title, message)


def explain_decision(decision: RiskDecision) -> tuple[VetoExplanation, ...]:
    """Explicaciones de todos los vetos de una decisión, en el orden del motor."""
    return tuple(explain(veto) for veto in decision.vetoes)


def _format(value: Decimal | None, unit: Unit, rounding: str) -> str:
    if value is None:
        return ""
    match unit:
        case Unit.USD:
            return f"{value.quantize(Decimal('0.01'), rounding=rounding):,.2f}"
        case Unit.PERCENT:
            return f"{(value * 100).quantize(Decimal('0.01'), rounding=rounding):,.2f}%"
        case Unit.MULTIPLE:
            return f"{value.quantize(Decimal('0.01'), rounding=rounding):,.2f}x"
        case Unit.BPS:
            return f"{value.quantize(Decimal('0.1'), rounding=rounding):,.1f} pb"
        case Unit.COUNT:
            return f"{value.quantize(Decimal(1), rounding=rounding):,.0f}"
    # Unit.DURATION: segundos.
    return _duration(int(value.quantize(Decimal(1), rounding=rounding)))


def _duration(total_seconds: int) -> str:
    sign = "-" if total_seconds < 0 else ""
    hours, rest = divmod(abs(total_seconds), 3600)
    minutes, secs = divmod(rest, 60)
    parts = [
        f"{amount} {label}"
        for amount, label in ((hours, "h"), (minutes, "min"), (secs, "s"))
        if amount
    ]
    return sign + (" ".join(parts) if parts else "0 s")
