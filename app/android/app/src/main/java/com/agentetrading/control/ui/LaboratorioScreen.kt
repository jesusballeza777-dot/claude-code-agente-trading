package com.agentetrading.control.ui

import androidx.activity.compose.BackHandler
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
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentetrading.control.Format
import com.agentetrading.control.model.Criterios
import com.agentetrading.control.model.DetalleLab
import com.agentetrading.control.model.GateLab
import com.agentetrading.control.model.HipotesisLab
import com.agentetrading.control.model.LabParsers
import com.agentetrading.control.model.LabVerdict
import com.agentetrading.control.model.Origen
import com.agentetrading.control.model.ResumenLab
import com.agentetrading.control.model.Segmento

/** Laboratorio: cada hipótesis se escribió y congeló antes de ver datos; aquí está su examen completo. */
@Composable
fun LaboratorioScreen(env: Env) {
    var selected by rememberSaveable { mutableStateOf<String?>(null) }
    BackHandler(enabled = selected != null) { selected = null }
    val id = selected
    if (id == null) LabList(env) { selected = it } else LabDetail(env, id) { selected = null }
}

@Composable
private fun LabList(env: Env, onOpen: (String) -> Unit) {
    val polled = env.poll("/api/laboratorio", 120_000, LabParsers::laboratorio)
    Page(
        "Laboratorio de estrategias",
        "Cada hipótesis se escribió y congeló antes de ver datos. Aquí ves su examen completo, con costes y con su incertidumbre.",
        polled,
        env.refresh,
    ) { lab ->
        Text(
            LabVerdict.text(lab.hipotesis),
            style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp)).background(Palette.AccentSoft).padding(14.dp),
        )
        Text(
            "Intentos: ${lab.intentosPrincipales} principales · ${lab.intentosTotal} corridas. ${lab.explicacionIntentos}",
            fontSize = 12.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        lab.hipotesis.forEach { HipotesisCard(it, lab.origen) { if (it.evaluada) onOpen(it.id) } }
    }
}

@Composable
private fun HipotesisCard(h: HipotesisLab, origen: Origen, onClick: () -> Unit) {
    InfoCard(
        title = "${h.id} · ${h.titulo}",
        modifier = if (h.evaluada) Modifier.clickable(onClick = onClick) else Modifier,
        origin = if (h.evaluada) origen else null,
    ) {
        Text(h.ciclo.joinToString(" · ") { "${it.etapa}: ${it.estado}" }, fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
        h.resumen?.let { r ->
            Text("${r.operaciones} operaciones · ${Format.r(r.esperanzaR)} por operación", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
        }
        h.gate?.let { g ->
            Text(
                (if (g.pasa) "Pasa los criterios 1-8" else "No pasa el gate") + " · ${g.cumplidos} de ${g.criterios.size} criterios",
                fontSize = 13.sp,
                color = if (g.pasa) Palette.Gain else Palette.Loss,
            )
        }
        h.pista?.let { Text(it, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant) }
        if (h.evaluada) Text("Toca para ver el detalle", fontSize = 11.sp, color = MaterialTheme.colorScheme.primary)
    }
}

@Composable
private fun LabDetail(env: Env, id: String, onBack: () -> Unit) {
    val polled = env.poll("/api/laboratorio/$id", 120_000, LabParsers::detalle)
    Page("Detalle de $id", polled.data?.titulo, polled, env.refresh, header = { TextButton(onClick = onBack) { Text("← Volver al laboratorio") } }) { d ->
        ResumenCard(d)
        d.gate?.let { GateCard(it) }
        InfoCard("Curva de capital neta", subtitle = "${d.curva.firstOrNull()?.t.orEmpty()} → ${d.curva.lastOrNull()?.t.orEmpty()}", origin = d.origen) {
            Sparkline(d.curva.map { it.capital })
            Text(
                "De USD ${Format.price(d.curva.minOfOrNull { it.capital }?.toString(), prefix = false)} a USD ${Format.price(d.curva.maxOfOrNull { it.capital }?.toString(), prefix = false)}",
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        InfoCard("Drawdown desde el máximo", subtitle = "Cuánto se cae desde el mejor punto. El mínimo es la peor racha.") {
            DrawdownArea(d.underwater.map { it.dd })
            Text("Peor caída: ${Format.pct(d.underwater.minOfOrNull { it.dd } ?: 0.0, 1)}", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        InfoCard("Distribución de resultados", subtitle = "Cuántas operaciones cayeron en cada tramo de R. Verde: ganó. Rojo: perdió.") {
            Histogram(d.distribucion)
            Text(
                "De ${Format.decimal(d.distribucion.minOfOrNull { it.desde } ?: 0.0, 2)} R a ${Format.decimal(d.distribucion.maxOfOrNull { it.hasta } ?: 0.0, 2)} R",
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        InfoCard("Abanico de Monte Carlo", subtitle = "Capital relativo (1.0 = inicial) en 90% y 50% de los órdenes posibles de las mismas operaciones.") {
            FanChart(d.abanico)
        }
        InfoCard("Mapa mensual", subtitle = "Suma de R por mes de salida") { MonthHeatmap(d.mapaMensual) }
        SensibilidadCard(d)
        SegmentosCard("Dirección", d.resumen.porDireccion)
        SegmentosCard("Régimen de mercado", d.resumen.porRegimen)
        SegmentosCard("Semestre", d.resumen.porSemestre)
        if (d.vetos.isNotEmpty()) {
            InfoCard("Vetos del motor de riesgo", subtitle = "Señales que el motor no dejó pasar, y por qué.") {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    d.vetos.forEach { veto ->
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
        Text(
            "Corrida ${d.trialId} · parámetros ${d.parametros.joinToString(" ") { "${it.first}=${it.second}" }} · código ${d.codigoCommit.take(7)} · dataset ${d.datasetId.take(7)}",
            fontSize = 11.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun ResumenCard(d: DetalleLab) {
    val r: ResumenLab = d.resumen
    InfoCard("Detalle de ${d.id}", subtitle = d.titulo, origin = d.origen) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            BigStat("Operaciones", "${r.operaciones}", Modifier.weight(1f))
            BigStat("Esperanza neta", Format.r(r.esperanzaR), Modifier.weight(1.2f), if (r.esperanzaR > 0) Palette.Gain else Palette.Loss)
        }
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            BigStat("Profit factor", r.pf?.let { Format.decimal(it, 2) } ?: "—", Modifier.weight(1f))
            BigStat("Acierto", Format.pct(r.tasaAcierto, 1), Modifier.weight(1.2f))
        }
        Text(
            "IC90% de la esperanza: [${Format.r(r.ic90Inferior)}, ${Format.r(r.ic90Superior)}]. Con stops, ganar menos de la mitad de las veces puede ser rentable.",
            fontSize = 12.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun GateCard(gate: GateLab) {
    InfoCard("Gate de la F4", subtitle = "${gate.cumplidos} de ${gate.criterios.size} criterios · criterio 9 (holdout): sellado") {
        Text(
            if (gate.pasa) "✓ Pasa los criterios 1-8" else "✕ No pasa el gate",
            color = if (gate.pasa) Palette.Gain else Palette.Loss,
            fontWeight = FontWeight.Bold,
        )
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            gate.criterios.forEach { criterio ->
                val texto = Criterios.texto(criterio.clave)
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(if (criterio.cumple) "✓" else "✕", color = if (criterio.cumple) Palette.Gain else Palette.Loss, fontWeight = FontWeight.Bold)
                    Column(modifier = Modifier.weight(1f)) {
                        Text(texto.nombre, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
                        if (texto.explica.isNotEmpty()) Text(texto.explica, fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    Text(Criterios.valor(criterio.clave, gate.valores), fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                }
            }
        }
        gate.holdout?.let { Text(it, fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant) }
    }
}

@Composable
private fun SensibilidadCard(d: DetalleLab) {
    if (d.sensibilidad.isEmpty()) return
    InfoCard("Robustez a ±20% en cada parámetro", subtitle = "Esperanza al mover un parámetro cada vez. El del medio es el valor base.") {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            d.sensibilidad.forEach { fila ->
                Column {
                    Text(fila.parametro, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.fillMaxWidth()) {
                        fila.valores.sortedBy { it.valor }.forEach { v ->
                            Column(
                                modifier =
                                    Modifier
                                        .weight(1f)
                                        .clip(RoundedCornerShape(10.dp))
                                        .background((if (v.esperanzaR > 0) Palette.Gain else Palette.Loss).copy(alpha = 0.12f))
                                        .padding(6.dp),
                            ) {
                                Text(Format.decimal(v.valor, 2).trimEnd('0').trimEnd('.'), fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                Text(Format.r(v.esperanzaR), fontSize = 12.sp, fontWeight = FontWeight.SemiBold, color = if (v.esperanzaR > 0) Palette.Gain else Palette.Loss)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun SegmentosCard(title: String, segmentos: Map<String, Segmento>) {
    if (segmentos.isEmpty()) return
    InfoCard(title) {
        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            segmentos.forEach { (nombre, s) ->
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("$nombre · ${s.n} operaciones", style = MaterialTheme.typography.bodyMedium)
                    Text(Format.r(s.esperanzaR), fontWeight = FontWeight.SemiBold, color = if (s.esperanzaR > 0) Palette.Gain else Palette.Loss)
                }
            }
        }
    }
}
