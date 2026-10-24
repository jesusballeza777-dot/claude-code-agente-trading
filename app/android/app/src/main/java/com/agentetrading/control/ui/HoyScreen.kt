package com.agentetrading.control.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentetrading.control.Format
import com.agentetrading.control.R
import com.agentetrading.control.model.Hoy
import com.agentetrading.control.model.Origen

/** Hoy: ¿estoy a salvo?, ¿qué ha decidido el sistema?, ¿está aprendiendo de verdad? En segundos. */
@Composable
fun HoyScreen(polled: Polled<Hoy>, local: Boolean, onRefresh: () -> Unit) {
    val hoy = polled.data
    Column(
        modifier = Modifier.verticalScroll(rememberScrollState()).padding(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(modifier = Modifier.weight(1f)) {
                Text("Hoy", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
                Text(
                    "¿Estoy a salvo? ¿Qué ha decidido el sistema? ¿Está aprendiendo de verdad?",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            IconButton(onClick = onRefresh) { Icon(Icons.Filled.Refresh, contentDescription = "Actualizar") }
        }
        when {
            hoy == null && polled.error != null -> ErrorBox(polled.error, onRefresh)
            hoy == null -> LoadingBox()
            else -> {
                if (polled.error != null) OfflineBanner(polled.error)
                Semaforo(hoy, local)
                ParteDelDia(hoy)
                CapitalYDrawdown(hoy)
                Presupuesto(hoy)
                InfoCard("Posiciones abiertas", origin = hoy.posiciones.origen) {
                    Text(
                        if (hoy.posiciones.cantidad == 0) hoy.posiciones.vacio else "${hoy.posiciones.cantidad} posiciones abiertas.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                InfoCard("Próximos eventos macro", origin = hoy.eventosMacro.origen) {
                    Text(hoy.eventosMacro.vacio, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                Pendientes(hoy)
                Text(
                    "No es asesoría financiera, legal ni fiscal. La rentabilidad es una hipótesis que el sistema tiene que demostrar.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(vertical = 8.dp),
                )
            }
        }
    }
}

@Composable
private fun Semaforo(hoy: Hoy, local: Boolean) {
    val estado = hoy.estado
    InfoCard("Semáforo del sistema", origin = estado.origen) {
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            StatusRow(
                "Ejecución real",
                if (estado.liveTrading) "LIVE_TRADING ENCENDIDO: revisa de inmediato" else "LIVE_TRADING apagado",
                if (estado.liveTrading) Tone.BAD else Tone.GOOD,
            )
            StatusRow("Fase", estado.faseActual, Tone.NEUTRAL)
            StatusRow(
                "Datos",
                if (local && !estado.datosDisponible) {
                    "Los datos de mercado 2020-2024 (unos 200 MB) viven en tu servidor"
                } else if (estado.datosDisponible) "2020-2024 al ${Format.pctOf(estado.completitud)} · última vela ${estado.ultimaVela ?: "—"}" else "Sin descargar",
                if (estado.datosDisponible) Tone.GOOD else if (local) Tone.NEUTRAL else Tone.WARN,
            )
            StatusRow(
                "Motor de riesgo",
                "${estado.motorEstado} · límites ${estado.versionLimites}",
                if (estado.motorEstado == "operativo") Tone.GOOD else Tone.BAD,
            )
            StatusRow(
                "Holdout",
                if (estado.holdoutSellado) "Sellado desde ${estado.holdoutDesde}" else "ABIERTO: revisa de inmediato",
                if (estado.holdoutSellado) Tone.GOOD else Tone.BAD,
            )
            StatusRow("Intentos registrados", "${estado.intentosPrincipales} principales · ${estado.intentosTotal} corridas en total", Tone.NEUTRAL)
        }
    }
}

@Composable
private fun ParteDelDia(hoy: Hoy) {
    InfoCard("Parte del día") {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Image(painterResource(R.drawable.ic_launcher_foreground), contentDescription = null, modifier = Modifier.size(44.dp))
            Column(
                modifier =
                    Modifier
                        .clip(RoundedCornerShape(16.dp))
                        .background(Palette.AccentSoft)
                        .padding(12.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                Text(hoy.parte.autor.uppercase(), fontSize = 10.sp, letterSpacing = 0.8.sp, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
                Text(hoy.parte.texto, style = MaterialTheme.typography.bodyMedium)
                if (hoy.parte.validado) {
                    Text("✓ cifras verificadas con los datos", fontSize = 11.sp, color = MaterialTheme.colorScheme.primary)
                }
            }
        }
    }
}

@Composable
private fun CapitalYDrawdown(hoy: Hoy) {
    val cuenta = hoy.cuenta
    InfoCard("Capital y drawdown", subtitle = if (cuenta.origen == Origen.DEMO) "La simulación en sombra empieza en la F7: esto es un ejemplo." else null, origin = cuenta.origen) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            BigStat("Capital", Format.usd(cuenta.capital), Modifier.weight(1f))
            BigStat("Máximo", Format.usd(cuenta.maximo), Modifier.weight(1f))
            BigStat("Drawdown", Format.pct(cuenta.drawdown), Modifier.weight(0.7f))
        }
        DrawdownGauge(cuenta.drawdown, cuenta.parada, cuenta.corteDuro)
        Sparkline(cuenta.curva.map { it.capital })
        Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.CenterEnd) {
            Text(
                "${cuenta.curva.firstOrNull()?.t.orEmpty()} → ${cuenta.curva.lastOrNull()?.t.orEmpty()}",
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun Presupuesto(hoy: Hoy) {
    val cuenta = hoy.cuenta
    InfoCard("Presupuesto de pérdida", origin = cuenta.origen) {
        BudgetBar("Pérdida diaria", cuenta.diario.usado, cuenta.diario.limite, Format.pct(cuenta.diario.usado, 1), Format.pct(cuenta.diario.limite, 0))
        BudgetBar("Pérdida semanal", cuenta.semanal.usado, cuenta.semanal.limite, Format.pct(cuenta.semanal.usado, 1), Format.pct(cuenta.semanal.limite, 0))
        Text(cuenta.textoDiario, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun Pendientes(hoy: Hoy) {
    InfoCard("Tus pendientes", subtitle = "En orden. Ninguno se puede hacer desde la app.") {
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            hoy.estado.pendientes.forEachIndexed { index, item ->
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Box(
                        modifier = Modifier.size(22.dp).clip(CircleShape).background(MaterialTheme.colorScheme.surfaceVariant),
                        contentAlignment = Alignment.Center,
                    ) { Text("${index + 1}", fontSize = 11.sp) }
                    Column {
                        Text(item.tarea, style = MaterialTheme.typography.bodyMedium)
                        Text(item.documento, fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }
    }
}
