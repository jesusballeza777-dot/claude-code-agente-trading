package com.agentetrading.control.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentetrading.control.Format
import com.agentetrading.control.model.LabParsers
import com.agentetrading.control.model.RegimeTimeline
import com.agentetrading.control.model.Velas
import com.agentetrading.control.net.Query

private val WINDOWS = listOf(60, 120, 240)

/** Mercado: velas reales del archivo público de Binance (2020-2024). El holdout de 2025 no se muestra. */
@Composable
fun MercadoScreen(env: Env) {
    var symbol by rememberSaveable { mutableStateOf("BTCUSDT") }
    var interval by rememberSaveable { mutableStateOf("4h") }
    var window by rememberSaveable { mutableIntStateOf(120) }
    val symbols = env.poll("/api/mercado/simbolos", 600_000, LabParsers::simbolos)
    // Días suficientes para el tramo más largo: 240 velas de 4h son 40 días; 240 diarias, 240.
    val days = if (interval == "4h") 60 else 300
    val path = Query.build("/api/mercado/velas", listOf("simbolo" to symbol, "intervalo" to interval, "dias" to days.toString()))
    val candles = env.poll(path, 60_000, LabParsers::velas)

    Page(
        "Mercado",
        "Velas reales del archivo público de Binance (2020-2024) con los indicadores que usan las hipótesis. El holdout de 2025 en adelante no se muestra.",
        candles,
        env.refresh,
        header = { Selectors(symbols.data?.simbolos ?: listOf(symbol), symbol, { symbol = it }, interval, { interval = it }, window) { window = it } },
    ) { v ->
        GraficoCard(v, window)
        FundingCard(v)
        RegimenCard(env)
        CorrelacionesCard(env)
    }
}

@Composable
private fun Selectors(
    symbols: List<String>,
    symbol: String,
    onSymbol: (String) -> Unit,
    interval: String,
    onInterval: (String) -> Unit,
    window: Int,
    onWindow: (Int) -> Unit,
) {
    var menu by remember { mutableStateOf(false) }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Box {
            OutlinedButton(onClick = { menu = true }) { Text("Activo: $symbol") }
            DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                symbols.forEach { s ->
                    DropdownMenuItem(
                        text = { Text(s) },
                        onClick = {
                            onSymbol(s)
                            menu = false
                        },
                    )
                }
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.horizontalScroll(rememberScrollState())) {
            listOf("4h", "1d").forEach { FilterChip(selected = interval == it, onClick = { onInterval(it) }, label = { Text(it) }) }
            WINDOWS.forEach { FilterChip(selected = window == it, onClick = { onWindow(it) }, label = { Text("$it velas") }) }
        }
    }
}

@Composable
private fun GraficoCard(v: Velas, window: Int) {
    val n = minOf(window, v.velas.size)
    val sameLength = v.canalAlto.size == v.velas.size && v.canalBajo.size == v.velas.size
    InfoCard("${v.simbolo} · ${v.intervalo}", subtitle = "Toca una vela para ver sus precios.", origin = v.origen) {
        CandleChart(
            candles = v.velas.takeLast(n),
            channelHigh = if (sameLength) v.canalAlto.takeLast(n) else emptyList(),
            channelLow = if (sameLength) v.canalBajo.takeLast(n) else emptyList(),
            markers = v.marcadores,
        )
        Text(
            "H2 entra cuando el cierre rompe el canal de 60 velas (línea ámbar) con la volatilidad en aumento. El triángulo es una entrada y el círculo una salida de la simulación.",
            fontSize = 11.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun FundingCard(v: Velas) {
    InfoCard("Funding", subtitle = "Tasa por 8 h; positiva = pagan los largos.") {
        val last = v.funding.lastOrNull()
        if (last == null) {
            Text("Sin funding para este activo en el periodo.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        } else {
            Text(Format.pct(last.tasa8h, 4), fontSize = 26.sp, fontWeight = FontWeight.SemiBold)
            Text("Última liquidación del periodo (${last.t.take(10)}).", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            FundingBars(v.funding.takeLast(90).map { it.tasa8h })
        }
        Text(
            "Pago entre largos y cortos cada pocas horas. El ADR-013 propone no entrar si el funding en contra supera 0.10% cada 8 h.",
            fontSize = 11.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

private fun regimeColor(regimen: String): Color =
    when (regimen) {
        "alcista" -> Palette.Gain
        "bajista" -> Palette.Loss
        "lateral" -> Palette.Neutral
        else -> Color(0xFF1D4652)
    }

@Composable
private fun RegimenCard(env: Env) {
    val polled = env.poll("/api/mercado/regimenes", 600_000, LabParsers::regimenes)
    val data = polled.data ?: return
    InfoCard("Régimen de BTC", subtitle = "Media de 200 días del par spot (solo para etiquetar)", origin = data.origen) {
        val segments = RegimeTimeline.segments(data.tramos)
        if (segments.isEmpty()) {
            Text("Sin datos de regímenes.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        } else {
            Row(modifier = Modifier.fillMaxWidth().height(22.dp).clip(RoundedCornerShape(50))) {
                segments.forEach { Box(modifier = Modifier.weight(it.share.toFloat().coerceAtLeast(0.0005f)).height(22.dp).background(regimeColor(it.regimen))) }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                listOf("alcista", "bajista", "lateral").forEach { name ->
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                        Box(modifier = Modifier.width(10.dp).height(10.dp).clip(RoundedCornerShape(3.dp)).background(regimeColor(name)))
                        Text(name, fontSize = 12.sp)
                    }
                }
            }
        }
        Text(
            "Alcista: precio sobre su media de 200 días y la media subiendo. Bajista: lo contrario. Lateral: el resto.",
            fontSize = 11.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun CorrelacionesCard(env: Env) {
    val polled = env.poll("/api/mercado/correlaciones", 600_000, LabParsers::correlaciones)
    val data = polled.data ?: return
    InfoCard("Correlaciones", subtitle = data.ventana.ifEmpty { "Rendimientos diarios" }, origin = data.origen) {
        Column(modifier = Modifier.horizontalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Row(horizontalArrangement = Arrangement.spacedBy(2.dp)) {
                Box(modifier = Modifier.width(44.dp))
                data.simbolos.forEach { Text(it.removeSuffix("USDT"), fontSize = 9.sp, modifier = Modifier.width(34.dp), color = MaterialTheme.colorScheme.onSurfaceVariant) }
            }
            data.matriz.forEachIndexed { i, row ->
                Row(horizontalArrangement = Arrangement.spacedBy(2.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text(data.simbolos.getOrElse(i) { "" }.removeSuffix("USDT"), fontSize = 9.sp, modifier = Modifier.width(44.dp), color = MaterialTheme.colorScheme.onSurfaceVariant)
                    row.forEach { value ->
                        Box(
                            modifier =
                                Modifier
                                    .width(34.dp)
                                    .height(26.dp)
                                    .clip(RoundedCornerShape(4.dp))
                                    .background(if (value == null) MaterialTheme.colorScheme.surfaceVariant else MaterialTheme.colorScheme.primary.copy(alpha = (kotlin.math.abs(value) * 0.4).toFloat())),
                            contentAlignment = Alignment.Center,
                        ) { Text(if (value == null) "·" else Format.decimal(value, 1), fontSize = 10.sp) }
                    }
                }
            }
        }
        Text(
            "Cerca de 1: se mueven juntos. Por eso BTC y ETH cuentan como una sola apuesta en el motor de riesgo.",
            fontSize = 11.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}
