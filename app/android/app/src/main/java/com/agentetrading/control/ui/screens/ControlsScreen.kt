package com.agentetrading.control.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.unit.dp
import com.agentetrading.control.ui.components.LabeledValue
import com.agentetrading.control.ui.components.Note
import com.agentetrading.control.ui.components.SectionCard

// Asimetría de seguridad (ADR-010): apagar es fácil, encender es difícil. Los controles se
// habilitan cuando exista el backend con autenticación (F6); hasta entonces están desactivados.

@Composable
fun ControlsScreen() {
    LazyColumn(contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            SectionCard("Kill switch") {
                Note("Bloquea nuevas entradas y cierra todas las posiciones. Requiere biometría.")
                Button(
                    onClick = {},
                    enabled = false,
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error),
                ) { Text("Activar kill switch") }
            }
        }
        item {
            SectionCard("Señales pendientes (nivel B)") {
                Note("No hay señales pendientes.")
                OutlinedButton(onClick = {}, enabled = false) { Text("Rechazar") }
                Button(onClick = {}, enabled = false) { Text("Aprobar (biometría + TOTP)") }
            }
        }
        item {
            SectionCard("Nivel A") {
                LabeledValue("Autoejecución de setups certificados", "Apagada")
                Switch(checked = false, onCheckedChange = null, enabled = false)
                Note("Encenderlo exige biometría + TOTP y setups certificados (ADR-006).")
            }
        }
        item {
            SectionCard("No disponible desde la app") {
                Note("Activar LIVE_TRADING: solo por CLI local con TOTP y commit firmado (regla 2).")
                Note("Cambiar límites de riesgo: solo mediante un ADR aprobado (regla 4).")
            }
        }
    }
}
