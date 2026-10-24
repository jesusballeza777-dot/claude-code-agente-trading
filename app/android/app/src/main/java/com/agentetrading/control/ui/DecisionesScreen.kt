package com.agentetrading.control.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentetrading.control.Format
import com.agentetrading.control.model.PageParsers

/** Decisiones del analista: llegan con la F5; mientras tanto, ejemplos rotulados. */
@Composable
fun DecisionesScreen(env: Env) {
    val polled = env.poll("/api/decisiones", 60_000, PageParsers::decisiones)
    Page("Decisiones del analista", "Cada decisión de Claude con su acción, nivel, motivo, evidencia y los vetos del motor. Llega con la F5.", polled, env.refresh) { data ->
        Text(
            data.vacio,
            style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp)).background(Palette.AccentSoft).padding(14.dp),
        )
        InfoCard("Línea de tiempo", subtitle = "Toca una decisión para ver su JSON.", origin = data.origen) {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                data.decisiones.forEachIndexed { index, decision ->
                    var open by rememberSaveable(index) { mutableStateOf(false) }
                    Column(
                        modifier =
                            Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(14.dp))
                                .background(MaterialTheme.colorScheme.surface.copy(alpha = 0.8f))
                                .clickable { open = !open }
                                .padding(12.dp),
                    ) {
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("${decision.accion} · nivel ${decision.nivel}", fontWeight = FontWeight.SemiBold)
                            Text(Format.fechaHora(decision.t), fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        Text(decision.motivo, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        if (decision.veto != null) Text("Vetada: ${decision.veto}", fontSize = 12.sp, color = Palette.Warn)
                        if (open) {
                            if (decision.evidencia.isNotEmpty()) Text("Evidencia: ${decision.evidencia.joinToString(" · ")}", fontSize = 12.sp)
                            Text(decision.json, fontFamily = FontFamily.Monospace, fontSize = 11.sp, modifier = Modifier.padding(top = 6.dp))
                        }
                    }
                }
            }
        }
        InfoCard("Libros A/B/C", subtitle = "Regla pura, regla + veto de Claude y placebo de vetos al azar", origin = data.origen) {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                data.libros.forEach { libro ->
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(libro.libro, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.weight(1f))
                        Text("${libro.operaciones} operaciones · ${libro.esperanzaR?.let { Format.r(it) } ?: "—"}", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }
    }
}
