package com.agentetrading.control.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentetrading.control.Format
import com.agentetrading.control.model.EnVivo
import com.agentetrading.control.model.Motor

/** En vivo: qué piezas existen y trabajan, qué ha pasado y qué decisiones (de ejemplo) llegarán. */
@Composable
fun EnVivoScreen(polled: Polled<EnVivo>, now: Long, local: Boolean, onRefresh: () -> Unit) {
    val vivo = polled.data
    Column(
        modifier = Modifier.verticalScroll(rememberScrollState()).padding(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text("En vivo", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        when {
            vivo == null && polled.error != null -> ErrorBox(polled.error, onRefresh)
            vivo == null -> LoadingBox()
            else -> {
                if (local) SinServidor() else Pulso(vivo, polled, now)
                // Sin servidor no hay API ni datos que "responden": se omiten esas dos piezas.
                val motores = if (local) vivo.motores.filter { it.id != "api" && it.id != "datos" } else vivo.motores
                InfoCard("Piezas del sistema", subtitle = "Solo lo que existe aparece como activo.") {
                    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) { motores.forEach { MotorRow(it) } }
                }
                if (!local) InfoCard("Actividad", subtitle = "${vivo.totalEventos} eventos registrados") {
                    if (vivo.eventos.isEmpty()) {
                        Text(
                            "Aún no hay actividad. Aquí aparecerán tus notas, los reportes que generes y, desde la F7, cada decisión de la sombra.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    } else {
                        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            vivo.eventos.take(8).forEach { evento ->
                                Column {
                                    Text(evento.texto, style = MaterialTheme.typography.bodyMedium)
                                    Text(Format.fechaHora(evento.t), fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                            }
                        }
                    }
                }
                InfoCard("Decisiones del analista", subtitle = vivo.decisionesAviso, origin = vivo.decisionesOrigen) {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        vivo.decisiones.forEach { decision ->
                            Column(
                                modifier =
                                    Modifier
                                        .fillMaxWidth()
                                        .clip(RoundedCornerShape(14.dp))
                                        .background(MaterialTheme.colorScheme.surface.copy(alpha = 0.8f))
                                        .padding(12.dp),
                            ) {
                                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                    Text(decision.accion, fontWeight = FontWeight.SemiBold)
                                    Text(Format.fechaHora(decision.t), fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                                Text(decision.motivo, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                if (decision.veto != null) Text("Veto: ${decision.veto}", fontSize = 12.sp, color = Palette.Warn)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun Pulso(vivo: EnVivo, polled: Polled<EnVivo>, now: Long) {
    val offline = polled.error != null
    val activos = vivo.motores.count { it.activo }
    val color: Color = if (offline) Palette.Loss else MaterialTheme.colorScheme.primary
    Row(
        modifier =
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(20.dp))
                .background(if (offline) MaterialTheme.colorScheme.surface else Palette.AccentSoft)
                .padding(16.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        PulseDot(active = !offline, color = color)
        Column(modifier = Modifier.weight(1f)) {
            Text(
                if (offline) "Sin conexión con el servidor" else "$activos de ${vivo.motores.size} piezas activas",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
            )
            Text(
                (if (offline) "Mostrando lo último recibido · " else "Servidor respondiendo · ") + "actualizado ${Format.ago(polled.updatedAtMs, now)}",
                fontSize = 12.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Text(
            if (vivo.liveTrading) "LIVE_TRADING ENCENDIDO" else "LIVE_TRADING apagado",
            fontSize = 11.sp,
            fontWeight = FontWeight.Bold,
            color = if (vivo.liveTrading) Palette.Loss else MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun MotorRow(motor: Motor) {
    val tone =
        when (motor.estado) {
            "activo" -> Tone.GOOD
            "sin datos" -> Tone.WARN
            else -> Tone.NEUTRAL
        }
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
        Column(modifier = Modifier.weight(1f)) {
            Text(motor.nombre, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
            Text(motor.detalle, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Text(motor.estado, fontSize = 12.sp, fontWeight = FontWeight.Medium, color = tone.color())
    }
}

@Composable
private fun SinServidor() {
    val openSettings = LocalOpenSettings.current
    InfoCard("Sin servidor conectado") {
        Text(
            "En vivo muestra si el sistema responde, y para eso hace falta un servidor. Aquí ves el estado del proyecto según los datos incluidos en la app.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        androidx.compose.material3.Button(onClick = openSettings) { Text("Conectar mi servidor") }
    }
}
