package com.agentetrading.control.model

import org.json.JSONException
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** Resultados reales de la F4 (research/results) y respuestas reales del mercado de la API. */
class LabParsersTest {
    private fun resource(name: String): JSONObject =
        JSONObject(javaClass.classLoader!!.getResourceAsStream("$name.json")!!.bufferedReader().use { it.readText() })

    @Test
    fun labListsEveryHypothesisAndNoneOfThemPasses() {
        val lab = LabParsers.laboratorio(resource("laboratorio"))
        assertEquals(listOf("H1-v1", "H2-v1", "H4-H1-v1", "H4-H2-v1", "H3"), lab.hipotesis.map { it.id })
        assertEquals(296, lab.intentosTotal)
        assertEquals(4, lab.intentosPrincipales)
        // La verdad de la F4: ninguna pasa el gate sin holdout.
        assertTrue(lab.hipotesis.mapNotNull { it.gate }.none { it.pasa })
        val h2 = lab.hipotesis.first { it.id == "H2-v1" }
        assertEquals(272, h2.resumen?.operaciones)
        assertEquals(9, h2.gate?.cumplidos)
        assertEquals(10, h2.gate?.criterios?.size)
    }

    @Test
    fun deferredHypothesisHasNoNumbers() {
        val h3 = LabParsers.laboratorio(resource("laboratorio")).hipotesis.first { it.id == "H3" }
        assertFalse(h3.evaluada)
        assertNull(h3.resumen)
        assertNull(h3.gate)
        assertEquals("aplazada", h3.ciclo.single().estado)
    }

    @Test
    fun criteriaKeepTheProtocolOrder() {
        val gate = LabParsers.laboratorio(resource("laboratorio")).hipotesis.first { it.id == "H2-v1" }.gate!!
        assertEquals("1_operaciones_>=200", gate.criterios.first().clave)
        assertEquals(listOf("4a_dsr_>=0.90", "4b_pbo_<=0.30"), gate.criterios.map { it.clave }.filter { it.startsWith("4") })
        // H2-v1 falla únicamente el PBO.
        assertEquals(listOf("4b_pbo_<=0.30"), gate.criterios.filter { !it.cumple }.map { it.clave })
    }

    @Test
    fun detailHasTheGateWithItsValues() {
        val detalle = LabParsers.detalle(resource("laboratorio-h2"))
        assertEquals("H2-v1", detalle.id)
        assertEquals("T0030", detalle.trialId)
        val valores = detalle.gate!!.valores!!
        assertEquals(272, valores.operaciones)
        assertEquals(0.456, valores.pbo!!, 0.001)
        assertEquals(3, valores.regimenesPositivos.size)
        assertNotNull(valores.costesIc90)
        assertTrue(detalle.gate!!.holdout!!.startsWith("sellado"))
        assertTrue(detalle.parametros.any { it.first == "channel" && it.second == "60" })
    }

    @Test
    fun detailHasTheSeriesTheChartsNeed() {
        val detalle = LabParsers.detalle(resource("laboratorio-h2"))
        assertTrue(detalle.curva.size > 50)
        assertTrue(detalle.underwater.all { it.dd <= 0.0 })
        assertEquals(detalle.resumen.operaciones, detalle.distribucion.sumOf { it.n })
        assertTrue(detalle.mapaMensual.size >= 60)
        assertTrue(detalle.abanico.all { it.p5 <= it.p50 && it.p50 <= it.p95 })
        assertEquals("channel", detalle.sensibilidad.first().parametro)
        assertEquals(2, detalle.resumen.porDireccion.size)
        assertTrue(detalle.resumen.porSemestre.isNotEmpty())
    }

    @Test
    fun marketSymbolsCandlesAndChannel() {
        assertEquals(listOf("BTCUSDT", "ETHUSDT", "SOLUSDT").take(1), LabParsers.simbolos(resource("mercado-simbolos")).simbolos.take(1))
        val velas = LabParsers.velas(resource("mercado-velas"))
        assertEquals("4h", velas.intervalo)
        assertTrue(velas.velas.isNotEmpty())
        assertTrue(velas.velas.all { it.l <= it.o && it.l <= it.c && it.h >= it.o && it.h >= it.c })
        assertEquals(velas.velas.size, velas.canalAlto.size)
        assertEquals(1, velas.funding.take(1).size)
    }

    @Test
    fun correlationsAreSquareWithOnesOnTheDiagonal() {
        val corr = LabParsers.correlaciones(resource("mercado-correlaciones"))
        assertEquals(corr.simbolos.size, corr.matriz.size)
        assertTrue(corr.matriz.all { it.size == corr.simbolos.size })
        corr.matriz.forEachIndexed { i, row -> assertEquals(1.0, row[i]!!, 1e-9) }
    }

    @Test
    fun regimesAreOptionalWhenThereIsNoData() {
        val regimenes = LabParsers.regimenes(JSONObject("""{"origen":"demo","tramos":[]}"""))
        assertEquals(Origen.DEMO, regimenes.origen)
        assertTrue(RegimeTimeline.segments(regimenes.tramos).isEmpty())
    }

    @Test(expected = JSONException::class)
    fun missingFieldsFail() {
        LabParsers.detalle(resource("laboratorio-h2").also { it.remove("curva") })
    }
}
