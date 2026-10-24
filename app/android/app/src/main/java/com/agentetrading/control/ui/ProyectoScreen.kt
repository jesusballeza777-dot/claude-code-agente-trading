package com.agentetrading.control.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentetrading.control.model.PageParsers
import com.agentetrading.control.model.Proyecto
import com.agentetrading.control.model.RiskMatrix

/** Proyecto: hoja de ruta, pendientes tuyos, matriz de riesgos, costes y decisiones de arquitectura. */
@Composable
fun ProyectoScreen(env: Env) {
    val polled = env.poll("/api/proyecto", 120_000, PageParsers::proyecto)
    Page("Proyecto", "Roadmap, decisiones de arquitectura, riesgos y costes, leídos de los documentos del repositorio.", polled, env.refresh) { data ->
        InfoCard("Roadmap F0-F9", origin = data.origen) {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                data.fases.forEach { fase ->
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("${fase.id} ${fase.nombre}", style = MaterialTheme.typography.bodyMedium, modifier = Modifier.weight(1f))
                        Text(fase.estado, fontSize = 12.sp, fontWeight = FontWeight.Medium, color = faseColor(fase.estado))
                    }
                }
            }
        }
        InfoCard("Tus pendientes", subtitle = "En orden. Ninguno se puede hacer desde la app.") {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                data.pendientes.forEachIndexed { index, item ->
                    Column {
                        Text("${index + 1}. ${item.tarea}", style = MaterialTheme.typography.bodyMedium)
                        Text(item.documento, fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }
        MatrizCard(data)
        InfoCard("Costes", subtitle = "Tipo de cambio: ${data.mxnPorUsd} MXN/USD (${data.estadoTipoCambio})") {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                data.costes.forEach { costo ->
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(costo.concepto, style = MaterialTheme.typography.bodyMedium)
                            Text(costo.estado, fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        Text("USD ${costo.usdMes}", fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
                    }
                }
                Text("${data.usoApiNota}", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        InfoCard("Decisiones de arquitectura (ADR)") {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                data.adr.forEach { adr ->
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(adr.id, fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
                        Text(adr.titulo, fontSize = 13.sp, modifier = Modifier.weight(1f))
                        Text(adr.estado, fontSize = 11.sp, color = if (adr.estado.startsWith("Propuesto")) Palette.Warn else MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }
    }
}

@Composable
private fun faseColor(estado: String): Color =
    when {
        estado.startsWith("cerrada") || estado.startsWith("hecha") -> Palette.Gain
        estado.startsWith("pendiente") -> Palette.Warn
        estado.startsWith("en curso") -> MaterialTheme.colorScheme.primary
        else -> Palette.Neutral
    }

@Composable
private fun MatrizCard(data: Proyecto) {
    val matrix = RiskMatrix.build(data.riesgos)
    val impact = listOf("bajo", "medio", "alto")
    val probability = listOf("alta", "media", "baja")
    InfoCard("Matriz de riesgos", subtitle = "Probabilidad × impacto (docs/risk_register.md)") {
        Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            Box(modifier = Modifier.weight(0.5f))
            impact.forEach { Text("Impacto $it", fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.weight(1f)) }
        }
        matrix.cells.forEachIndexed { row, cells ->
            Row(horizontalArrangement = Arrangement.spacedBy(4.dp), verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                Text("Prob. ${probability[row]}", fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.weight(0.5f))
                cells.forEachIndexed { column, risks ->
                    val severity = (2 - row) + column
                    Column(
                        modifier =
                            Modifier
                                .weight(1f)
                                .heightIn(min = 56.dp)
                                .clip(RoundedCornerShape(10.dp))
                                .background(Palette.Loss.copy(alpha = 0.06f + severity * 0.07f))
                                .padding(6.dp),
                    ) {
                        Text(risks.joinToString(" ") { it.id }, fontSize = 10.sp)
                    }
                }
            }
        }
        if (matrix.outside.isNotEmpty()) {
            Text(
                "Fuera de la matriz: ${matrix.outside.joinToString(", ") { "${it.id} (${it.probabilidad.lowercase()})" }}.",
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 4.dp),
            )
        }
    }
}
