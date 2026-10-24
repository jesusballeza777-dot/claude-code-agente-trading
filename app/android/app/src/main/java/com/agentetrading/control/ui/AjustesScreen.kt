package com.agentetrading.control.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentetrading.control.BuildConfig
import com.agentetrading.control.Format
import com.agentetrading.control.model.PageParsers

/** Ajustes: servidor y seguridad de la app, y los límites de riesgo (se ven, no se editan aquí). */
@Composable
fun AjustesScreen(env: Env) {
    val polled = env.poll("/api/riesgo/limites", 120_000, PageParsers::limites)
    Page("Ajustes", "Preferencias de la app. Los límites de riesgo se ven, pero no se editan aquí.", polled, env.refresh) { data ->
        InfoCard("Esta app") {
            Text(
                if (env.local) "Modo sin servidor: datos incluidos en la app" else "Servidor: ${env.baseUrl}",
                style = MaterialTheme.typography.bodyMedium,
            )
            Text("Versión ${BuildConfig.VERSION_NAME}", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Button(onClick = env.onOpenSettings, modifier = Modifier.fillMaxWidth()) { Text("Servidor, bloqueo y privacidad") }
            if (!env.local) OutlinedButton(onClick = env.onOpenWeb, modifier = Modifier.fillMaxWidth()) { Text("Abrir el Centro de Mando web") }
        }
        InfoCard("Notificaciones", subtitle = "Llegan con la F6 (alertas por Telegram o por la app, sin datos sensibles).") {
            Text("Aún no hay notificaciones que configurar.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        InfoCard("Límites de riesgo (solo lectura)", subtitle = data.aviso, origin = data.origen) {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                data.vigentes.forEach { limite ->
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(limite.nombre, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.weight(1f))
                        Text(
                            if (limite.esFraccion) Format.pct(limite.valor.toDouble()) else "${limite.valor}x",
                            fontWeight = FontWeight.SemiBold,
                        )
                    }
                }
            }
        }
    }
}
