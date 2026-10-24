package com.agentetrading.control.model

import java.time.LocalDate
import java.time.temporal.ChronoUnit

/** Línea de tiempo de regímenes de BTC: cuánto ocupa cada tramo dentro del periodo mostrado. */
object RegimeTimeline {
    class Segment(val regimen: String, val share: Double)

    /** Solo los tramos que terminan en o después de `from` (2020-01-01: el periodo de investigación). */
    fun segments(tramos: List<Tramo>, from: String = "2020-01-01"): List<Segment> {
        val kept = tramos.filter { it.hasta >= from }
        val days = kept.map { ChronoUnit.DAYS.between(LocalDate.parse(it.desde), LocalDate.parse(it.hasta)) + 1 }
        val total = days.sum().toDouble().takeIf { it > 0 } ?: return emptyList()
        return kept.indices.map { Segment(kept[it].regimen, days[it] / total) }
    }
}
