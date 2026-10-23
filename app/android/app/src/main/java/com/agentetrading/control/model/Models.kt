package com.agentetrading.control.model

// Modelos de pantalla. Reflejan el contrato de la API del backend
// (docs/app/especificacion.md §9); los números los calcula siempre el backend.

enum class LimitUnit { PERCENT, MULTIPLE }

data class LimitUsage(
    val label: String,
    val used: Double,
    val limit: Double,
    val unit: LimitUnit,
)

data class SafetyStatus(
    val liveTrading: Boolean,
    val killSwitch: Boolean,
    val dataFresh: Boolean,
    val venuesConnected: Map<String, Boolean>,
)

data class Summary(
    val mode: String,
    val autonomyStep: String,
    val nextStep: String,
    val safety: SafetyStatus,
    val capitalUsd: Double?,
    val pnlTodayUsd: Double?,
    val pnlTotalR: Double?,
    val limits: List<LimitUsage>,
    val nextDecision: String,
)

data class CountItem(val label: String, val count: Int)

data class FilterValue(val label: String, val measured: Int, val meanR: Double?)

data class Decisions(
    val funnel: List<CountItem>,
    val vetoReasons: List<CountItem>,
    val valueAdded: List<FilterValue>,
)

data class TradeCard(
    val tradeId: String,
    val symbol: String,
    val side: String,
    val strategy: String,
    val rMultiple: Double,
    val entrySlippageBps: Double,
    val exitSlippageBps: Double,
    val maeR: Double?,
    val mfeR: Double?,
    val rationale: String,
    val tags: List<String>,
)

data class TagImpact(val tag: String, val count: Int, val totalR: Double)

data class Learning(
    val trades: List<TradeCard>,
    val tagImpact: List<TagImpact>,
    val timeline: List<String>,
)

data class TaxReportInfo(
    val year: Int,
    val liveTrades: Int,
    val columns: List<String>,
    val note: String,
)
