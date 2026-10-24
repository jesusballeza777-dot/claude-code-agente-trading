package com.agentetrading.control.ui

import android.webkit.CookieManager
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.platform.LocalContext
import com.agentetrading.control.Format
import com.agentetrading.control.PrefsNoteStore
import com.agentetrading.control.net.DataSource
import com.agentetrading.control.net.LocalSource
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.lifecycle.Lifecycle
import com.agentetrading.control.model.Parsers
import com.agentetrading.control.net.ApiClient

/** Todas las páginas de la app. */
private enum class Destination(val label: String) {
    HOY("Hoy"),
    EN_VIVO("En vivo"),
    LABORATORIO("Laboratorio"),
    RIESGO("Riesgo"),
    MERCADO("Mercado"),
    DECISIONES("Decisiones"),
    DIARIO("Diario"),
    PROYECTO("Proyecto"),
    REPORTES("Reportes"),
    AJUSTES("Ajustes"),

    /** El Centro de Mando web completo dentro de la app: una salida para lo que aún no sea nativo. */
    WEB("Centro de Mando web"),
    ;
}

private class BarItem(val label: String, val icon: ImageVector, val destination: Destination?)

private val BAR =
    listOf(
        BarItem("Hoy", Icons.Filled.Home, Destination.HOY),
        BarItem("En vivo", Icons.Filled.Favorite, Destination.EN_VIVO),
        BarItem("Laboratorio", Icons.Filled.Build, Destination.LABORATORIO),
        BarItem("Riesgo", Icons.Filled.Lock, Destination.RIESGO),
        BarItem("Más", Icons.Filled.Menu, null),
    )

private val MORE = listOf(Destination.MERCADO, Destination.DECISIONES, Destination.DIARIO, Destination.PROYECTO, Destination.REPORTES, Destination.AJUSTES)

/**
 * Pestañas de la app: todas las páginas del Centro de Mando son nativas (ADR-018). La web completa
 * queda como salida opcional desde Ajustes.
 */
@Composable
fun AppShell(baseUrl: String?, lifecycle: Lifecycle, onOpenSettings: () -> Unit) {
    val context = LocalContext.current
    val local = baseUrl == null
    // Con servidor: el cliente HTTP. Sin servidor: la instantánea que lleva la app y las notas del teléfono.
    val source: DataSource =
        remember(baseUrl) { if (baseUrl != null) ApiClient(baseUrl) else LocalSource({ readSnapshot(context, it) }, PrefsNoteStore(context)) }
    val client = source as? ApiClient
    var destination by rememberSaveable { mutableStateOf(Destination.HOY) }
    var moreOpen by remember { mutableStateOf(false) }
    var needsLogin by remember(baseUrl) { mutableStateOf(false) }
    val manifest = (source as? LocalSource)?.manifest()
    var reload by remember(baseUrl) { mutableIntStateOf(0) }
    val resumed = rememberResumed(lifecycle)
    val now = rememberNow()

    val hoy = rememberPolled(source, "/api/hoy", 30_000, resumed && destination == Destination.HOY && !needsLogin, reload, { needsLogin = true }, Parsers::hoy)
    val vivo = rememberPolled(source, "/api/en-vivo", 5_000, resumed && destination == Destination.EN_VIVO && !needsLogin, reload, { needsLogin = true }, Parsers::enVivo)
    val env =
        Env(source, baseUrl.orEmpty(), resumed && !needsLogin, reload, { needsLogin = true }, { reload++ }, onOpenSettings, { destination = Destination.WEB }, local)

    BackHandler(enabled = destination != Destination.HOY && !needsLogin) { destination = Destination.HOY }

    CompositionLocalProvider(LocalOpenSettings provides onOpenSettings) {
        Scaffold(
            containerColor = MaterialTheme.colorScheme.background,
            contentWindowInsets = WindowInsets(0, 0, 0, 0),
            bottomBar = {
                NavigationBar(containerColor = MaterialTheme.colorScheme.surface, windowInsets = WindowInsets(0, 0, 0, 0)) {
                    BAR.forEach { item ->
                        NavigationBarItem(
                            selected = if (item.destination == null) destination in MORE else destination == item.destination,
                            onClick = { if (item.destination == null) moreOpen = true else destination = item.destination },
                            icon = { Icon(item.icon, contentDescription = null) },
                            label = { Text(item.label) },
                        )
                    }
                }
            },
        ) { padding ->
            Column(modifier = Modifier.padding(padding).fillMaxSize()) {
                if (local) {
                    LocalBanner(
                        if (manifest != null) {
                            "Modo sin servidor · datos incluidos en la app (${Format.fechaHora(manifest.first)}, commit ${manifest.second.take(7)})"
                        } else {
                            "Modo sin servidor · esta compilación no incluye los datos"
                        },
                        onOpenSettings,
                    )
                }
                Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
                    if (needsLogin && client != null && baseUrl != null) {
                        LoginScreen(
                            client = client,
                            onSignedIn = {
                                // La web del WebView y la app comparten la sesión: se entra una sola vez.
                                client.sessionCookie?.let { CookieManager.getInstance().setCookie(baseUrl, "$it; Path=/") }
                                CookieManager.getInstance().flush()
                                needsLogin = false
                                reload++
                            },
                            onOpenSettings = onOpenSettings,
                        )
                    } else {
                        when (destination) {
                            Destination.HOY -> HoyScreen(hoy, local) { reload++ }
                            Destination.EN_VIVO -> EnVivoScreen(vivo, now, local) { reload++ }
                            Destination.LABORATORIO -> LaboratorioScreen(env)
                            Destination.RIESGO -> RiesgoScreen(env)
                            Destination.MERCADO -> MercadoScreen(env)
                            Destination.DECISIONES -> DecisionesScreen(env)
                            Destination.DIARIO -> DiarioScreen(env)
                            Destination.PROYECTO -> ProyectoScreen(env)
                            Destination.REPORTES -> ReportesScreen(env)
                            Destination.AJUSTES -> AjustesScreen(env)
                            // Solo se llega desde Ajustes con un servidor conectado.
                            Destination.WEB -> WebScreen(baseUrl.orEmpty(), lifecycle, "/", onOpenSettings)
                        }
                    }
                }
            }
        }
    }

    if (moreOpen) {
        Dialog(onDismissRequest = { moreOpen = false }) {
            Card(shape = RoundedCornerShape(24.dp), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                Column(modifier = Modifier.verticalScroll(rememberScrollState()).padding(8.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    Text("Más secciones", style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(16.dp))
                    MORE.forEach { target ->
                        Text(
                            target.label,
                            style = MaterialTheme.typography.bodyLarge,
                            modifier =
                                Modifier
                                    .fillMaxWidth()
                                    .clickable {
                                        destination = target
                                        moreOpen = false
                                    }
                                    .padding(horizontal = 16.dp, vertical = 14.dp),
                        )
                    }
                    Text(
                        "Servidor y seguridad",
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.primary,
                        modifier =
                            Modifier
                                .fillMaxWidth()
                                .clickable {
                                    moreOpen = false
                                    onOpenSettings()
                                }
                                .padding(horizontal = 16.dp, vertical = 14.dp),
                    )
                }
            }
        }
    }
}

/** Lee un archivo de la instantánea que la CI empaqueta en el APK (assets/snapshot). */
private fun readSnapshot(context: android.content.Context, name: String): String? =
    try {
        context.assets.open("snapshot/$name").bufferedReader().use { it.readText() }
    } catch (_: java.io.IOException) {
        null
    }
