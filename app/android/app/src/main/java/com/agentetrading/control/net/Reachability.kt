package com.agentetrading.control.net

import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

/** Comprueba que la dirección es de verdad un Centro de Mando antes de guardarla. */
object Reachability {
    sealed interface Outcome {
        /** Es el Centro de Mando. `needsLogin` indica que pedirá contraseña y código. */
        data class Found(val needsLogin: Boolean) : Outcome

        data class Failed(val message: String) : Outcome
    }

    fun check(baseUrl: String): Outcome =
        try {
            val connection = URL("$baseUrl/api/estado").openConnection() as HttpURLConnection
            connection.connectTimeout = TIMEOUT_MS
            connection.readTimeout = TIMEOUT_MS
            connection.instanceFollowRedirects = false
            connection.setRequestProperty("Accept", "application/json")
            try {
                when (val code = connection.responseCode) {
                    200 -> {
                        val body = connection.inputStream.bufferedReader().use { it.readText() }
                        if ("\"live_trading\"" in body) {
                            Outcome.Found(needsLogin = false)
                        } else {
                            Outcome.Failed("Ese servidor responde, pero no parece el Centro de Mando.")
                        }
                    }
                    401 -> Outcome.Found(needsLogin = true)
                    else -> Outcome.Failed("El servidor respondió con el código $code.")
                }
            } finally {
                connection.disconnect()
            }
        } catch (e: IOException) {
            Outcome.Failed("No se pudo conectar: ${e.message ?: "sin respuesta"}.")
        }

    private const val TIMEOUT_MS = 6_000
}
