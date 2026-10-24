package com.agentetrading.control.ui

import android.webkit.CookieManager
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
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

private enum class Tab(val label: String, val icon: ImageVector) {
    HOY("Hoy", Icons.Filled.Home),
    EN_VIVO("En vivo", Icons.Filled.Favorite),
    LABORATORIO("Laboratorio", Icons.Filled.Build),
    RIESGO("Riesgo", Icons.Filled.Lock),
    MAS("Más", Icons.Filled.Menu),
}

/** Páginas que todavía se muestran con la web dentro de la app, mientras se pasan a nativo. */
private val MORE_PAGES = listOf(
    "Mercado" to "/mercado",
    "Decisiones" to "/decisiones",
    "Diario" to "/diario",
    "Proyecto" to "/proyecto",
    "Reportes" to "/reportes",
    "Ajustes" to "/ajustes",
)

/**
 * Pestañas de la app. Hoy y En vivo son nativas; el resto se muestra con el mismo Centro de
 * Mando web y pasará a nativo página por página (ADR-018).
 */
@Composable
fun AppShell(baseUrl: String, lifecycle: Lifecycle, onOpenSettings: () -> Unit) {
    val client = remember(baseUrl) { ApiClient(baseUrl) }
    var tab by rememberSaveable { mutableStateOf(Tab.HOY) }
    var morePath by rememberSaveable { mutableStateOf("/mercado") }
    var moreOpen by remember { mutableStateOf(false) }
    var needsLogin by remember(baseUrl) { mutableStateOf(false) }
    var reload by remember(baseUrl) { mutableIntStateOf(0) }
    val resumed = rememberResumed(lifecycle)
    val now = rememberNow()

    val hoy =
        rememberPolled(client, "/api/hoy", 30_000, resumed && tab == Tab.HOY && !needsLogin, reload, { needsLogin = true }, Parsers::hoy)
    val vivo =
        rememberPolled(client, "/api/en-vivo", 5_000, resumed && tab == Tab.EN_VIVO && !needsLogin, reload, { needsLogin = true }, Parsers::enVivo)

    BackHandler(enabled = tab != Tab.HOY && !needsLogin) { tab = Tab.HOY }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        contentWindowInsets = WindowInsets(0, 0, 0, 0),
        bottomBar = {
            NavigationBar(containerColor = MaterialTheme.colorScheme.surface, windowInsets = WindowInsets(0, 0, 0, 0)) {
                Tab.entries.forEach { entry ->
                    NavigationBarItem(
                        selected = tab == entry,
                        onClick = { if (entry == Tab.MAS) moreOpen = true else tab = entry },
                        icon = { Icon(entry.icon, contentDescription = null) },
                        label = { Text(entry.label) },
                    )
                }
            }
        },
    ) { padding ->
        Box(modifier = Modifier.padding(padding).fillMaxSize()) {
            when {
                needsLogin ->
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
                tab == Tab.HOY -> HoyScreen(hoy) { reload++ }
                tab == Tab.EN_VIVO -> EnVivoScreen(vivo, now) { reload++ }
                tab == Tab.LABORATORIO -> WebScreen(baseUrl, lifecycle, "/laboratorio", onOpenSettings)
                tab == Tab.RIESGO -> WebScreen(baseUrl, lifecycle, "/riesgo", onOpenSettings)
                else -> WebScreen(baseUrl, lifecycle, morePath, onOpenSettings)
            }
        }
    }

    if (moreOpen) {
        Dialog(onDismissRequest = { moreOpen = false }) {
            Card(shape = RoundedCornerShape(24.dp), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                Column(modifier = Modifier.padding(8.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    Text("Más secciones", style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(16.dp))
                    MORE_PAGES.forEach { (label, path) ->
                        Text(
                            label,
                            style = MaterialTheme.typography.bodyLarge,
                            modifier =
                                Modifier
                                    .fillMaxWidth()
                                    .clickable {
                                        morePath = path
                                        tab = Tab.MAS
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
