package com.agentetrading.control.model

import org.json.JSONException
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Las respuestas de ejemplo son salidas reales de la API (tests/api/android_fixtures.py). */
class PageParsersTest {
    private fun resource(name: String): JSONObject =
        JSONObject(javaClass.classLoader!!.getResourceAsStream("$name.json")!!.bufferedReader().use { it.readText() })

    @Test
    fun limitesAreReadOnlyAndComeWithTheirAdr() {
        val limites = PageParsers.limites(resource("limites"))
        assertFalse(limites.editable)
        assertEquals(7, limites.vigentes.size)
        val riesgo = limites.vigentes.first { it.nombre == "Riesgo por operación" }
        assertEquals("0.005", riesgo.valor)
        assertTrue(riesgo.esFraccion)
        assertEquals("ADR-007", riesgo.adr)
        assertEquals(listOf("BTC", "ETH"), limites.gruposCorrelacionados.first())
    }

    @Test
    fun approvedCalculation() {
        val calculo = PageParsers.calculo(resource("calculadora-aprobada"))
        assertTrue(calculo.aprobada)
        assertTrue(calculo.vetos.isEmpty())
        assertNotNull(calculo.riesgoUsd)
        assertNotNull(calculo.precioLiquidacion)
        assertEquals("7.500", calculo.presupuestoUsd)
    }

    @Test
    fun vetoedCalculationKeepsTheEnginesExplanation() {
        val calculo = PageParsers.calculo(resource("calculadora-vetada"))
        assertFalse(calculo.aprobada)
        assertEquals("INVALID_STOP", calculo.vetos.single().codigo)
        assertTrue(calculo.vetos.single().explicacion.contains("stop"))
        // Sin operación aprobada no hay riesgo, apalancamiento ni liquidación: son null, no la palabra "null".
        assertNull(calculo.riesgoUsd)
        assertNull(calculo.apalancamientoEfectivo)
        assertNull(calculo.precioLiquidacion)
    }

    @Test
    fun vetoHistory() {
        val vetos = PageParsers.vetos(resource("vetos"))
        assertEquals(Origen.BACKTEST, vetos.origen)
        assertTrue(vetos.vetos.all { it.veces > 0 && it.explicacion.isNotEmpty() })
    }

    @Test
    fun decisionsAreDemoAndKeepTheirJson() {
        val decisiones = PageParsers.decisiones(resource("decisiones"))
        assertEquals(Origen.DEMO, decisiones.origen)
        assertEquals(18, decisiones.decisiones.size)
        assertTrue(decisiones.decisiones.first().json.contains("\"action\""))
        assertTrue(decisiones.decisiones.none { it.veto == "null" })
        assertEquals(3, decisiones.libros.size)
        assertNull(decisiones.libros.first().esperanzaR)
    }

    @Test
    fun journalHasTradesAndNotes() {
        val diario = PageParsers.diario(resource("diario"))
        assertEquals(Origen.BACKTEST, diario.origen)
        assertTrue(diario.operaciones.isNotEmpty())
        assertEquals("H2-v1", diario.notas.single().referencia)
        assertTrue(diario.operaciones.first().id.startsWith("H"))
    }

    @Test
    fun aSingleNote() {
        val nota = PageParsers.nota(JSONObject("""{"id":"a1","fecha_utc":"2026-10-24T03:26:25Z","referencia":"","texto":"hola"}"""))
        assertEquals("hola", nota.texto)
    }

    @Test
    fun projectCombinesRoadmapRisksAndCosts() {
        val proyecto = PageParsers.proyecto(resource("proyecto"))
        assertEquals("F0", proyecto.fases.first().id)
        assertTrue(proyecto.adr.any { it.id == "013" && it.estado.contains("Propuesto") })
        assertTrue(proyecto.riesgos.size > 10)
        assertEquals("18.70", proyecto.mxnPorUsd)
        assertTrue(proyecto.estadoTipoCambio.contains("por verificar"))
        assertEquals(Origen.DEMO, proyecto.usoApiOrigen)
    }

    @Test
    fun reportsListTypesAndHistory() {
        val reportes = PageParsers.reportes(resource("reportes"))
        assertTrue(reportes.tipos.any { it.tipo == "semanal" && it.formato == "pdf" })
        assertTrue(reportes.tipos.any { it.tipo == "contador" && it.formato == "csv" })
        assertEquals("contador", reportes.historial.single().tipo)
        assertTrue(reportes.historial.single().demo)
    }

    @Test(expected = JSONException::class)
    fun missingFieldsFail() {
        PageParsers.diario(resource("diario").also { it.remove("notas") })
    }
}
