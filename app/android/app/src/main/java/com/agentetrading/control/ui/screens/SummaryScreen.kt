package com.agentetrading.control.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.runtime.Composable
import androidx.compose.ui.unit.dp
import com.agentetrading.control.format.Format
import com.agentetrading.control.model.Summary
import com.agentetrading.control.ui.components.LabeledValue
import com.agentetrading.control.ui.components.LimitBar
import com.agentetrading.control.ui.components.Note
import com.agentetrading.control.ui.components.SectionCard
import com.agentetrading.control.ui.components.StatusRow

@Composable
fun SummaryScreen(summary: Summary) {
    val safety = summary.safety
    LazyColumn(contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            SectionCard("Autonomía (ADR-011)") {
                LabeledValue("Modo", summary.mode)
                LabeledValue("Escalón", summary.autonomyStep)
                Note("Siguiente: ${summary.nextStep}")
            }
        }
        item {
            SectionCard("Seguridad") {
                StatusRow(
                    label = if (safety.liveTrading) "LIVE_TRADING activado" else "LIVE_TRADING desactivado",
                    ok = !safety.liveTrading,
                    detail = "Solo se activa por CLI local con TOTP y commit firmado",
                )
                StatusRow(
                    label = if (safety.killSwitch) "Kill switch activado" else "Kill switch en reposo",
                    ok = !safety.killSwitch,
                    detail = "Bloquea entradas y cierra posiciones",
                )
                StatusRow(
                    label = if (safety.dataFresh) "Datos al día" else "Sin datos en vivo",
                    ok = safety.dataFresh,
                    detail = "El motor de riesgo veta con datos atrasados",
                )
                safety.venuesConnected.forEach { (venue, connected) ->
                    StatusRow(venue, connected, if (connected) "Conectado" else "Sin conexión")
                }
            }
        }
        item {
            SectionCard("Capital") {
                LabeledValue("Capital total", Format.usd(summary.capitalUsd))
                LabeledValue("P&L de hoy", Format.usd(summary.pnlTodayUsd))
                LabeledValue("Resultado total", Format.r(summary.pnlTotalR))
            }
        }
        item {
            SectionCard("Límites del plan §3") {
                summary.limits.forEach { LimitBar(it) }
            }
        }
        item {
            SectionCard("Próxima decisión") {
                Note(summary.nextDecision)
            }
        }
    }
}
