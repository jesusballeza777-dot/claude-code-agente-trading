package com.agentetrading.control.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.draw.clip
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentetrading.control.Format
import com.agentetrading.control.model.PageParsers
import com.agentetrading.control.model.TipoReporte
import com.agentetrading.control.net.LocalSource

private val MIME =
    mapOf(
        "pdf" to "application/pdf",
        "xlsx" to "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "csv" to "text/csv",
        "json" to "application/json",
        "parquet" to "application/octet-stream",
    )

/** Reportes: se generan al descargarlos y quedan en la carpeta Descargas del teléfono. */
@Composable
fun ReportesScreen(env: Env) {
    val polled = env.poll("/api/reportes", 60_000, PageParsers::reportes)
    val context = LocalContext.current
    Page("Reportes", "PDF, Excel y CSV listos para ti y para tu contador. Se generan al descargarlos.", polled, env.refresh) { data ->
        if (env.local) {
            Text(
                LocalSource.NEEDS_REPORTS,
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp)).background(Palette.DemoSoft).padding(14.dp),
            )
        }
        val grupos: Map<String, List<TipoReporte>> = data.tipos.groupBy { it.tipo }
        grupos.forEach { (_, formatos) ->
            InfoCard(formatos.first().nombre, origin = data.origen) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    formatos.forEach { tipo ->
                        OutlinedButton(
                            enabled = !env.local,
                            onClick = {
                                downloadFile(context, "${env.baseUrl}/api/reportes/${tipo.tipo}/${tipo.formato}", "${tipo.tipo}.${tipo.formato}", MIME[tipo.formato])
                                env.refresh()
                            },
                        ) { Text(tipo.formato.uppercase()) }
                    }
                }
            }
        }
        InfoCard("Historial", subtitle = "Lo que has generado en este servidor") {
            if (data.historial.isEmpty()) {
                Text("Aún no has generado ningún reporte.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            } else {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    data.historial.take(20).forEach { item ->
                        Column(modifier = Modifier.fillMaxWidth()) {
                            Text(item.archivo, fontSize = 13.sp, fontWeight = FontWeight.Medium)
                            Text(
                                Format.fechaHora(item.fechaUtc) + if (item.demo) " · con datos de demostración" else "",
                                fontSize = 11.sp,
                                color = if (item.demo) Palette.Demo else MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                }
            }
        }
    }
}
