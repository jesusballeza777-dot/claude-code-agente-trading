package com.agentetrading.control.net

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ServerUrlTest {
    private fun ok(input: String): String = (ServerUrl.parse(input) as ServerUrl.Result.Ok).url

    private fun invalid(input: String): String = (ServerUrl.parse(input) as ServerUrl.Result.Invalid).reason

    @Test
    fun withoutSchemeItAssumesHttps() {
        assertEquals("https://mi-vps.tail1234.ts.net", ok("mi-vps.tail1234.ts.net"))
        assertEquals("https://mi-vps.ts.net", ok("  MI-VPS.ts.net/  "))
    }

    @Test
    fun keepsTheExplicitPort() {
        assertEquals("https://mi-vps.ts.net:8443", ok("https://mi-vps.ts.net:8443"))
    }

    @Test
    fun httpIsOnlyForThisPhone() {
        assertEquals("http://127.0.0.1:8080", ok("http://127.0.0.1:8080"))
        assertEquals("http://localhost:8080", ok("http://localhost:8080/"))
        assertTrue(invalid("http://192.168.1.20:8080").contains("https://"))
        assertTrue(invalid("http://mi-vps.ts.net").contains("https://"))
    }

    @Test
    fun loopbackWithoutSchemeAssumesHttp() {
        assertEquals("http://127.0.0.1:8080", ok("127.0.0.1:8080"))
        assertEquals("http://localhost:8080", ok("localhost:8080"))
        assertEquals("https://localhost.evil.example", ok("localhost.evil.example"))
    }

    @Test
    fun rejectsOtherSchemesAndCredentials() {
        assertTrue(invalid("ftp://mi-vps.ts.net").contains("https://"))
        assertTrue(invalid("javascript://x").isNotEmpty())
        assertTrue(invalid("https://usuario:clave@mi-vps.ts.net").contains("usuario"))
    }

    @Test
    fun rejectsPathsQueriesAndEmptyInput() {
        assertTrue(invalid("https://mi-vps.ts.net/api").contains("ruta"))
        assertTrue(invalid("https://mi-vps.ts.net?x=1").contains("parámetros"))
        assertTrue(invalid("   ").contains("Escribe"))
        assertTrue(invalid("https://").isNotEmpty())
    }
}
