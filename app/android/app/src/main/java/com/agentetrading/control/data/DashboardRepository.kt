package com.agentetrading.control.data

import com.agentetrading.control.model.CountItem
import com.agentetrading.control.model.Decisions
import com.agentetrading.control.model.FilterValue
import com.agentetrading.control.model.Learning
import com.agentetrading.control.model.LimitUnit
import com.agentetrading.control.model.LimitUsage
import com.agentetrading.control.model.SafetyStatus
import com.agentetrading.control.model.Summary
import com.agentetrading.control.model.TagImpact
import com.agentetrading.control.model.TaxReportInfo
import com.agentetrading.control.model.TradeCard

/** Fuente de datos de la app. La implementación real llamará a la API del backend (F6). */
interface DashboardRepository {
    val isDemo: Boolean

    fun summary(): Summary

    fun decisions(): Decisions

    fun learning(): Learning

    fun taxReport(): TaxReportInfo
}

/**
 * Datos de demostración. El resumen refleja el estado real del proyecto (F1, sin operaciones).
 * Decisiones y aprendizaje son ejemplos ilustrativos para ver el diseño: no son resultados.
 */
object DemoRepository : DashboardRepository {
    override val isDemo: Boolean = true

    override fun summary(): Summary =
        Summary(
            mode = "Investigación (F1)",
            autonomyStep = "0 · Investigación",
            nextStep = "1 · Sombra: una hipótesis tiene que pasar el gate de la F4",
            safety =
                SafetyStatus(
                    liveTrading = false,
                    killSwitch = false,
                    dataFresh = false,
                    venuesConnected = mapOf("Binance" to false, "Hyperliquid" to false),
                ),
            capitalUsd = null,
            pnlTodayUsd = null,
            pnlTotalR = null,
            limits =
                listOf(
                    LimitUsage("Drawdown (parada 15%)", 0.0, 0.15, LimitUnit.PERCENT),
                    LimitUsage("Pérdida diaria posible", 0.0, 0.02, LimitUnit.PERCENT),
                    LimitUsage("Pérdida semanal posible", 0.0, 0.04, LimitUnit.PERCENT),
                    LimitUsage("Apalancamiento efectivo", 0.0, 2.0, LimitUnit.MULTIPLE),
                ),
            nextDecision = "Sin estrategias activas todavía",
        )

    override fun decisions(): Decisions =
        Decisions(
            funnel =
                listOf(
                    CountItem("Señales de las reglas", 40),
                    CountItem("Claude propone entrar", 24),
                    CountItem("Aprobadas por el motor de riesgo", 19),
                    CountItem("Aprobadas por ti / nivel A", 15),
                    CountItem("Ejecutadas", 15),
                ),
            vetoReasons =
                listOf(
                    CountItem("Exposición BTC+ETH", 3),
                    CountItem("Pérdida diaria", 1),
                    CountItem("Datos atrasados", 1),
                ),
            valueAdded =
                listOf(
                    FilterValue("Ejecutadas", 15, 0.21),
                    FilterValue("Descartadas por Claude", 12, -0.08),
                    FilterValue("Vetadas por el motor", 5, -0.40),
                    FilterValue("Rechazadas por ti", 4, 0.05),
                ),
        )

    override fun learning(): Learning =
        Learning(
            trades =
                listOf(
                    TradeCard(
                        tradeId = "ejemplo-1",
                        symbol = "BTCUSDT",
                        side = "LARGO",
                        strategy = "H2",
                        rMultiple = 1.8,
                        entrySlippageBps = 2.0,
                        exitSlippageBps = 3.5,
                        maeR = -0.4,
                        mfeR = 2.3,
                        rationale = "Ruptura del canal de 10 días con volatilidad creciente.",
                        tags = listOf("GANADORA"),
                    ),
                    TradeCard(
                        tradeId = "ejemplo-2",
                        symbol = "ETHUSDT",
                        side = "CORTO",
                        strategy = "H2",
                        rMultiple = -1.4,
                        entrySlippageBps = 3.0,
                        exitSlippageBps = 18.0,
                        maeR = -1.4,
                        mfeR = 0.6,
                        rationale = "Ruptura bajista; el stop se ejecutó con gap.",
                        tags = listOf("PERDEDORA", "SLIPPAGE_SOBRE_MODELO", "PERDIDA_MAYOR_QUE_R"),
                    ),
                ),
            tagImpact =
                listOf(
                    TagImpact("PERDIDA_MAYOR_QUE_R", 2, -2.9),
                    TagImpact("GANANCIA_DEVUELTA", 1, -0.1),
                    TagImpact("FUNDING_RELEVANTE", 3, 1.2),
                ),
            timeline =
                listOf(
                    "23-oct-2026 · Pre-registro fusionado: H1-v1, H2-v1, H4-v1 (4614d65)",
                    "23-oct-2026 · Límites de riesgo firmados (ADR-007)",
                ),
        )

    override fun taxReport(): TaxReportInfo =
        TaxReportInfo(
            year = 2026,
            liveTrades = 0,
            columns =
                listOf(
                    "id_operacion",
                    "plataforma",
                    "instrumento",
                    "lado",
                    "fecha_fiscal_cdmx",
                    "pnl_neto_usd",
                    "tipo_cambio_mxn_usd",
                    "pnl_neto_mxn",
                ),
            note = "Formato por validar con tu contador. Solo incluye operaciones reales.",
        )
}
