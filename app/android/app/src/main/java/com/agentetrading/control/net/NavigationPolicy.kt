package com.agentetrading.control.net

import java.net.URI
import java.net.URISyntaxException

/** Qué hacer cuando la página pide ir a otra dirección. El WebView nunca sale del servidor propio. */
object NavigationPolicy {
    enum class Decision {
        /** Misma dirección que el Centro de Mando: se queda en la app. */
        STAY,

        /** Enlace interno `brujula://ajustes`: abre los ajustes nativos. */
        SETTINGS,

        /** Otro sitio https: se abre en el navegador, no dentro de la app. */
        EXTERNAL,

        /** Cualquier otra cosa (http ajeno, file:, intent:, javascript:, data:…). */
        BLOCK,
    }

    const val SETTINGS_LINK = "brujula://ajustes"

    fun decide(base: String, target: String): Decision {
        if (target == SETTINGS_LINK) return Decision.SETTINGS
        val to = parse(target) ?: return Decision.BLOCK
        val from = parse(base) ?: return Decision.BLOCK
        return when {
            to.scheme == from.scheme && to.host == from.host && to.port == from.port -> Decision.STAY
            to.scheme == "https" -> Decision.EXTERNAL
            else -> Decision.BLOCK
        }
    }

    private data class Origin(val scheme: String, val host: String, val port: Int)

    private fun parse(text: String): Origin? =
        try {
            val uri = URI(text)
            val scheme = uri.scheme?.lowercase()
            val host = uri.host?.lowercase()
            if ((scheme != "http" && scheme != "https") || host == null) {
                null
            } else {
                Origin(scheme, host, if (uri.port != -1) uri.port else if (scheme == "https") 443 else 80)
            }
        } catch (_: URISyntaxException) {
            null
        }
}
