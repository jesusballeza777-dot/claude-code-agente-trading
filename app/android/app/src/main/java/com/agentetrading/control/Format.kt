package com.agentetrading.control

import java.math.BigDecimal
import java.math.RoundingMode
import java.text.DecimalFormat
import java.text.DecimalFormatSymbols
import java.util.Locale

/** Solo da formato a lo que entrega el servidor; ninguna cifra se calcula aquí (CLAUDE.md regla 3). */
object Format {
    private fun grouped(pattern: String) = DecimalFormat(pattern, DecimalFormatSymbols(Locale.US)).apply { roundingMode = RoundingMode.HALF_EVEN }

    /** "1500.34" -> "USD 1,500.34". Si no es un número se muestra "—". */
    fun usd(decimal: String): String {
        val value = decimal.toBigDecimalOrNull() ?: return "—"
        return "USD " + grouped("#,##0.00").format(value.setScale(2, RoundingMode.HALF_EVEN))
    }

    /** 0.0175 -> "1.75%". */
    fun pct(fraction: Double, decimals: Int = 2): String {
        val pattern = if (decimals == 0) "0" else "0." + "0".repeat(decimals)
        return grouped(pattern).format(BigDecimal.valueOf(fraction * 100)) + "%"
    }

    /** Completitud 0.998767 -> "99.88%". */
    fun pctOf(fraction: Double?): String = if (fraction == null) "—" else pct(fraction)

    /** "2026-10-06T20:00:00+00:00" -> "2026-10-06 20:00 UTC". */
    fun fechaHora(iso: String): String = if (iso.length >= 16) iso.substring(0, 16).replace('T', ' ') + " UTC" else iso

    fun ago(sinceMs: Long, nowMs: Long): String {
        val seconds = ((nowMs - sinceMs).coerceAtLeast(0) / 1000)
        return when {
            seconds < 5 -> "ahora mismo"
            seconds < 60 -> "hace $seconds s"
            else -> "hace ${seconds / 60} min"
        }
    }
}
