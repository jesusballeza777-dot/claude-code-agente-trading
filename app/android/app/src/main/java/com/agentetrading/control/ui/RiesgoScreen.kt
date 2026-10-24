package com.agentetrading.control.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentetrading.control.Format
import com.agentetrading.control.model.Calculo
import com.agentetrading.control.model.Limite
import com.agentetrading.control.model.Limites
import com.agentetrading.control.model.PageParsers
import com.agentetrading.control.net.ApiClient
import com.agentetrading.control.net.Query
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONException

/** Riesgo: la calculadora usa el motor real (el mismo que vetaría una operación de verdad). No envía nada. */
@Composable
fun RiesgoScreen(env: Env) {
    val limites = env.poll("/api/riesgo/limites", 120_000, PageParsers::limites)
    Page("Riesgo", "El motor de riesgo tiene veto absoluto y no depende de Claude. Sus límites solo cambian con un ADR que apruebas tú.", limites, env.refresh) { data ->
        Calculadora(env)
        LimitesCard(data)
        VetosCard(env)
    }
}

private sealed interface CalcState {
    data object Idle : CalcState

    data object Busy : CalcState

    data class Done(val calculo: Calculo) : CalcState

    data class Error(val message: String) : CalcState
}

@Composable
private fun Calculadora(env: Env) {
    var symbol by rememberSaveable { mutableStateOf("BTCUSDT") }
    var perpetual by rememberSaveable { mutableStateOf(true) }
    var long by rememberSaveable { mutableStateOf(true) }
    var leverage by rememberSaveable { mutableStateOf("3") }
    var entry by rememberSaveable { mutableStateOf("60000") }
    var stop by rememberSaveable { mutableStateOf("58800") }
    var capital by rememberSaveable { mutableStateOf("1500") }
    var state by remember { mutableStateOf<CalcState>(CalcState.Idle) }
    val scope = rememberCoroutineScope()

    fun calculate() {
        state = CalcState.Busy
        val path =
            Query.build(
                "/api/riesgo/calculadora",
                listOf(
                    "simbolo" to symbol.trim().uppercase(),
                    "mercado" to if (perpetual) "PERPETUAL" else "SPOT",
                    "lado" to if (long) "LONG" else "SHORT",
                    "entrada" to entry.trim(),
                    "stop" to stop.trim(),
                    "apalancamiento" to leverage.trim(),
                    "capital" to capital.trim(),
                ),
            )
        scope.launch {
            state =
                when (val result = withContext(Dispatchers.IO) { env.client.get(path) }) {
                    is ApiClient.Result.Ok ->
                        try {
                            CalcState.Done(PageParsers.calculo(result.json))
                        } catch (_: JSONException) {
                            CalcState.Error("Respuesta inesperada del servidor.")
                        }
                    is ApiClient.Result.NeedsLogin -> {
                        env.onNeedsLogin()
                        CalcState.Idle
                    }
                    is ApiClient.Result.Failed -> CalcState.Error(result.message)
                }
        }
    }

    InfoCard("Calculadora con el motor real", subtitle = "Mismo código que vetaría una operación de verdad. No envía nada a ningún exchange.") {
        OutlinedTextField(
            value = symbol,
            onValueChange = { symbol = it.uppercase() },
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Activo") },
            singleLine = true,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(selected = perpetual, onClick = { perpetual = true }, label = { Text("Perpetuo") })
            FilterChip(selected = !perpetual, onClick = { perpetual = false }, label = { Text("Spot") })
            FilterChip(selected = long, onClick = { long = true }, label = { Text("Largo") })
            FilterChip(selected = !long, onClick = { long = false }, label = { Text("Corto") })
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Field("Entrada (USD)", entry, { entry = it }, Modifier.weight(1f))
            Field("Stop (USD)", stop, { stop = it }, Modifier.weight(1f))
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Field("Capital (USD)", capital, { capital = it }, Modifier.weight(1f))
            Field("Apalancamiento", leverage, { leverage = it }, Modifier.weight(1f))
        }
        Button(onClick = { calculate() }, enabled = state != CalcState.Busy, modifier = Modifier.fillMaxWidth()) {
            Text(if (state == CalcState.Busy) "Calculando…" else "Calcular")
        }
        when (val current = state) {
            is CalcState.Done -> CalcResult(current.calculo)
            is CalcState.Error -> Text(current.message, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodyMedium)
            else -> Unit
        }
    }
}

@Composable
private fun Field(label: String, value: String, onChange: (String) -> Unit, modifier: Modifier) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        modifier = modifier,
        label = { Text(label) },
        singleLine = true,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
    )
}

@Composable
private fun CalcResult(calculo: Calculo) {
    val color = if (calculo.aprobada) Palette.Gain else Palette.Loss
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text(
            if (calculo.aprobada) "✓ El motor la aprobaría" else "✕ El motor la vetaría",
            color = color,
            fontWeight = FontWeight.Bold,
            fontSize = 16.sp,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            BigStat("Tamaño", Format.quantity(calculo.cantidad), Modifier.weight(1f))
            BigStat("Nocional", Format.price(calculo.nocional), Modifier.weight(1f))
        }
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            BigStat("Riesgo con costes", Format.price(calculo.riesgoUsd), Modifier.weight(1f))
            BigStat("Presupuesto", Format.price(calculo.presupuestoUsd), Modifier.weight(1f))
        }
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            BigStat("Apalancamiento efectivo", Format.multiple(calculo.apalancamientoEfectivo), Modifier.weight(1f))
            BigStat("Liquidación estimada", Format.price(calculo.precioLiquidacion), Modifier.weight(1f))
        }
        Text(
            "Costes supuestos: ${Format.pct(calculo.comision.toDouble())} de comisión + ${Format.pct(calculo.slippage.toDouble())} de slippage por lado.",
            fontSize = 12.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        if (calculo.aprobada) {
            Text(
                "Esta operación respeta todos los límites. Aun así, aprobarla no significa que vaya a ganar: solo que, si pierde, pierde dentro de lo acordado.",
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.clip(RoundedCornerShape(14.dp)).background(Palette.AccentSoft).padding(12.dp),
            )
        }
        calculo.vetos.forEach { veto ->
            Column(modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(MaterialTheme.colorScheme.surfaceVariant).padding(12.dp)) {
                Text(veto.titulo, fontWeight = FontWeight.SemiBold, color = Palette.Loss)
                Text(veto.explicacion, style = MaterialTheme.typography.bodyMedium)
                Text(veto.codigo, fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

private fun valor(limite: Limite): String = if (limite.esFraccion) Format.pct(limite.valor.toDouble()) else "${limite.valor}x"

private fun techo(limite: Limite): String = if (limite.esFraccion) Format.pct(limite.techoPlan.toDouble()) else "${limite.techoPlan}x"

@Composable
private fun LimitesCard(data: Limites) {
    InfoCard("Límites vigentes", subtitle = data.aviso, origin = data.origen) {
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            data.vigentes.forEach { limite ->
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(limite.nombre, style = MaterialTheme.typography.bodyMedium)
                        Text("techo del plan ${techo(limite)} · ${limite.adr}", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    Text(valor(limite), fontWeight = FontWeight.SemiBold)
                }
            }
            data.gruposCorrelacionados.forEach { group ->
                Text("${group.joinToString(" y ")} cuentan como una sola exposición: ${group.joinToString(" + ")}.", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
private fun VetosCard(env: Env) {
    val vetos = env.poll("/api/riesgo/vetos", 120_000, PageParsers::vetos)
    val data = vetos.data ?: return
    InfoCard("Historial de vetos", subtitle = data.nota, origin = data.origen) {
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            data.vetos.forEach { veto ->
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(veto.titulo, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
                        Text(veto.explicacion, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    Text("${veto.veces}", fontWeight = FontWeight.SemiBold)
                }
            }
        }
    }
}
