package com.agentetrading.control.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.agentetrading.control.Format
import com.agentetrading.control.model.Diario
import com.agentetrading.control.model.PageParsers
import com.agentetrading.control.net.ApiClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject

/** Diario: tus notas (la única escritura de la app, no toca riesgo ni ejecución) y las operaciones simuladas. */
@Composable
fun DiarioScreen(env: Env) {
    val polled = env.poll("/api/diario", 60_000, PageParsers::diario)
    Page("Diario", "Tus notas y las operaciones simuladas del backtest.", polled, env.refresh) { data ->
        NotaCard(env)
        NotasCard(data)
        OperacionesCard(data)
    }
}

@Composable
private fun NotaCard(env: Env) {
    var reference by remember { mutableStateOf("") }
    var text by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf<Pair<Boolean, String>?>(null) }
    val scope = rememberCoroutineScope()

    fun save() {
        busy = true
        message = null
        scope.launch {
            val body = JSONObject().put("referencia", reference.trim()).put("texto", text.trim())
            when (val result = withContext(Dispatchers.IO) { env.client.post("/api/diario/notas", body) }) {
                is ApiClient.Result.Ok -> {
                    text = ""
                    message = true to "Nota guardada."
                    env.refresh()
                }
                is ApiClient.Result.NeedsLogin -> env.onNeedsLogin()
                is ApiClient.Result.Failed -> message = false to result.message
                is ApiClient.Result.NeedsServer -> message = false to result.message
            }
            busy = false
        }
    }

    InfoCard("Nueva nota", subtitle = "Se guarda en tu servidor. No cambia ningún límite ni orden.") {
        OutlinedTextField(reference, { reference = it }, Modifier.fillMaxWidth(), label = { Text("Referencia (opcional, por ejemplo H2-v1)") }, singleLine = true)
        OutlinedTextField(text, { text = it }, Modifier.fillMaxWidth(), label = { Text("Nota") }, minLines = 3)
        Button(onClick = { save() }, enabled = !busy && text.isNotBlank(), modifier = Modifier.fillMaxWidth()) { Text(if (busy) "Guardando…" else "Guardar nota") }
        message?.let { (ok, note) -> Text(note, color = if (ok) Palette.Gain else MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodyMedium) }
    }
}

@Composable
private fun NotasCard(data: Diario) {
    InfoCard("Notas", subtitle = "${data.notas.size} guardadas") {
        if (data.notas.isEmpty()) {
            Text(data.vacio, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        } else {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                data.notas.asReversed().forEach { nota ->
                    Column {
                        Text(nota.texto, style = MaterialTheme.typography.bodyMedium)
                        Text(
                            Format.fechaHora(nota.fechaUtc) + if (nota.referencia.isNotEmpty()) " · ${nota.referencia}" else "",
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
        }
    }
}

private const val MAX_TRADES = 30

@Composable
private fun OperacionesCard(data: Diario) {
    InfoCard("Operaciones simuladas", subtitle = data.aviso, origin = data.origen) {
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            data.operaciones.take(MAX_TRADES).forEach { op ->
                Column {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("${op.id} · ${op.lado} ${op.simbolo}", fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
                        Text(Format.r(op.r), fontWeight = FontWeight.SemiBold, color = if (op.r >= 0) Palette.Gain else Palette.Loss)
                    }
                    Text(
                        "${Format.fechaHora(op.entrada)} · ${Format.price(op.precioEntrada)} → ${Format.price(op.precioSalida)} (${op.motivoSalida}) · ${op.regimen}",
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
            if (data.operaciones.size > MAX_TRADES) {
                Text("Mostrando $MAX_TRADES de ${data.operaciones.size}.", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}
