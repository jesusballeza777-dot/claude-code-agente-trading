package com.agentetrading.control.net

import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import org.json.JSONException
import org.json.JSONObject

/**
 * Cliente de la API del Centro de Mando. Solo hace GET, salvo el inicio de sesión.
 * La sesión (cookie) vive en memoria: al cerrar la app hay que volver a entrar.
 */
class ApiClient(private val baseUrl: String, private val timeoutMs: Int = 8_000) {
    sealed interface Result {
        data class Ok(val json: JSONObject) : Result

        /** El servidor tiene la autenticación activa y no hay sesión (o caducó). */
        data object NeedsLogin : Result

        data class Failed(val message: String) : Result
    }

    sealed interface LoginResult {
        data object Ok : LoginResult

        data class Rejected(val message: String) : LoginResult

        data class Failed(val message: String) : LoginResult
    }

    private class Raw(val code: Int, val body: String, val setCookies: List<String>)

    @Volatile
    var sessionCookie: String? = null
        private set

    fun get(path: String): Result = call("GET", path, null)

    /** Única escritura de la API además de la sesión: las notas del diario. Lleva la cabecera anti-CSRF. */
    fun post(path: String, body: JSONObject): Result = call("POST", path, body.toString())

    private fun call(method: String, path: String, body: String?): Result =
        try {
            val raw = send(method, path, body)
            when (raw.code) {
                200 ->
                    try {
                        Result.Ok(JSONObject(raw.body))
                    } catch (_: JSONException) {
                        Result.Failed("Respuesta inesperada del servidor.")
                    }
                401 -> {
                    sessionCookie = null
                    Result.NeedsLogin
                }
                // 4xx con explicación: la API dice qué está mal en `detail` o `detalle`.
                in 400..499 -> Result.Failed(detail(raw.body) ?: "El servidor respondió con el código ${raw.code}.")
                else -> Result.Failed("El servidor respondió con el código ${raw.code}.")
            }
        } catch (e: IOException) {
            Result.Failed("Sin conexión con el servidor: ${e.message ?: "sin respuesta"}.")
        }

    private fun detail(body: String): String? =
        try {
            val json = JSONObject(body)
            (json.opt("detail") ?: json.opt("detalle")) as? String
        } catch (_: JSONException) {
            null
        }

    fun login(password: String, totp: String): LoginResult =
        try {
            val body = JSONObject().put("password", password).put("totp", totp).toString()
            val raw = send("POST", "/api/sesion", body)
            when (raw.code) {
                200 -> {
                    sessionCookie = raw.setCookies.firstNotNullOfOrNull { cookiePair(it) }
                    LoginResult.Ok
                }
                401 -> LoginResult.Rejected("Contraseña o código incorrectos.")
                429 -> LoginResult.Rejected("Demasiados intentos: espera 5 minutos.")
                else -> LoginResult.Failed("El servidor respondió con el código ${raw.code}.")
            }
        } catch (e: IOException) {
            LoginResult.Failed("Sin conexión con el servidor: ${e.message ?: "sin respuesta"}.")
        }

    private fun send(method: String, path: String, body: String?): Raw {
        val connection = URL(baseUrl + path).openConnection() as HttpURLConnection
        try {
            connection.requestMethod = method
            connection.connectTimeout = timeoutMs
            connection.readTimeout = timeoutMs
            connection.instanceFollowRedirects = false
            connection.setRequestProperty("Accept", "application/json")
            sessionCookie?.let { connection.setRequestProperty("Cookie", it) }
            if (body != null) {
                // Cabecera anti-CSRF que exige la API para cualquier escritura (ADR-015).
                connection.setRequestProperty("X-Brujula", "1")
                connection.setRequestProperty("Content-Type", "application/json")
                connection.doOutput = true
                connection.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
            }
            val code = connection.responseCode
            val stream = if (code in 200..299) connection.inputStream else connection.errorStream
            val text = stream?.bufferedReader()?.use { it.readText() }.orEmpty()
            val cookies = connection.headerFields.filterKeys { it.equals("Set-Cookie", ignoreCase = true) }.values.flatten()
            return Raw(code, text, cookies)
        } finally {
            connection.disconnect()
        }
    }

    private fun cookiePair(setCookie: String): String? =
        setCookie.substringBefore(';').takeIf { it.startsWith("$SESSION_COOKIE=") && it.length > SESSION_COOKIE.length + 1 }

    companion object {
        const val SESSION_COOKIE = "brujula_sesion"
    }
}
