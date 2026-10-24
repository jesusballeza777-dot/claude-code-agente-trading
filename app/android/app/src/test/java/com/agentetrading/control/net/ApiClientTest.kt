package com.agentetrading.control.net

import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpServer
import java.net.InetSocketAddress
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/** Habla por HTTP real con un servidor local que imita la autenticación del Centro de Mando. */
class ApiClientTest {
    private lateinit var server: HttpServer
    private lateinit var base: String
    private var authRequired = true
    private var loginStatus = 200
    private var lastPostHeaders = emptyMap<String, String>()
    private var lastPostBody = ""

    private fun HttpExchange.reply(code: Int, body: String, extra: Map<String, String> = emptyMap()) {
        extra.forEach { (k, v) -> responseHeaders.add(k, v) }
        responseHeaders.add("Content-Type", "application/json")
        val bytes = body.toByteArray()
        sendResponseHeaders(code, bytes.size.toLong())
        responseBody.use { it.write(bytes) }
    }

    @Before
    fun start() {
        server = HttpServer.create(InetSocketAddress("127.0.0.1", 0), 0)
        server.createContext("/api/estado") { ex ->
            val signedIn = ex.requestHeaders.getFirst("Cookie")?.contains("brujula_sesion=abc123") == true
            if (authRequired && !signedIn) ex.reply(401, """{"detalle":"inicia sesión"}""") else ex.reply(200, """{"live_trading":false}""")
        }
        server.createContext("/api/roto") { ex -> ex.reply(200, "esto no es json") }
        server.createContext("/api/caido") { ex -> ex.reply(502, "") }
        server.createContext("/api/sesion") { ex ->
            lastPostHeaders = mapOf("X-Brujula" to (ex.requestHeaders.getFirst("X-Brujula") ?: ""))
            lastPostBody = ex.requestBody.bufferedReader().readText()
            if (loginStatus == 200) {
                ex.reply(200, """{"activa":true}""", mapOf("Set-Cookie" to "brujula_sesion=abc123; HttpOnly; Path=/; SameSite=strict"))
            } else {
                ex.reply(loginStatus, """{"detalle":"no"}""")
            }
        }
        server.start()
        base = "http://127.0.0.1:${server.address.port}"
    }

    @After
    fun stop() = server.stop(0)

    @Test
    fun getsJsonWhenOpen() {
        authRequired = false
        val result = ApiClient(base).get("/api/estado")
        assertTrue(result is ApiClient.Result.Ok)
        assertEquals(false, (result as ApiClient.Result.Ok).json.getBoolean("live_trading"))
    }

    @Test
    fun asksForLoginOn401ThenWorksAfterLoggingIn() {
        val client = ApiClient(base)
        assertEquals(ApiClient.Result.NeedsLogin, client.get("/api/estado"))
        assertEquals(ApiClient.LoginResult.Ok, client.login("clave", "123456"))
        assertEquals("brujula_sesion=abc123", client.sessionCookie)
        assertTrue(client.get("/api/estado") is ApiClient.Result.Ok)
        // El inicio de sesión lleva la cabecera anti-CSRF y el cuerpo JSON esperado por la API.
        assertEquals("1", lastPostHeaders["X-Brujula"])
        assertTrue(lastPostBody.contains("\"totp\":\"123456\"") && lastPostBody.contains("\"password\":\"clave\""))
    }

    @Test
    fun rejectedLoginsKeepNoSession() {
        val client = ApiClient(base)
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
        val client = ApiClient(base)
        client.login("clave", "123456")
        assertNotNull(client.sessionCookie)
        authRequired = true
        // Tras un 401 el servidor ya no acepta la cookie guardada: se descarta y se vuelve a pedir.
        server.removeContext("/api/estado")
        server.createContext("/api/estado") { ex -> ex.reply(401, "{}") }
        assertEquals(ApiClient.Result.NeedsLogin, client.get("/api/estado"))
        assertNull(client.sessionCookie)
    }

    @Test
    fun badResponsesBecomeReadableFailures() {
        val client = ApiClient(base)
        assertEquals("Respuesta inesperada del servidor.", (client.get("/api/roto") as ApiClient.Result.Failed).message)
        assertTrue((client.get("/api/caido") as ApiClient.Result.Failed).message.contains("502"))
    }

    @Test
    fun unreachableServerFailsInsteadOfCrashing() {
        val closed = HttpServer.create(InetSocketAddress("127.0.0.1", 0), 0)
        val port = closed.address.port
        closed.stop(0)
        val result = ApiClient("http://127.0.0.1:$port", timeoutMs = 1_000).get("/api/estado")
        assertTrue((result as ApiClient.Result.Failed).message.startsWith("Sin conexión"))
    }
}
