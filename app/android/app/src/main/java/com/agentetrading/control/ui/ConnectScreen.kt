package com.agentetrading.control.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.agentetrading.control.R
import com.agentetrading.control.net.Reachability
import com.agentetrading.control.net.ServerUrl
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private sealed interface Probe {
    data object Idle : Probe

    data object Testing : Probe

    /** `url` no es nulo cuando la dirección era válida pero el servidor no respondió. */
    data class Failed(val message: String, val url: String?) : Probe
}

/** Servidor y seguridad: primera conexión y ajustes de la app. */
@Composable
fun ConnectScreen(
    initialUrl: String,
    lockEnabled: Boolean,
    secureScreen: Boolean,
    lockAvailable: Boolean,
    canClose: Boolean,
    onSaved: (String) -> Unit,
    onLockChange: (Boolean) -> Unit,
    onSecureChange: (Boolean) -> Unit,
    onClose: () -> Unit,
) {
    var text by remember { mutableStateOf(initialUrl) }
    var probe by remember { mutableStateOf<Probe>(Probe.Idle) }
    val scope = rememberCoroutineScope()

    fun connect() {
        when (val parsed = ServerUrl.parse(text)) {
            is ServerUrl.Result.Invalid -> probe = Probe.Failed(parsed.reason, null)
            is ServerUrl.Result.Ok -> {
                probe = Probe.Testing
                scope.launch {
                    val outcome = withContext(Dispatchers.IO) { Reachability.check(parsed.url) }
                    probe =
                        when (outcome) {
                            is Reachability.Outcome.Found -> {
                                onSaved(parsed.url)
                                Probe.Idle
                            }
                            is Reachability.Outcome.Failed -> Probe.Failed(outcome.message, parsed.url)
                        }
                }
            }
        }
    }

    Column(
        modifier = Modifier.imePadding().verticalScroll(rememberScrollState()).padding(horizontal = 20.dp, vertical = 16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Image(painterResource(R.drawable.ic_launcher_foreground), contentDescription = null, modifier = Modifier.size(72.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text("Brújula", style = MaterialTheme.typography.headlineMedium)
                Text(
                    "Centro de Mando del agente de trading",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            if (canClose) TextButton(onClick = onClose) { Text("Volver") }
        }

        Panel("Servidor") {
            Text(
                "Dirección de tu Centro de Mando. La app solo muestra datos: no envía órdenes ni guarda claves de exchanges.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(8.dp))
            OutlinedTextField(
                value = text,
                onValueChange = {
                    text = it
                    probe = Probe.Idle
                },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Dirección del servidor") },
                placeholder = { Text("https://mi-servidor.ts.net") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
            )
            Spacer(Modifier.height(8.dp))
            Button(onClick = { connect() }, enabled = probe != Probe.Testing, modifier = Modifier.fillMaxWidth()) {
                if (probe == Probe.Testing) {
                    CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                    Spacer(Modifier.size(8.dp))
                    Text("Comprobando…")
                } else {
                    Text("Conectar")
                }
            }
            (probe as? Probe.Failed)?.let { failed ->
                Text(failed.message, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodyMedium)
                failed.url?.let { url ->
                    TextButton(onClick = { onSaved(url) }) { Text("Guardar de todos modos") }
                }
            }
        }

        Panel("Seguridad") {
            ToggleRow(
                title = "Bloqueo con huella, rostro o PIN",
                detail = if (lockAvailable) "Se pide al abrir y al volver tras un minuto fuera." else "Este teléfono no tiene bloqueo de pantalla: configura uno para proteger la app.",
                checked = lockEnabled,
                enabled = lockAvailable,
                onChange = onLockChange,
            )
            ToggleRow(
                title = "Ocultar en apps recientes y capturas",
                detail = "Evita que se vea el contenido al cambiar de app o al capturar la pantalla.",
                checked = secureScreen,
                onChange = onSecureChange,
            )
        }

        Panel("Cómo conectar") {
            Step("Por cable USB (sin red)", "En tu computadora: adb reverse tcp:8080 tcp:8080. Dirección: 127.0.0.1:8080")
            Step("Desde cualquier lugar", "Tailscale en el servidor y en este teléfono. Dirección: https://tu-servidor.tu-red.ts.net")
            Text(
                "Nunca publiques el Centro de Mando en internet abierto.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.secondary,
            )
        }
    }
}

@Composable
private fun Panel(title: String, content: @Composable () -> Unit) {
    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary)
            content()
        }
    }
}

@Composable
private fun Step(title: String, detail: String) {
    Column(modifier = Modifier.padding(vertical = 4.dp)) {
        Text(title, style = MaterialTheme.typography.bodyLarge)
        Text(detail, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun ToggleRow(title: String, detail: String, checked: Boolean, enabled: Boolean = true, onChange: (Boolean) -> Unit) {
    Row(
        modifier =
            Modifier
                .fillMaxWidth()
                .toggleable(value = checked, enabled = enabled, role = Role.Switch, onValueChange = onChange)
                .padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.bodyLarge)
            Text(detail, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Switch(checked = checked && enabled, onCheckedChange = null, enabled = enabled)
    }
}
