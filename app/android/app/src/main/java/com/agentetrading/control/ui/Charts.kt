package com.agentetrading.control.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentetrading.control.Format
import com.agentetrading.control.model.Barra
import com.agentetrading.control.model.Marcador
import com.agentetrading.control.model.MesR
import com.agentetrading.control.model.PuntoMc
import com.agentetrading.control.model.Vela
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

/** Drawdown desde el máximo ("underwater"): siempre ≤ 0; el cero es la línea de arriba. */
@Composable
fun DrawdownArea(values: List<Double>, modifier: Modifier = Modifier) {
    Canvas(modifier = modifier.fillMaxWidth().height(110.dp)) {
        if (values.size < 2) return@Canvas
        val lowest = values.min().takeIf { it < 0 } ?: return@Canvas
        val dx = size.width / (values.size - 1)
        fun y(v: Double) = (size.height * (v / lowest)).toFloat()
        val line = Path().apply { values.forEachIndexed { i, v -> if (i == 0) moveTo(0f, y(v)) else lineTo(i * dx, y(v)) } }
        val fill = Path().apply {
            moveTo(0f, 0f)
            values.forEachIndexed { i, v -> lineTo(i * dx, y(v)) }
            lineTo(size.width, 0f)
            close()
        }
        drawPath(fill, Palette.Loss.copy(alpha = 0.18f))
        drawPath(line, Palette.Loss, style = Stroke(width = 2.dp.toPx(), cap = StrokeCap.Round))
        drawLine(Palette.Neutral, Offset(0f, 0f), Offset(size.width, 0f), strokeWidth = 1.dp.toPx())
    }
}

/** Distribución de los resultados por operación, en múltiplos de R: verde si ganó, rojo si perdió. */
@Composable
fun Histogram(bars: List<Barra>, modifier: Modifier = Modifier) {
    Canvas(modifier = modifier.fillMaxWidth().height(120.dp)) {
        val tallest = bars.maxOfOrNull { it.n }?.takeIf { it > 0 } ?: return@Canvas
        val step = size.width / bars.size
        bars.forEachIndexed { i, bar ->
            val h = size.height * bar.n / tallest
            drawRect(
                color = if (bar.desde >= 0) Palette.Gain else Palette.Loss,
                topLeft = Offset(i * step + step * 0.08f, size.height - h),
                size = Size(step * 0.84f, h),
            )
        }
    }
}

/** Abanico de Monte Carlo: bandas p5-p95 y p25-p75 alrededor de la mediana. */
@Composable
fun FanChart(points: List<PuntoMc>, modifier: Modifier = Modifier) {
    val accent = MaterialTheme.colorScheme.primary
    Canvas(modifier = modifier.fillMaxWidth().height(150.dp)) {
        if (points.size < 2) return@Canvas
        val lo = points.minOf { it.p5 }
        val hi = points.maxOf { it.p95 }
        val span = (hi - lo).takeIf { it > 0 } ?: 1.0
        val dx = size.width / (points.size - 1)
        fun y(v: Double) = (size.height * (1 - (v - lo) / span)).toFloat()

        fun band(upper: (PuntoMc) -> Double, lower: (PuntoMc) -> Double) =
            Path().apply {
                points.forEachIndexed { i, p -> if (i == 0) moveTo(0f, y(upper(p))) else lineTo(i * dx, y(upper(p))) }
                for (i in points.indices.reversed()) lineTo(i * dx, y(lower(points[i])))
                close()
            }
        drawPath(band({ it.p95 }, { it.p5 }), accent.copy(alpha = 0.15f))
        drawPath(band({ it.p75 }, { it.p25 }), accent.copy(alpha = 0.30f))
        val median = Path().apply { points.forEachIndexed { i, p -> if (i == 0) moveTo(0f, y(p.p50)) else lineTo(i * dx, y(p.p50)) } }
        drawPath(median, accent, style = Stroke(width = 2.dp.toPx(), cap = StrokeCap.Round))
        if (1.0 in lo..hi) drawLine(Palette.Neutral, Offset(0f, y(1.0)), Offset(size.width, y(1.0)), strokeWidth = 1.dp.toPx())
    }
}

/** Mapa mensual: celdas con color y cifra (nunca solo color). Años en filas, meses en columnas. */
@Composable
fun MonthHeatmap(months: List<MesR>, modifier: Modifier = Modifier) {
    val years = months.map { it.mes.take(4) }.distinct()
    val peak = max(1.0, months.maxOfOrNull { abs(it.r) } ?: 1.0)
    val labels = listOf("E", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D")
    Column(modifier = modifier, verticalArrangement = Arrangement.spacedBy(3.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(3.dp)) {
            Box(modifier = Modifier.weight(1.4f))
            labels.forEach { Text(it, fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant, textAlign = TextAlign.Center, modifier = Modifier.weight(1f)) }
        }
        years.forEach { year ->
            Row(horizontalArrangement = Arrangement.spacedBy(3.dp), verticalAlignment = Alignment.CenterVertically) {
                Text(year, fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.weight(1.4f))
                (1..12).forEach { month ->
                    val value = months.firstOrNull { it.mes == "$year-${month.toString().padStart(2, '0')}" }?.r ?: 0.0
                    // Tope del 40% de color: el texto mantiene el contraste.
                    val alpha = min(abs(value) / peak, 1.0).toFloat() * 0.3f + if (value == 0.0) 0f else 0.1f
                    Box(
                        modifier =
                            Modifier
                                .weight(1f)
                                .clip(RoundedCornerShape(4.dp))
                                .background(if (value == 0.0) MaterialTheme.colorScheme.surfaceVariant else (if (value > 0) Palette.Gain else Palette.Loss).copy(alpha = alpha))
                                .padding(vertical = 5.dp),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text(if (value == 0.0) "·" else Format.decimal(value, 1), fontSize = 9.sp)
                    }
                }
            }
        }
    }
}

/** Velas con canal de H2, marcas de entrada y salida; toca una vela para ver su OHLC. */
@Composable
fun CandleChart(
    candles: List<Vela>,
    channelHigh: List<Double?>,
    channelLow: List<Double?>,
    markers: List<Marcador>,
    modifier: Modifier = Modifier,
) {
    var selected by remember(candles) { mutableStateOf<Int?>(null) }
    val accent = MaterialTheme.colorScheme.primary
    Column(modifier = modifier) {
        Canvas(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .height(260.dp)
                    .pointerInput(candles) {
                        detectTapGestures { offset -> selected = (offset.x / size.width * candles.size).toInt().coerceIn(0, candles.lastIndex) }
                    },
        ) {
            if (candles.isEmpty()) return@Canvas
            val lo = candles.minOf { it.l }
            val hi = candles.maxOf { it.h }
            val span = (hi - lo).takeIf { it > 0 } ?: 1.0
            val step = size.width / candles.size
            val body = step * 0.7f
            fun y(price: Double) = (size.height * (1 - (price - lo) / span)).toFloat().coerceIn(0f, size.height)
            fun x(index: Int) = step * index + step / 2

            fun channel(values: List<Double?>, color: Color) {
                if (values.size != candles.size) return
                val path = Path()
                var started = false
                values.forEachIndexed { i, v ->
                    if (v == null) return@forEachIndexed
                    if (!started) path.moveTo(x(i), y(v)).also { started = true } else path.lineTo(x(i), y(v))
                }
                if (started) drawPath(path, color, style = Stroke(width = 1.dp.toPx()))
            }
            channel(channelHigh, Palette.Warn.copy(alpha = 0.7f))
            channel(channelLow, Palette.Warn.copy(alpha = 0.7f))

            candles.forEachIndexed { i, c ->
                val color = if (c.c >= c.o) Palette.Gain else Palette.Loss
                drawLine(color, Offset(x(i), y(c.h)), Offset(x(i), y(c.l)), strokeWidth = 1.dp.toPx())
                val top = y(max(c.o, c.c))
                val bottom = y(min(c.o, c.c))
                drawRect(color, Offset(x(i) - body / 2, top), Size(body, max(bottom - top, 1.dp.toPx())))
            }

            val index = candles.withIndex().associate { it.value.t to it.index }
            markers.forEach { m ->
                val i = index[m.t] ?: return@forEach
                if (m.tipo == "entrada") {
                    val base = y(candles[i].l) + 10.dp.toPx()
                    val tip = Path().apply {
                        moveTo(x(i), base - 8.dp.toPx())
                        lineTo(x(i) - 5.dp.toPx(), base)
                        lineTo(x(i) + 5.dp.toPx(), base)
                        close()
                    }
                    drawPath(tip, accent)
                } else {
                    drawCircle(accent, radius = 4.dp.toPx(), center = Offset(x(i), y(candles[i].c)), style = Stroke(width = 2.dp.toPx()))
                }
            }
            selected?.let { i -> drawLine(Color.White.copy(alpha = 0.5f), Offset(x(i), 0f), Offset(x(i), size.height), strokeWidth = 1.dp.toPx()) }
        }
        val shown = selected?.let { candles.getOrNull(it) } ?: candles.lastOrNull()
        if (shown != null) {
            Text(
                "${Format.fechaHora(shown.t)} · A ${Format.price(shown.o.toString(), prefix = false)} · M ${Format.price(shown.h.toString(), prefix = false)} · " +
                    "m ${Format.price(shown.l.toString(), prefix = false)} · C ${Format.price(shown.c.toString(), prefix = false)}",
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 6.dp),
            )
        }
    }
}

/** Barras de funding por liquidación: turquesa si pagan los largos, rojo si pagan los cortos. */
@Composable
fun FundingBars(rates: List<Double>, modifier: Modifier = Modifier) {
    Canvas(modifier = modifier.fillMaxWidth().height(56.dp)) {
        if (rates.isEmpty()) return@Canvas
        val step = size.width / rates.size
        rates.forEachIndexed { i, rate ->
            val h = max(size.height * min(abs(rate) / 0.001, 1.0).toFloat(), 1.dp.toPx())
            drawRect(
                color = if (rate >= 0) Color(0xFF2DD4BF) else Palette.Loss,
                topLeft = Offset(i * step + step * 0.1f, size.height - h),
                size = Size(step * 0.8f, h),
            )
        }
    }
}
