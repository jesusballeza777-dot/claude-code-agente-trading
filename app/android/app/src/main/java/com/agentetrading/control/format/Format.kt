package com.agentetrading.control.format

import com.agentetrading.control.model.LimitUnit
import java.util.Locale
import kotlin.math.abs

/** Formato de presentación. Los valores llegan calculados del backend; aquí solo se muestran. */
object Format {
    private const val EMPTY = "—"

    fun usd(value: Double?): String {
        if (value == null) return EMPTY
        val sign = if (value < 0) "-" else ""
        return sign + String.format(Locale.US, "$%,.2f", abs(value))
    }

    fun r(value: Double?): String = if (value == null) EMPTY else String.format(Locale.US, "%+.2f R", value)

    fun pct(fraction: Double): String = String.format(Locale.US, "%.1f%%", fraction * 100)

    fun multiple(value: Double): String = String.format(Locale.US, "%.2fx", value)

    fun bps(value: Double): String = String.format(Locale.US, "%.1f pb", value)

    fun limit(value: Double, unit: LimitUnit): String =
        when (unit) {
            LimitUnit.PERCENT -> pct(value)
            LimitUnit.MULTIPLE -> multiple(value)
        }

    /** Fracción de la barra de un límite, acotada a [0, 1]. Un límite no positivo cuenta como lleno. */
    fun usage(used: Double, limit: Double): Float =
        if (limit <= 0.0) 1f else (used / limit).coerceIn(0.0, 1.0).toFloat()
}
