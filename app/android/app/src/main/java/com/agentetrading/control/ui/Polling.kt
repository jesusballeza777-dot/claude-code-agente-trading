package com.agentetrading.control.ui

import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import com.agentetrading.control.net.ApiClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import org.json.JSONException
import org.json.JSONObject

/** Último dato recibido. Si el servidor deja de responder se conserva el dato y se añade el error. */
data class Polled<T>(
    val data: T? = null,
    val error: String? = null,
    val loading: Boolean = true,
    val updatedAtMs: Long = 0L,
)

/**
 * Pide `path` cada `intervalMs` mientras la app está al frente (`active`) y avisa si hay que
 * iniciar sesión. `reload` fuerza una lectura inmediata.
 */
@Composable
fun <T> rememberPolled(
    client: ApiClient,
    path: String,
    intervalMs: Long,
    active: Boolean,
    reload: Int,
    onNeedsLogin: () -> Unit,
    parse: (JSONObject) -> T,
): Polled<T> {
    var state by remember(client, path) { mutableStateOf(Polled<T>()) }
    val currentParse by rememberUpdatedState(parse)
    val currentNeedsLogin by rememberUpdatedState(onNeedsLogin)
    LaunchedEffect(client, path, active, reload) {
        if (!active) return@LaunchedEffect
        while (true) {
            when (val result = withContext(Dispatchers.IO) { client.get(path) }) {
                is ApiClient.Result.Ok ->
                    state =
                        try {
                            Polled(currentParse(result.json), null, false, System.currentTimeMillis())
                        } catch (_: JSONException) {
                            state.copy(error = "Respuesta inesperada del servidor.", loading = false)
                        }
                is ApiClient.Result.NeedsLogin -> {
                    currentNeedsLogin()
                    return@LaunchedEffect
                }
                is ApiClient.Result.Failed -> state = state.copy(error = result.message, loading = false)
            }
            delay(intervalMs)
        }
    }
    return state
}

/** Verdadero mientras la app está al frente: en segundo plano no se sondea (ahorra batería y datos). */
@Composable
fun rememberResumed(lifecycle: Lifecycle): Boolean {
    var resumed by remember(lifecycle) { mutableStateOf(lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)) }
    DisposableEffect(lifecycle) {
        val observer =
            LifecycleEventObserver { _, event ->
                if (event == Lifecycle.Event.ON_RESUME) resumed = true
                if (event == Lifecycle.Event.ON_PAUSE) resumed = false
            }
        lifecycle.addObserver(observer)
        onDispose { lifecycle.removeObserver(observer) }
    }
    return resumed
}

/** Reloj de un segundo para los "actualizado hace…". */
@Composable
fun rememberNow(): Long {
    var now by remember { mutableStateOf(System.currentTimeMillis()) }
    LaunchedEffect(Unit) {
        while (true) {
            delay(1_000)
            now = System.currentTimeMillis()
        }
    }
    return now
}
