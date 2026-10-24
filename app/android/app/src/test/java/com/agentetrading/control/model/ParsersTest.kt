package com.agentetrading.control.model

import org.json.JSONException
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Las respuestas de ejemplo son salidas reales de la API (tests/api: contrato con la app). */
class ParsersTest {
    private fun resource(name: String): JSONObject =
        JSONObject(javaClass.classLoader!!.getResourceAsStream(name)!!.bufferedReader().use { it.readText() })

    @Test
    fun parsesHoy() {
        val hoy = Parsers.hoy(resource("hoy.json"))
        assertFalse(hoy.estado.liveTrading)
        assertTrue(hoy.estado.holdoutSellado)
        assertEquals("2024-12-31", hoy.estado.ultimaVela)
        assertEquals(10, hoy.estado.fases.size)
        assertEquals("F0", hoy.estado.fases.first().id)
        assertEquals("docs/f1-verificacion-plataforma.md", hoy.estado.pendientes.first().documento)
        assertTrue(hoy.estado.pendientes.size >= 6)
        assertEquals(Origen.DEMO, hoy.cuenta.origen)
        assertEquals("1500.34", hoy.cuenta.capital)
        assertEquals(0.15, hoy.cuenta.parada, 1e-9)
        assertEquals(0.02, hoy.cuenta.diario.limite, 1e-9)
        assertTrue(hoy.cuenta.curva.size > 10)
        assertTrue(hoy.parte.validado)
        assertEquals("Brújula", hoy.parte.autor)
        assertEquals(0, hoy.posiciones.cantidad)
        assertTrue(hoy.posiciones.vacio.isNotEmpty())
    }

    @Test
    fun parsesEnVivo() {
        val vivo = Parsers.enVivo(resource("en-vivo.json"))
        assertEquals(7, vivo.motores.size)
        assertEquals(3, vivo.motores.count { it.activo })
        assertEquals("no iniciado", vivo.motores.first { it.id == "analista" }.estado)
        assertEquals("no conectado", vivo.motores.first { it.id == "exchanges" }.estado)
        // Las decisiones del analista son siempre demostración hasta la F5.
        assertEquals(Origen.DEMO, vivo.decisionesOrigen)
        assertEquals(6, vivo.decisiones.size)
        assertFalse(vivo.liveTrading)
    }

    @Test
    fun nullVetoIsNullNotTheWordNull() {
        val vivo = Parsers.enVivo(resource("en-vivo.json"))
        assertNull(vivo.decisiones.firstOrNull { it.veto == null }?.veto)
        assertTrue(vivo.decisiones.none { it.veto == "null" })
    }

    @Test
    fun unknownOriginIsNeverTreatedAsReal() {
        val json = resource("en-vivo.json").put("origen", "algo-raro")
        assertEquals(Origen.DEMO, Parsers.enVivo(json).origen)
    }

    @Test(expected = JSONException::class)
    fun missingRequiredFieldFails() {
        Parsers.enVivo(resource("en-vivo.json").also { it.remove("motores") })
    }
}
