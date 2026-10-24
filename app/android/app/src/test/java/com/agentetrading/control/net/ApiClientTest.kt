package com.agentetrading.control.net

import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Habla por HTTP real con un servidor local que imita la autenticación del Centro de Mando. */
class ApiClientTest {
    private var authRequired = true
    private var loginStatus = 200
    private var expireSessions = false

    private val server =
        MiniServer { request ->
            when (request.path) {
                "/api/estado" -> {
                    val signedIn = request.headers["cookie"]?.contains("brujula_sesion=abc123") == true
                    if ((authRequired && !signedIn) || expireSessions) {
                        MiniServer.Response(401, """{"detalle":"inicia sesión"}""")
                    } else {
                        MiniServer.Response(200, """{"live_trading":false}""")
                    }
                }
                "/api/roto" -> MiniServer.Response(200, "esto no es json")
                "/api/caido" -> MiniServer.Response(502)
                "/api/sesion" ->
                    if (loginStatus == 200) {
                        MiniServer.Response(200, """{"activa":true}""", listOf("Set-Cookie" to "brujula_sesion=abc123; HttpOnly; Path=/; SameSite=strict"))
                    } else {
                        MiniServer.Response(loginStatus, """{"detalle":"no"}""")
                    }
                else -> MiniServer.Response(404)
            }
        }

    @After
    fun stop() = server.close()

    @Test
    fun getsJsonWhenOpen() {
        authRequired = false
        val result = ApiClient(server.baseUrl).get("/api/estado")
        assertTrue(result is ApiClient.Result.Ok)
        assertEquals(false, (result as ApiClient.Result.Ok).json.getBoolean("live_trading"))
    }

    @Test
    fun asksForLoginOn401ThenWorksAfterLoggingIn() {
        val client = ApiClient(server.baseUrl)
        assertEquals(ApiClient.Result.NeedsLogin, client.get("/api/estado"))
        assertEquals(ApiClient.LoginResult.Ok, client.login("clave", "123456"))
        assertEquals("brujula_sesion=abc123", client.sessionCookie)
        val login = server.lastRequest
        assertTrue(client.get("/api/estado") is ApiClient.Result.Ok)
        // El inicio de sesión lleva la cabecera anti-CSRF y el cuerpo JSON que espera la API.
        assertEquals("POST", login?.method)
        assertEquals("1", login?.headers?.get("x-brujula"))
        assertTrue(login?.body?.contains("\"totp\":\"123456\"") == true)
        assertTrue(login?.body?.contains("\"password\":\"clave\"") == true)
    }

    @Test
    fun rejectedLoginsKeepNoSession() {
        val client = ApiClient(server.baseUrl)
        loginStatus = 401
        assertEquals("Contraseña o código incorrectos.", (client.login("x", "000000") as ApiClient.LoginResult.Rejected).message)
        loginStatus = 429
        assertTrue((client.login("x", "000000") as ApiClient.LoginResult.Rejected).message.contains("5 minutos"))
        loginStatus = 500
        assertTrue(client.login("x", "000000") is ApiClient.LoginResult.Failed)
        assertNull(client.sessionCookie)
    }

    @Test
    fun anExpiredSessionClearsTheCookie() {
        val client = ApiClient(server.baseUrl)
        client.login("clave", "123456")
        assertNotNull(client.sessionCookie)
        expireSessions = true // el servidor ya no acepta la cookie guardada
        assertEquals(ApiClient.Result.NeedsLogin, client.get("/api/estado"))
        assertNull(client.sessionCookie)
    }

    @Test
    fun badResponsesBecomeReadableFailures() {
        val client = ApiClient(server.baseUrl)
        assertEquals("Respuesta inesperada del servidor.", (client.get("/api/roto") as ApiClient.Result.Failed).message)
        assertTrue((client.get("/api/caido") as ApiClient.Result.Failed).message.contains("502"))
    }

    @Test
    fun unreachableServerFailsInsteadOfCrashing() {
        val closed = MiniServer { MiniServer.Response(200) }
        val url = closed.baseUrl
        closed.close()
        val result = ApiClient(url, timeoutMs = 1_000).get("/api/estado")
        assertTrue((result as ApiClient.Result.Failed).message.startsWith("Sin conexión"))
    }
}
