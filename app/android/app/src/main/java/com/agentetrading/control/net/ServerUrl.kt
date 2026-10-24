package com.agentetrading.control.net

import java.net.URI
import java.net.URISyntaxException

/**
 * Dirección del Centro de Mando que escribe el propietario.
 *
 * Reglas (ADR-018): HTTPS siempre; HTTP solo hacia este mismo teléfono (127.0.0.1, localhost),
 * que es lo que da `adb reverse` por USB. Sin usuario ni contraseña en la dirección y sin ruta.
 */
object ServerUrl {
    sealed interface Result {
        data class Ok(val url: String) : Result

        data class Invalid(val reason: String) : Result
    }

    private val SCHEME = Regex("^[a-zA-Z][a-zA-Z0-9+.-]*://")
    private val LOOPBACK = setOf("localhost", "127.0.0.1", "[::1]")

    fun isLoopback(host: String): Boolean = host.lowercase() in LOOPBACK

    private fun startsWithLoopback(text: String): Boolean =
        LOOPBACK.any { text.lowercase().let { t -> t == it || t.startsWith("$it:") || t.startsWith("$it/") } }

    fun parse(input: String): Result {
        val text = input.trim()
        if (text.isEmpty()) return Result.Invalid("Escribe la dirección del servidor.")
        val withScheme =
            when {
                SCHEME.containsMatchIn(text) -> text
                // Sin esquema: http hacia este mismo teléfono (cable USB), https para todo lo demás.
                startsWithLoopback(text) -> "http://$text"
                else -> "https://$text"
            }
        val uri =
            try {
                URI(withScheme)
            } catch (_: URISyntaxException) {
                return Result.Invalid("La dirección no es válida.")
            }
        val scheme = uri.scheme?.lowercase()
        val host = uri.host?.lowercase()
        return when {
            scheme != "https" && scheme != "http" -> Result.Invalid("Usa una dirección que empiece con https://.")
            host.isNullOrEmpty() -> Result.Invalid("Falta el nombre del servidor.")
            uri.userInfo != null -> Result.Invalid("No pongas usuario ni contraseña en la dirección.")
            scheme == "http" && !isLoopback(host) ->
                Result.Invalid("Fuera de este teléfono solo se permite https:// (Tailscale lo da).")
            !uri.rawPath.isNullOrEmpty() && uri.rawPath != "/" ->
                Result.Invalid("Pon solo el servidor, sin ruta (por ejemplo https://mi-servidor.ts.net).")
            uri.rawQuery != null || uri.rawFragment != null ->
                Result.Invalid("La dirección no debe llevar parámetros.")
            else -> {
                val port = if (uri.port == -1) "" else ":${uri.port}"
                Result.Ok("$scheme://$host$port")
            }
        }
    }
}
