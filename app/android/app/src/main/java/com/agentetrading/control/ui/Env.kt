package com.agentetrading.control.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.agentetrading.control.net.ApiClient
import org.json.JSONObject

/** Lo que cada pantalla necesita de la app: el cliente, si está al frente y cómo pedir sesión o refrescar. */
class Env(
    val client: ApiClient,
    val baseUrl: String,
    val active: Boolean,
    val reload: Int,
    val onNeedsLogin: () -> Unit,
    val refresh: () -> Unit,
    val onOpenSettings: () -> Unit,
    val onOpenWeb: () -> Unit = {},
)

@Composable
fun <T> Env.poll(path: String, intervalMs: Long = 60_000, parse: (JSONObject) -> T): Polled<T> =
    rememberPolled(client, path, intervalMs, active, reload, onNeedsLogin, parse)

/** Estructura común de una página: título, actualizar y los tres estados (cargando, error, con datos). */
@Composable
fun <T> Page(
    title: String,
    subtitle: String?,
    polled: Polled<T>,
    onRefresh: () -> Unit,
    header: @Composable ColumnScope.() -> Unit = {},
    content: @Composable ColumnScope.(T) -> Unit,
) {
    val data = polled.data
    Column(
        modifier = Modifier.verticalScroll(rememberScrollState()).padding(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(modifier = Modifier.weight(1f)) {
                Text(title, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
                if (subtitle != null) {
                    Text(subtitle, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
            IconButton(onClick = onRefresh) { Icon(Icons.Filled.Refresh, contentDescription = "Actualizar") }
        }
        this.header()
        when {
            data == null && polled.error != null -> ErrorBox(polled.error, onRefresh)
            data == null -> LoadingBox()
            else -> {
                if (polled.error != null) OfflineBanner(polled.error)
                this.content(data)
            }
        }
    }
}
